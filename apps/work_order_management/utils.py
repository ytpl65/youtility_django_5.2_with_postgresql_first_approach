from apps.core.utils import get_email_addresses, send_email
from .models import Wom
from datetime import timedelta
from django.template.loader import render_to_string 
from django.conf import settings
from apps.peoples.models import People
from django.http import QueryDict
from apps.peoples import utils as putils
from apps.activity.models.question_model import QuestionSetBelonging,QuestionSet
from apps.work_order_management.models import WomDetails
from django.http import response as rp
from background_tasks.tasks import send_email_notification_for_sla_report
import logging
import getpass
logger = logging.getLogger('django')
import os
def check_attachments_if_any(wo):
    from apps.activity.models.attachment_model import Attachment
    return Attachment.objects.get_att_given_owner(wo.uuid)

def notify_wo_creation(id):
    '''
    function notifies vendor and creator about the new 
    work order has been created
    '''
    if wo := Wom.objects.filter(id=id).first():
        peopleids = [wo.cuser_id, wo.muser_id]
        
        emails = get_email_addresses(people_ids=peopleids)
        emails += [wo.vendor.email]
        logger.info(f'Email Addresses of recipents are {emails=}')
        subject = f'New work order #{wo.id} from {wo.client.buname}'
        context = {
            'workorderid'   : id,
            'description'   : wo.description,
            'priority'      : wo.priority,
            'vendorname'    : wo.vendor.name,
            'plandatetime'  : wo.plandatetime + timedelta(minutes=wo.ctzoffset),
            'expirydatetime': wo.expirydatetime + timedelta(minutes=wo.ctzoffset),
            'asset'         : wo.asset.assetname if wo.asset_id not in [1, None] else None,
            'cuseremail'    : wo.cuser.email,
            'cusername'     : wo.cuser.peoplename,
            'cdtz'          : wo.cdtz + timedelta(minutes=wo.ctzoffset),
            'token'         : wo.other_data['token'],
            'HOST'          : settings.HOST 
        }
        if atts := check_attachments_if_any(wo):
            attachments = [f"{settings.MEDIA_ROOT}/{att['filepath']}{att['filename']}" for att in atts]
        
        html_message = render_to_string('work_order_management/work_order_email.html', context=context)
        send_email(
            subject=subject, body=html_message, to=emails, atts= attachments if atts else None
        )
        wo.ismailsent = True
        wo.save()
        return wo
    else:
        logger.info('object not found')
        
def check_all_verified(womuuid,usercode):
    w = Wom.objects.filter(uuid = womuuid).first()
    all_verified = True
    logger.info(f"{usercode}, {womuuid}")
    for verifier in w.other_data['wp_verifiers']:
        logger.info(f"Verifier {verifier}")
        if verifier['peoplecode'] == usercode:
            verifier['status'] = 'APPROVED'
            logger.info(f"verifier {verifier['name']} has approved with status code {verifier['status']}")
        if verifier['status'] != 'APPROVED':
            all_verified = False
    w.save()
    logger.info(f"all approved status is {all_verified}")
    return all_verified
        
def check_all_approved(womuuid, usercode):
    w = Wom.objects.filter(uuid = womuuid).first()
    all_approved = True
    logger.info(f"{usercode}, {womuuid}")
    for approver in w.other_data['wp_approvers']:
        logger.info(f"Approver {approver}")
        if approver['peoplecode'] == usercode:
            approver['status'] = 'APPROVED'
            logger.info(f"approver {approver['name']} has approved with status code {approver['status']}")
        if approver['status'] != 'APPROVED':
            all_approved = False
    w.save()
    logger.info(f"all approved status is {all_approved}")
    return all_approved
    
def reject_workpermit(womuuid, usercode):
    w = Wom.objects.filter(uuid = womuuid).first()
    for approver in w.other_data['wp_verifiers']:
        if approver['peoplecode'] == usercode:
            approver['status'] = 'REJECTED'
    w.save()


