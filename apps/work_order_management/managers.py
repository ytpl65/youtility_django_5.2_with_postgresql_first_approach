from django.db import models
from django.db.models.functions import Concat, Cast
from django.db.models import CharField, Value as V
from django.db.models import Q, F, Count, Case, When,IntegerField
from django.contrib.gis.db.models.functions import   AsGeoJSON
from django.conf import settings
from datetime import datetime, timedelta
import json
import urllib.parse
from apps.peoples.models import People
from django.apps import apps
from django.utils.timezone import make_aware
import logging
import pytz

logger       = logging.getLogger('django')

def safe_json_parse_params(request_get, param_name='params'):
    """
    Safely parse JSON parameters from request.GET.
    Returns dict with default date range if parsing fails or keys missing.
    """
    from datetime import date, timedelta
    logger = logging.getLogger(__name__)
    
    params_raw = request_get.get(param_name, '{}')
    
    if params_raw in ['null', None, '']:
        parsed = {}
    else:
        try:
            # URL decode if necessary
            if params_raw.startswith('%'):
                params_raw = urllib.parse.unquote(params_raw)
            parsed = json.loads(params_raw)
        except (json.JSONDecodeError, TypeError) as e:
            # Fallback to empty dict if JSON parsing fails
            logger.warning(f"Failed to parse {param_name} JSON: {params_raw}, error: {e}")
            parsed = {}
    
    # Ensure required keys exist with default values
    today = date.today()
    parsed.setdefault('from', (today - timedelta(days=7)).strftime('%Y-%m-%d'))
    parsed.setdefault('to', today.strftime('%Y-%m-%d'))
    
    return parsed
debug_logger = logging.getLogger('debug_logger')
error_logger = logging.getLogger('error_logger')
class VendorManager(models.Manager):
    use_in_migrations = True
    
    def get_vendor_list(self, request, fields, related):
        R , S = request.GET, request.session
        if R.get('params'): P = safe_json_parse_params(R)
        
        qobjs =  self.select_related(*related).filter(
            client_id = S['client_id'],
            enable=True
        ).values(*fields).order_by('name')
        return qobjs or self.none()
    
    def get_vendors_for_mobile(self, request, clientid, mdtz, buid, ctzoffset):
        if not isinstance(mdtz, datetime):
            mdtz = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        mdtz = make_aware(mdtz, timezone=pytz.UTC)
        
        mdtz = mdtz - timedelta(minutes=ctzoffset)
            
        qset = self.filter(
            Q(bu_id = buid) | Q(show_to_all_sites = True),
            mdtz__gte = mdtz,
            client_id = clientid, 
            
        ).values()
        
        return qset or self.none()
    
class ApproverManager(models.Manager):
    use_in_migrations = True
    
    def get_approver_list(self, request, fields, related):
        R,S  = request.GET, request.session
        qobjs =  self.select_related(*related).filter(
           ( Q(bu_id = S['bu_id']) | Q( bu_id__in = S['assignedsites'])) | (Q(forallsites = True) & Q(client_id = S['client_id']))
        ).values(*fields)
        return qobjs or self.none()
    
    def get_approver_options_wp(self, request):
        S = request.session
        assignedsites = S.get('assignedsites', [])
        
        # Ensure assignedsites is always a list
        if isinstance(assignedsites, (int, str)):
            assignedsites = [assignedsites]
        elif not isinstance(assignedsites, (list, tuple)):
            assignedsites = []
            
        qset = self.annotate(
            text=F('people__peoplename'),
        ).filter( 
            (Q(bu_id=S['bu_id']) | Q(sites__contains=assignedsites)) | 
            (Q(forallsites=True) & Q(client_id=S['client_id'])),
            approverfor__contains=['WORKPERMIT'],
            identifier='APPROVER'
        ).values('id', 'text')
        return qset or self.none()
    
    def get_verifier_options_wp(self,request):
        S = request.session
        assignedsites = S.get('assignedsites', [])
        if not isinstance(assignedsites, (list, tuple)):
            assignedsites = [assignedsites]
        qset = self.annotate(
            text=F('people__peoplename'),
        ).filter(
            (Q(bu_id=S['bu_id']) | Q(sites__contains=assignedsites)) | 
            (Q(forallsites=True) & Q(client_id=S['client_id'])),
            approverfor__contains=['WORKPERMIT'],  # Ensure this is a list
            identifier='VERIFIER'
        ).values('id', 'text')
        return qset or self.none()
    
    def get_approver_options_sla(self,request):
        S = request.session
        qset = self.annotate(
            text = F('people__peoplename'),
        ).filter( (Q(bu_id = S['bu_id']) | Q( sites__contains = S['assignedsites'])) | (Q(forallsites = True) & 
        Q(client_id = S['client_id'])),approverfor__contains = ['SLA_TEMPLATE'],identifier = 'APPROVER').values('id', 'text')
        return qset or self.none()
    
    def get_approver_list_for_mobile(self, buid, clientid):
        qset = self.select_related().filter(
            Q(bu_id=buid) | Q(forallsites=True), client_id=clientid
        ).annotate(
            peoplecode=F('people__peoplecode'),
            peoplename=F('people__peoplename')).values(
                'id', 'cdtz', 'mdtz', 'cuser_id', 'muser_id', 'ctzoffset', 'bu_id',
                'client_id', 'people_id', 'peoplename', 'peoplecode', 'forallsites',
                'approverfor', 'sites','identifier'
            )
        if qset:
            for obj in qset:
                obj['approverfor'] = ','.join(obj['approverfor'] or "")
                obj['sites'] = ','.join(obj['sites'] or "")
        logger.info(f"Qset : {qset}")
        return qset or self.none()