def reject_workpermit_verifier(womuuid, usercode):
    w = Wom.objects.filter(uuid = womuuid).first()
    for verifier in w.other_data['wp_verifiers']:
        if verifier['peoplecode'] == usercode:
            verifier['status'] = 'REJECTED'
    for approver in w.other_data['wp_approvers']:
        approver['status'] = 'PENDING'
    w.save()
    
def save_approvers_injson(wp):
    logger.info("saving approvers started")
    wp_approvers = [
        {'name': People.objects.get(peoplecode=approver).peoplename, 'status': 'PENDING','identifier':'APPROVER','peoplecode':approver} for approver in wp.approvers
    ]
    wp.other_data['wp_approvers'] = wp_approvers
    wp.save()
    logger.info("saving approvers ended")
    return wp

def save_verifiers_injson(wp):
    logger.info("saving verifiers started")
    wp_verifiers = [
        {'name': People.objects.get(peoplecode=verifier).peoplename, 'status':'PENDING','identifier':'VERIFIER','peoplecode':verifier} for verifier in wp.verifiers
    ]
    wp.other_data['wp_verifiers'] = wp_verifiers
    wp.save()
    logger.info("saving verifiers ended")
    return wp

def save_workpermit_name_injson(wp,permit_name):
    wp.other_data['wp_name'] = permit_name
    wp.save()
    return wp

def get_approvers(approver_codes):
    approvers = []
    for code in approver_codes:
        try:
            people = People.objects.get(peoplecode = code)
            approvers.append({'peoplename': people.peoplename})
        except People.DoesNotExist:
            approvers.append({'peoplecode': code, 'peoplename': code})
    return approvers


def extract_data(wp_answers):
        for section in wp_answers:
            for question in section['questions']:
                if question['question__quesname'] == 'Permit Authorized by':
                    return question['answer']
                

def handle_valid_form(form, R, request, create):
    from urllib.parse import parse_qs
    S = request.session
    sla = form.save(commit=False)
    month = request.POST.get('month_name','')
    sla.other_data['month'] = month
    sla.uuid = request.POST.get('uuid')
    sla = putils.save_userinfo(
        sla, request.user, request.session, create = create)
    sla = save_approvers_injson(sla)
    formdata = QueryDict(request.POST['sladetails']).copy()
    overall_score = get_overall_score(sla.id)
    sla.other_data['overall_score'] = overall_score
    create_sla_details(request.POST, sla, request, formdata)
    sitename = S.get('sitename')
    wom_parent = Wom.objects.get(id=sla.id)
    wom = Wom.objects.filter(parent_id=sla.id).order_by('-id')[1]
    uptime_score = WomDetails.objects.filter(wom_id=wom.id)[2].answer
    wom_parent.other_data['uptime_score'] = uptime_score
    wom.other_data['section_weightage']=0
    wom_parent.save()
    send_email_notification_for_sla_report.delay(sla.id,sitename)
    return rp.JsonResponse({'pk':sla.id})


def create_sla_details(R,wom,request,formdata):
        SECTION_WEIGHTAGE = {
            'WORK SAFETY': 0.2,
            'SERVICE DELIVERY':0.2,
            'LEGAL COMPLIANCE':0.2,
            'DOCUMENTATION/RECORD':0.2,
            'TECHNOLOGY DESIGN':0.1,
            'CPI':0.1,
            'KPI As Per Agreement':0,
            'REMARKS':0,
        }
        logger.info(f'creating sla_details started {R}')
        for k,v in formdata.items():
            if k not in ['ctzoffset', 'wom_id', 'action', 'csrfmiddlewaretoken'] and '_' in k:
                ids = k.split('_')
                qsb_id = ids[0]
                qset_id = ids[1]

                qsb_obj = QuestionSetBelonging.objects.filter(id=qsb_id).first()

                if qsb_obj.answertype in  ['NUMERIC'] and qsb_obj.alerton and len(qsb_obj.alerton) > 0:
                    alerton = qsb_obj.alerton.replace('>', '').replace('<', '').split(',')
                    if len(alerton) > 1:
                        _min, _max = alerton[0], alerton[1]
                        alerts = float(v) < float(_min) or float(v) > float(_max)
                else:
                    alerts = False

                childwom = create_child_wom(wom,qset_id)
                lookup_args = {
                    'wom_id':childwom.id,
                    'question_id':qsb_obj.question_id,
                    'qset_id':qset_id
                }
                default_data = {
                    'seqno'       : qsb_obj.seqno,
                    'answertype'  : qsb_obj.answertype,
                    'answer'      : v,
                    'isavpt'      : qsb_obj.isavpt,
                    'options'     : qsb_obj.options,
                    'min'         : qsb_obj.min,
                    'max'         : qsb_obj.max,
                    'alerton'     : qsb_obj.alerton,
                    'ismandatory' : qsb_obj.ismandatory,
                    'alerts'      : alerts,
                    'cuser_id'    : request.user.id,
                    'muser_id'    : request.user.id,
                }
                data = lookup_args | default_data

                WomDetails.objects.create(
                    **data
                )
                logger.info(f"wom detail is created for the for the child wom: {childwom.description}")


def create_child_wom(wom, qset_id):
    qset = QuestionSet.objects.get(id=qset_id)
    if childwom := Wom.objects.filter(
        parent_id = wom.id,
        qset_id = qset.id,
        seqno = qset.seqno
    ).first():
        logger.info(f"wom already exist with qset_id {qset_id} so returning it")
        return childwom
    else:
        logger.info(f'creating wom for qset_id {qset_id}')
        SECTION_WEIGHTAGE = {
            'WORK SAFETY': 0.2,
            'SERVICE DELIVERY':0.2,
            'LEGAL COMPLIANCE':0.2,
            'DOCUMENTATION/RECORD':0.2,
            'TECHNOLOGY DESIGN':0.1,
            'KPI As Per Agreement':0,
            'CPI':0.1,
            'REMARKS':0,
        }
        qs = QuestionSet.objects.get(id=qset_id).qsetname
        if qs in SECTION_WEIGHTAGE:

            section_weightage = SECTION_WEIGHTAGE[qs]
            wom.other_data['section_weightage'] = section_weightage
            logger.info(f"section and question %s %s",section_weightage,qs)
        return Wom.objects.create(
                parent_id      = wom.id,
                description    = qset.qsetname,
                plandatetime   = wom.plandatetime,
                expirydatetime = wom.expirydatetime,
                starttime      = wom.starttime,
                gpslocation    = wom.gpslocation,
                asset          = wom.asset,
                location       = wom.location,
                workstatus     = wom.workstatus,
                seqno          = qset.seqno,
                approvers      = wom.approvers,
                workpermit     = wom.workpermit,
                priority       = wom.priority,
                vendor         = wom.vendor,
                performedby    = wom.performedby,
                alerts         = wom.alerts,
                client         = wom.client,
                bu             = wom.bu,
                ticketcategory = wom.ticketcategory,
                other_data     = wom.other_data,
                qset           = qset,
                cuser          = wom.cuser,
                muser          = wom.muser,
                ctzoffset      = wom.ctzoffset
        )
    

def get_overall_score(id):
    sla_answers_data,overall_score,question_ans,all_average_score,remarks = Wom.objects.sla_data_for_report(id)
    return overall_score

def get_pdf_path():
    user_name = getpass.getuser()
    tmp_pdf_location = f'/var/tmp/youtility4_media/'
    if not os.path.exists(tmp_pdf_location):
        os.makedirs(tmp_pdf_location)
    return tmp_pdf_location