class WorkOrderManager(models.Manager):
    use_in_migrations = True
    
    def get_workorder_list(self, request, fields, related):
        from .models import Wom
        S = request.session
        P = safe_json_parse_params(request.GET)
        qset = self.filter(
            cdtz__date__gte=P['from'],
            cdtz__date__lte=P['to'],
            client_id=S['client_id'],
            workpermit=Wom.WorkPermitStatus.NOTNEED
        ).select_related(*related).values(
            *fields
        )
        if P.get('status'):
            qset = qset.filter(workstatus =P['status'])
        return qset or self.none()
    
    def get_workpermitlist(self, request):
        from apps.work_order_management.models import Approver
        R, S = request.GET, request.session
        P = safe_json_parse_params(R)
        people_id = S['people_id']
        try:
            identifier = Approver.objects.get(people_id=people_id, approverfor='{WORKPERMIT}').identifier
        except Approver.DoesNotExist:
            identifier = None
        if identifier == 'APPROVER':
            qobjs = self.select_related('cuser', 'bu', 'qset','vendor').filter(
            ~Q(workpermit__in =  ['NOT_REQUIRED', 'NOTREQUIRED']),
                ~Q(identifier = 'SLA'),
                parent_id = 1,
                client_id = S['client_id'],
                bu_id = S['bu_id'],
                cdtz__date__gte = P['from'],
                cdtz__date__lte = P['to'],
                verifiers_status='APPROVED'
            ).order_by('-other_data__wp_seqno').values('cdtz', 'other_data__wp_seqno', 'qset__qsetname', 'workpermit', 'ctzoffset',
                    'workstatus', 'id', 'cuser__peoplename', 'bu__buname', 'bu__bucode','identifier','verifiers_status','vendor__name','remarks')
        else:
            qobjs = self.select_related('cuser', 'bu', 'qset','vendor').filter(
            ~Q(workpermit__in =  ['NOT_REQUIRED', 'NOTREQUIRED']),
                ~Q(identifier = 'SLA'),
                parent_id = 1,
                client_id = S['client_id'],
                bu_id = S['bu_id'],
                cdtz__date__gte = P['from'],
                cdtz__date__lte = P['to'],
            ).order_by('-other_data__wp_seqno').values('cdtz', 'other_data__wp_seqno', 'qset__qsetname', 'workpermit', 'ctzoffset',
                    'workstatus', 'id', 'cuser__peoplename', 'bu__buname', 'bu__bucode','identifier','verifiers_status','vendor__name','remarks')
        
        return qobjs or self.none()
         

    def get_slalist(self,request):
        R,S = request.GET, request.session
        P = safe_json_parse_params(R)
        qobjs = self.select_related('cuser', 'bu', 'qset','vendor').filter(
            identifier = 'SLA',
            client_id = S['client_id'],
            bu_id = S['bu_id'],
            cdtz__date__gte = P['from'],
            cdtz__date__lte = P['to'],
        ).order_by('-other_data__wp_seqno').values('cdtz', 'other_data__wp_seqno', 'qset__qsetname', 'workpermit', 'ctzoffset',
                 'workstatus', 'id', 'cuser__peoplename', 'bu__buname', 'bu__bucode','vendor__name','other_data__overall_score','other_data__uptime_score','other_data__remarks')
        return qobjs or self.none()

    def get_workpermit_details(self, request, wp_qset_id):
        S = request.session
        QuestionSet = apps.get_model('activity', 'QuestionSet')
        wp_details = []
        sections_qset = QuestionSet.objects.filter(parent_id = wp_qset_id,enable = True).order_by('seqno')
        for section in sections_qset:
            sq = {
                "section":section.qsetname,
                "sectionID":section.seqno,
                'questions':section.questionsetbelonging_set.values(
                    'question__quesname', 'answertype', 'qset_id',
                    'min', 'max', 'options', 'id', 'ismandatory').order_by('seqno')
            }
            wp_details.append(sq)
        return wp_details or self.none()
        
    def get_return_wp_details(self, qset_id):
        QuestionSet = apps.get_model('activity', 'QuestionSet')
        sections_qset = QuestionSet.objects.filter(parent_id = qset_id,enable=True).order_by('seqno')

        rwp_details = []
        for section in sections_qset:
            sq={
                "section":section.qsetname,
                "sectionID":section.seqno,
                'questions':section.questionsetbelonging_set.values(
                    'question__quesname', 'answertype', 'qset_id',
                    'min', 'max', 'options', 'id', 'ismandatory').order_by('seqno')
            }
            rwp_details.append(sq)
        return rwp_details.pop(-1) or self.none()
            
        
 