def save_pdf_to_tmp_location(report_pdf_object,report_name,report_number):
    tmp_pdf_location = get_pdf_path()
    output_pdf = f'{report_name}-{report_number}.pdf'
    final_path = os.path.join(tmp_pdf_location,output_pdf)
    with open(final_path, 'wb') as file:
        file.write(report_pdf_object)
    return final_path


def get_report_object(permit_name):
    from apps.reports.report_designs import workpermit as wp
    return {
            'Cold Work Permit':wp.ColdWorkPermit,
            'Hot Work Permit':wp.HotWorkPermit,
            'Confined Space Work Permit':wp.ConfinedSpaceWorkPermit,
            'Electrical Work Permit':wp.ElectricalWorkPermit,
            'Height Work Permit':wp.HeightWorkPermit,
            'Entry Request':wp.EntryRequest,
    }.get(permit_name)



from django.db.models import Max
from datetime import datetime, timedelta

def get_month_number(MONTH_CHOICES,month_name):
        if month_name == 0:
            return '-'
        for number, name in MONTH_CHOICES.items():
            if name.lower() == month_name.lower():
                return int(number)
        return '-'
 

def get_last_12_months_sla_reports(vendor_id, bu_id,month_number):
    logger.info(f'Month Number: {month_number}')
    sla_reports = {}
    # Get the last 3 months' approved records, excluding the current month
    current_month = datetime.now().month
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    current_date = datetime.now()
    current_year = current_date.year
    if current_date.month == 1:
        previous_month_year = current_date.year - 1
    else:
        previous_month_year = current_date.year

    for i in range(1, 13):
        month = int(month_number) - i
        year = current_year
        
        if current_year == previous_month_year:
            if month <=0:
                year-=1
            else:
                year = current_year
        else:
            if month <= 0:
                year-=2
            else:
                year -= 1
        month_name = months[month - 1]
        year_ = str(year)[2:]
        month_year = f"{month_name}'{year_}"
        if month<=0:
            month= month + 12
        latest_report = Wom.objects.filter(
            vendor_id=vendor_id,
            identifier='SLA',
            bu_id=bu_id,
            workpermit=Wom.WorkPermitStatus.APPROVED,
            cdtz__month=month,
            cdtz__year=year
        ).aggregate(max_date=Max('cdtz'))

        if latest_report['max_date']:
            report = Wom.objects.filter(
                vendor_id=vendor_id,
                identifier='SLA',
                bu_id=bu_id,
                workpermit=Wom.WorkPermitStatus.APPROVED,
                cdtz=latest_report['max_date']
            ).first()
            sla_reports[month_year] = [report.other_data['overall_score'],report.other_data.get('uptime_score','N/A')]
        else:
            sla_reports[month_year] = ['N/A','N/A']
    return sla_reports




def get_sla_report_approvers(sla_approvers):
    approver_name = []
    for data in sla_approvers:
        approver_name.append(data['name'])
    return approver_name

def get_peoplecode(wp_approvers):
    people_codes = []
    for approver_data in wp_approvers:
        peoplecode = approver_data['peoplecode']
        people_codes.append(peoplecode)
    return people_codes

def approvers_email_and_name(people_codes):
    approvers_email = []
    approvers_name  = []
    for people_code in people_codes:
        data = People.objects.filter(peoplecode=people_code).values('peoplename','email')[0]
        name,email  = data['peoplename'],data['email']
        approvers_email.append(email)
        approvers_name.append(name)
    return approvers_email,approvers_name

def get_approvers_code(approver_data):
    approvers_code = []
    for ele in approver_data:
        approvers_code.append(ele['peoplecode'])
    return approvers_code

def get_verifiers_code(verifiers_data):
    verifiers_code = []
    for ele in verifiers_data:
        verifiers_code.append(ele['peoplecode'])
    return verifiers_code


def check_if_valid_approver(peoplecode,approvers_code):
    return peoplecode in approvers_code


def check_if_valid_verifier(peoplecode,verifiers_code):
    return peoplecode in verifiers_code