# Testing
    def get_wp_answers(self, womid):
        childwoms = self.filter(parent_id = womid).order_by('seqno')
        logger.info(f"{childwoms = }")
        wp_details = []
        for childwom in childwoms:
            sq = {
                "section":childwom.description,
                "sectionID":childwom.seqno,
                'questions':childwom.womdetails_set.values(
                    'question__quesname', 'answertype', 'answer', 'qset_id',
                    'min', 'max', 'options', 'id', 'ismandatory').order_by('seqno')
            }
            wp_details.append(sq)
        return wp_details or self.none()





    def get_approver_list(self, womid):
        if womid == 'None':return []
        obj = self.filter(
            id = womid
        ).values('other_data').first()
        app_verifier_status_data = obj['other_data']['wp_approvers'] 
        return app_verifier_status_data or []
    
    def get_approver_verifier_status(self, womid):
        if womid == 'None':return []
        obj = self.filter(id = womid).values('other_data').first()
        verifier_data = obj['other_data']['wp_verifiers']
        approver_data = obj['other_data']['wp_approvers']
        data = verifier_data + approver_data
        return data
    
    def get_wom_status_chart(self, request):
        S,R = request.session, request.GET
        qset = self.filter(
            bu_id__in = S['assignedsites'],
            client_id = S['client_id'],
            cdtz__date__gte = R['from'],
            cdtz__date__lte = R['upto'],
            workpermit = 'NOT_REQUIRED'
        )

        aggregate_data = qset.aggregate(
            assigned    = Count(Case(When(workstatus='ASSIGNED',then=1),output_field=IntegerField())),
            re_assigned = Count(Case(When(workstatus='RE_ASSIGNED',then=1),output_field=IntegerField())),
            completed   = Count(Case(When(workstatus='COMPLETED',then=1),output_field=IntegerField())),
            inprogress  = Count(Case(When(workstatus='INPROGRESS',then=1),output_field=IntegerField())),
            closed      = Count(Case(When(workstatus='CLOSED',then=1),output_field=IntegerField())),
            cancelled   = Count(Case(When(workstatus='CANCELLED',then=1),output_field=IntegerField()))
        )

        stats = [
            aggregate_data['assigned'],
            aggregate_data['re_assigned'],
            aggregate_data['completed'],
            aggregate_data['cancelled'],
            aggregate_data['inprogress'],
            aggregate_data['closed']
        ]

        data = stats,sum(stats)
        return data
    
    def get_events_for_calendar(self, request):
        from apps.work_order_management.models import Wom
        S,R = request.session, request.GET
        
        start_date = datetime.strptime(R['start'], "%Y-%m-%dT%H:%M:%S%z").date()
        end_date = datetime.strptime(R['end'], "%Y-%m-%dT%H:%M:%S%z").date()

        qset = self.annotate(
            start=Cast(F('plandatetime'), output_field=CharField()),
            end=Cast(F('expirydatetime'), output_field=CharField()),
            title = Case(When(workpermit = 'NOT_REQUIRED', then = F('description') ), default=F('qset__qsetname'), output_field=CharField()),
            color = Case(
                When(workstatus__exact = Wom.Workstatus.CANCELLED, then = V('#727272')),
                When(workstatus__exact = Wom.Workstatus.REASSIGNED, then= V( '#004679')),
                When(workstatus__exact = Wom.Workstatus.INPROGRESS, then= V( '#b87707')),
                When(workstatus__exact = Wom.Workstatus.CLOSED, then= V( '#13780e')),
                When(workstatus__exact = Wom.Workstatus.COMPLETED, then=V('#0d96ab')),
                When(workstatus__exact = Wom.Workstatus.ASSIGNED, then=V('#a14020')),
                output_field=CharField()
            )
        ).filter(
            cdtz__date__gte = start_date,
            cdtz__date__lte = end_date,
            bu_id = S['bu_id'],
            client_id = S['client_id']
        )
        
        if R['eventType'] == 'Work Orders':
            qset = qset.filter(workpermit = Wom.WorkPermitStatus.NOTNEED)
        else:
            qset = qset.filter(~Q(workpermit = Wom.WorkPermitStatus.NOTNEED))
        qset = qset.values('id', 'start', 'end', 'title','color')
        return qset or self.none()
    
    
    def get_attachments(self, id):
        if qset := self.filter(id=id).values('uuid'):
            if atts := self.get_atts(qset[0]['uuid']):
                return atts or self.none()
        return self.none()

    
    def get_atts(self, uuid):
        from apps.activity.models.attachment_model import Attachment
        if atts := Attachment.objects.annotate(
            file = Concat(V(settings.MEDIA_URL, output_field=models.CharField()),
                          F('filepath'),
                          V('/'), Cast('filename', output_field=models.CharField())),
            location = AsGeoJSON('gpslocation')
            ).filter(owner = uuid).values(
            'filepath', 'filename', 'attachmenttype', 'datetime', 'location', 'id', 'file'
            ):return atts
        return self.none()
    
    def get_wom_records_for_mobile(self, fromdate, todate, peopleid, workpermit, buid, clientid, parentid):
        from apps.peoples.models import People
        from apps.work_order_management.models import Approver
        people = People.objects.get(id=peopleid)
        workpermit_statuses = workpermit.replace(', ', ',').split(',')
        fields = ['cuser_id', 'muser_id', 'cdtz', 'mdtz', 'ctzoffset','description', 'uuid', 'plandatetime',
                  'expirydatetime', 'starttime', 'endtime', 'gpslocation', 'location_id', 'asset_id',
                  'workstatus', 'workpermit', 'priority','parent_id', 'alerts', 'permitno', 'approverstatus', 
                  'performedby','ismailsent', 'isdenied', 'client_id', 'bu_id', 'approvers', 'id','verifiers','verifierstatus','vendor_id','qset_id__qsetname']
        
        try:
            identifier = Approver.objects.get(people_id=peopleid, approverfor='{WORKPERMIT}').identifier
        except Approver.DoesNotExist:
            identifier = None
        
        if identifier == 'APPROVER':
            qset = self.select_related().annotate(
                permitno = F('other_data__wp_seqno'),
                approverstatus = F('other_data__wp_approvers'),
                verifierstatus = F('other_data__wp_verifiers')
                ).filter(
                Q(cuser_id = peopleid) | Q(muser_id=peopleid) | Q(approvers__contains = [people.peoplecode])|Q(verifiers__contains = [people.peoplecode]),
                cdtz__date__gte = fromdate,
                cdtz__date__lte = todate,
                workpermit__in = workpermit_statuses,
                bu_id = buid,
                client_id = clientid,
                parent_id=parentid,
                verifiers_status='APPROVED',
                identifier='WP'
            ).values(*fields).order_by('-cdtz')
        else:
            qset = self.select_related().annotate(
                permitno = F('other_data__wp_seqno'),
                approverstatus = F('other_data__wp_approvers'),
                verifierstatus = F('other_data__wp_verifiers')
                ).filter(
                Q(cuser_id = peopleid) | Q(muser_id=peopleid) | Q(approvers__contains = [people.peoplecode])|Q(verifiers__contains = [people.peoplecode]),
                cdtz__date__gte = fromdate,
                cdtz__date__lte = todate,
                workpermit__in = workpermit_statuses,
                bu_id = buid,
                client_id = clientid,
                parent_id=parentid,
                identifier='WP'
            ).values(*fields).order_by('-cdtz')
        return qset or self.none()
    
    
    def get_empty_rwp_section(self):
        return {
            'section':'THIS SECTION TO BE COMPLETED ON RETURN OF PERMIT',
            'questions':[
                {
                    'question__quesname':'Permit Returned at',
                    'answer':'',
                },
                {
                    'question__quesname':'Work Checked at',
                    'answer':'',
                },
                {
                    'question__quesname':'Name of Requester',
                    'answer':'',
                }
            ]
        }

    def wp_data_for_report(self, id):
        site = self.filter(id=id).first().bu
        wp_answers = self.get_wp_answers(id)
        wp_info = wp_answers[0]
        wp_answers.pop(0)
        rwp_section = wp_answers.pop(-1)
        if rwp_section['section'] == 'EMAIL':
            rwp_section = self.get_empty_rwp_section()
        wp_sections = wp_answers
        return wp_info, wp_sections, rwp_section, site.buname
    
    
    def get_sla_answers(self,slaid):
        child_slarecords = self.filter(parent_id = slaid).order_by('seqno')
        # work_permit_no = childwoms[0].other_data['wp_seqno']
        sla_details = []
        overall_score = []
        all_questions = []
        all_answers = []
        all_average_score = []
        remarks = []
        for child_sla in child_slarecords:
            section_weight = child_sla.other_data['section_weightage']
            ans = []
            answers = child_sla.womdetails_set.values('answer')
            for answer in answers:
                if answer['answer'].isdigit():
                    if int(answer['answer']) <=10:
                        all_answers.append(int(answer['answer']))
                        ans.append(int(answer['answer']))
                else:
                    remarks.append(answer['answer'])
            questions = child_sla.womdetails_set.values('question__quesname')
            for que in questions:
                all_questions.append(que['question__quesname'])
            if sum(ans)== 0 or len(ans)== 0:
                average_score = 0
            else:
                average_score = sum(ans)/len(ans)
            all_average_score.append(round(average_score,1))
            score = average_score * section_weight
            overall_score.append(score)
            sq = {
                "section":child_sla.description,
                "sectionID":child_sla.seqno,
                "section_weightage":child_sla.other_data['section_weightage']
            }

            sla_details.append(sq)
        overall_score = sum(overall_score)
        question_ans = dict(zip(all_questions,all_answers))
        final_overall_score = overall_score * 10
        rounded_overall_score = round(final_overall_score,2)
        wom_ele = self.model.objects.get(id=slaid)
        wom_ele.other_data['overall_score'] = rounded_overall_score
        remarks = remarks[-1] if len(remarks) > 0 else ''
        wom_ele.other_data['remarks'] = remarks
        wom_ele.save()
        return sla_details,rounded_overall_score,question_ans,all_average_score,remarks or self.none()

        

    def sla_data_for_report(self,id):
        sla_answers,overall_score,question_ans,all_average_score,remarks = self.get_sla_answers(id)
        return sla_answers,overall_score,question_ans,all_average_score,remarks

    def convert_the_queryset_to_list(self,workpermit_sections):
        questions = workpermit_sections.get('questions')
        questions_in_list = list(questions.values('question__quesname','answer'))
        workpermit_sections.pop('questions')
        workpermit_sections['questions'] = questions_in_list
        return workpermit_sections

    def extract_question_from_general_details(self, new_general_details,id,approval_status):
        permit_initiated_by = "" 
        permit_authorized_by = "" 
        workpermit = ""
        permit_valid_upto = ""
        permit_valid_from = ""
        for question in new_general_details['questions']:
            quesname = question['question__quesname'].lower()  # Convert to lowercase for case-insensitive comparison
            if quesname == 'permit initiated by':
                permit_initiated_by = question['answer']
            elif quesname == 'permit authorized by':
                permit_authorized_by = question['answer'].split(',')
            elif quesname == 'type of permit':
                workpermit = question['answer']
            elif quesname == 'permit valid from':
                permit_valid_from = question['answer']
            elif quesname == 'permit valid upto':
                permit_valid_upto = question['answer']
        from apps.work_order_management.models import Wom
            
        approvers = []
        wom = Wom.objects.get(id=id)
        permit_authorized_by = wom.approvers
        for code in permit_authorized_by:
            people = People.objects.get(peoplecode = code)
            approvers.append(people.peoplename)
        
        
        data = {
            'permit_initiated_by': permit_initiated_by,
            'permit_authorized_by': approvers if approval_status == 'APPROVED' else "",
            'workpermit': workpermit,
            'permit_valid_from': permit_valid_from,
            'permit_valid_upto': permit_valid_upto
        }
        return data
    
    def extract_questions_from_section_five(self,new_section_details_five):
        permit_returned_at = ""
        work_checked_at = ""
        name_of_requester = ""

        for question in new_section_details_five['questions']:
            if question['question__quesname'] == 'PERMIT RETURNED AT':
                permit_returned_at = question['answer']
            elif question['question__quesname'] == 'WORK CHECKED AT':
                work_checked_at = question['answer']
            elif question['question__quesname'] == 'Name Of Requester':
                name_of_requester = question['answer']
        
        section_data = {
            'permit_returned_at':permit_returned_at,
            'work_checked_at':work_checked_at,
            'name_of_requester':name_of_requester
        }
        return section_data

    def extract_questions_from_section_one(self,new_section_details_one):
        name_of_supervisor = ""
        name_of_persons_involved = "" 
        other_control_measures = "" 
        debris_cleared = "" 
        department = "" 
        area_building = ""
        location = ""
        job_description = ""
        employees_contractors = ""
        workmen_fitness = ""
        for question in new_section_details_one['questions']:
            if question['question__quesname'] == 'Name of the Supervisors/Incharge':
                name_of_supervisor = question['answer']
            elif question['question__quesname'] == 'Name of the persons involved':
                name_of_persons_involved = question['answer']
            elif question['question__quesname'] == 'Debris are Cleared and kept at':
                debris_cleared = question['answer']
            elif question['question__quesname'] == 'Any Other or additional control measures if required':
                other_control_measures = question['answer']
            elif question['question__quesname'] == 'Department':
                department = question['answer']
            elif question['question__quesname'] == 'Area/Building':
                area_building = question['answer']
            elif question['question__quesname'] == 'Location':
                location = question['answer']
            elif question['question__quesname'] == 'Job Description':
                job_description = question['answer']
            elif question['question__quesname'] == "Name of the Employees/Contractor's":
                employees_contractors = question['answer']
            elif question['question__quesname'] == "Workmen Fitness":
                workmen_fitness = question['answer']

            section_data = {
                'name_of_supervisor':name_of_supervisor,
                'name_of_persons_involved':name_of_persons_involved,
                'debris_cleared':debris_cleared,
                'other_control_measures':other_control_measures,
                'department':department,
                'area_building':area_building,
                'location':location,
                'job_description':job_description,
                'employees_contractors':employees_contractors,
                'workmen_fitness':workmen_fitness
            }
        return section_data
    

    def get_wp_sections_answers(self,wp_answers,id,approval_status):
        general_details = wp_answers[0]
        section_details_one = wp_answers[1]
        section_details_two = wp_answers[2]
        section_details_three = wp_answers[3]

        # Converting the queryset to list
        new_general_details = self.convert_the_queryset_to_list(general_details)
        new_section_details_one = self.convert_the_queryset_to_list(section_details_one)
        new_section_details_two = self.convert_the_queryset_to_list(section_details_two)
        new_section_details_three = self.convert_the_queryset_to_list(section_details_three)
        

        # Extracting the questions from the queryset
        general_details_data = self.extract_question_from_general_details(new_general_details,id,approval_status)
        section_one_data = self.extract_questions_from_section_one(new_section_details_one)
        

        # Creating the final data
        name_of_supervisor = section_one_data['name_of_supervisor']
        name_of_persons_involved = section_one_data['name_of_persons_involved']
        department = section_one_data['department']
        area_building = section_one_data['area_building']
        location = section_one_data['location']
        job_description = section_one_data['job_description']
        employees_contractors = section_one_data['employees_contractors']
        workmen_fitness = section_one_data['workmen_fitness']
        other_control_measures = section_one_data['other_control_measures']
        debris_cleared = section_one_data['debris_cleared']
        permit_authorized_by = general_details_data['permit_authorized_by']
        permit_initiated_by = general_details_data['permit_initiated_by']
        workpermit = general_details_data['workpermit']
        permit_valid_from = general_details_data['permit_valid_from']
        permit_valid_upto = general_details_data['permit_valid_upto']

        data = {
            'department':department,
            'area_building':area_building,
            'location':location,
            'job_description':job_description,
            'employees_contractors':employees_contractors,
            'workmen_fitness':workmen_fitness,
            'permit_authorized_by':permit_authorized_by,
            'permit_initiated_by':permit_initiated_by,
            'name_of_supervisor':name_of_supervisor,
            'name_of_persons_involved':name_of_persons_involved,
            'other_control_measures':other_control_measures,
            'debris_cleared':debris_cleared,
            'new_section_details_two':new_section_details_two['questions'],
            'new_section_details_three':new_section_details_three['questions'],
            'workpermit':workpermit,
            'permit_valid_from':permit_valid_from,
            'permit_valid_upto':permit_valid_upto,
            'permit_returned_at':"",
            'work_checked_at':"",
            'name_of_requester':""
        }

        if len(wp_answers)==6:
            section_details_five = wp_answers[5]
            new_section_details_five = self.convert_the_queryset_to_list(section_details_five)
            section_five_data = self.extract_questions_from_section_five(new_section_details_five)
            permit_returned_at = section_five_data['permit_returned_at']
            work_checked_at = section_five_data['work_checked_at']  
            name_of_requester = section_five_data['name_of_requester']
            data['permit_returned_at'] = permit_returned_at
            data['work_checked_at'] = work_checked_at
            data['name_of_requester'] = name_of_requester

        return data
    
    def get_workpermit_count(self, request):
        R, S = request.GET, request.session
        pd1 = R.get('from', datetime.now().date())
        pd2 = R.get('upto', datetime.now().date())
        qobjs = self.select_related('cuser', 'bu', 'qset','vendor').filter(
        ~Q(workpermit__in =  ['NOT_REQUIRED', 'NOTREQUIRED']),
            ~Q(identifier = 'SLA'),
            parent_id = 1,
            client_id = S['client_id'],
            bu_id = S['bu_id'],
            cdtz__date__gte = pd1,
            cdtz__date__lte = pd2,
        ).count()
        return qobjs


class WOMDetailsManager(models.Manager):
    use_in_migrations = True
    def get_wo_details(self, womid):
        if womid in [None, 'None', '']: return self.none()
        qset = self.filter(
            wom_id = womid
        ).select_related('question').values('question__quesname', 'answertype', 'min', 'max', 'id',
            'options', 'alerton', 'ismandatory', 'seqno','answer', 'alerts').order_by('seqno')
        return qset or self.none()
    
    def getAttachmentJND(self, id):
        if qset := self.filter(id=id).values('uuid'):
            if atts := self.get_atts(qset[0]['uuid']):
                return atts or self.none()
        return self.none()
    
    def get_atts(self, uuid):
        from apps.activity.models.attachment_model import Attachment
        from django.conf import settings
        if atts := Attachment.objects.annotate(
            file = Concat(V(settings.MEDIA_URL, output_field=models.CharField()), F('filepath'),
                          V('/'), Cast('filename', output_field=models.CharField()))
            ).filter(owner = uuid).values(
            'filepath', 'filename', 'attachmenttype', 'datetime',  'id', 'file'
            ):return atts
        return self.none()
    
    
    