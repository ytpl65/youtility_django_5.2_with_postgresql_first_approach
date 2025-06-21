# Celery removed - tasks now run via PostgreSQL Task Queue
# from intelliwiz_config.celery import app
# from celery import shared_task
from background_tasks import utils as butils
from apps.core import utils
from django.apps import apps
from logging import getLogger
from django.db import transaction
from datetime import timedelta, datetime
import traceback as tb
from apps.core.raw_queries import get_query
from pprint import pformat
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
import base64, os, json
from django.core.mail import EmailMessage
from apps.reports.models import ScheduleReport
from apps.reports import utils as rutils
from django.templatetags.static import static
import logging
import time 

mqlog = getLogger('message_q')
tlog = getLogger('tracking')
logger = logging.getLogger('django')

from .move_files_to_GCS import move_files_to_GCS, del_empty_dir, get_files
from .report_tasks import (
    get_scheduled_reports_fromdb, generate_scheduled_report, handle_error,  
    walk_directory, get_report_record, check_time_of_report, 
    remove_reportfile, save_report_to_tmp_folder)
from io import BytesIO

# from celery import shared_task  # Removed - using PostgreSQL Task Queue
from mqtt_utils import publish_message





def publish_mqtt(topic, payload):
    try:
        publish_message(topic, payload)
        logger.info(f"[PostgreSQL Task Queue] Task completed: topic={topic}")
    except Exception as e:
        logger.error(f"[PostgreSQL Task Queue] Task failed! Error: {e}", exc_info=True)
        raise



# @app.task(bind=True, default_retry_delay=300, max_retries=5, name="send_ticket_email")  # Removed - using PostgreSQL Task Queue
def send_ticket_email(ticket=None, id=None):
    from apps.y_helpdesk.models import Ticket
    from django.conf import settings
    from django.template.loader import render_to_string
    try:
        if not ticket and id:
            ticket = Ticket.objects.get(id=id)
        if ticket:
            logger.info(f"ticket found with ticket id: {ticket.ticketno}")
            logger.info("ticket email sending start ")
            resp = {}
            emails = butils.get_email_recipents_for_ticket(ticket)
            logger.info(f"email addresses of recipents: {emails}")
            updated_or_created = "Created" if ticket.cdtz == ticket.mdtz else "Updated"
            context = {
                'subject': f"Ticket with #{ticket.ticketno} is {updated_or_created} at site: {ticket.bu.buname}",
                'desc': ticket.ticketdesc,
                'template': ticket.ticketcategory.taname,
                'status': ticket.status,
                'createdon': ticket.cdtz.strftime("%Y-%m-%d %H:%M:%S"),
                'modifiedon': ticket.mdtz.strftime("%Y-%m-%d %H:%M:%S"),
                'modifiedby': ticket.muser.peoplename,
                'assignedto': ticket.assignedtogroup.groupname if ticket.assignedtopeople_id in [None, 1] else ticket.assignedtopeople.peoplename,
                'comments': ticket.comments,
                "priority": ticket.priority,
                'level': ticket.level
            }
            logger.info(f'context for email template: {context}')
            html_message = render_to_string('y_helpdesk/ticket_email.html', context)
            msg = EmailMessage()
            msg.body = html_message
            msg.to = emails
            msg.subject = context['subject']
            msg.from_email = settings.EMAIL_HOST_USER
            msg.content_subtype = 'html'
            msg.send()
            logger.info("ticket email sent")
        else:
            logger.info('ticket not found no emails will send')
    except Exception as e:
        logger.critical("Error while sending ticket email", exc_info=True)
        resp['traceback'] = tb.format_exc()
    return resp


def autoclose_job(jobneedid=None):
    from django.template.loader import render_to_string
    from django.conf import settings
    context = {}
    try:
        # get all expired jobs
        Jobneed = apps.get_model('activity', 'Jobneed')
        resp = {'story': "", 'traceback': "", 'id': []}
        expired = Jobneed.objects.get_expired_jobs(id=jobneedid)
        resp['story'] += f'total expired jobs = {len(expired)}\n'
        with transaction.atomic(using=utils.get_current_db_name()):
            resp['story'] += f"using database: {utils.get_current_db_name()}\n"
            for rec in expired:
                resp['story'] += f"processing record with id= {rec['id']}\n"
                resp['story'] += f"record category is {rec['ticketcategory__tacode']}\n"

                if rec['ticketcategory__tacode'] in ['AUTOCLOSENOTIFY', 'RAISETICKETNOTIFY']:

                    logger.info("notifying through email...")
                    pdate = rec["plandatetime"] + \
                        timedelta(minutes=rec['ctzoffset'])
                    pdate = pdate.strftime("%d-%b-%Y %H:%M")
                    edate = rec["expirydatetime"] + \
                        timedelta(minutes=rec['ctzoffset'])
                    edate = edate.strftime("%d-%b-%Y %H:%M")

                    subject = f'AUTOCLOSE {"TOUR" if rec["identifier"] in  ["INTERNALTOUR", "EXTERNALTOUR"] else rec["identifier"] } planned on \
                    {pdate} not reported in time'
                    context = {
                        'subject': subject,
                        'buname': rec['bu__buname'],
                        'plan_dt': pdate,
                        'creatorname': rec['cuser__peoplename'],
                        'assignedto': rec['assignedto'],
                        'exp_dt': edate,
                        'show_ticket_body': False,
                        'identifier': rec['identifier'],
                        'jobdesc': rec['jobdesc']
                    }

                    emails = butils.get_email_recipients(rec['bu_id'], rec['client_id'])
                    resp['story'] += f"email recipents are as follows {emails}\n"
                    logger.info(f"recipents are as follows...{emails}")
                    msg = EmailMessage()
                    msg.subject = subject
                    msg.from_email = settings.EMAIL_HOST_USER
                    msg.to = emails
                    msg.content_subtype = 'html'

                    if rec['ticketcategory__tacode'] == 'RAISETICKETNOTIFY':
                        logger.info("ticket needs to be generated")
                        context['show_ticket_body'] = True
                        jobdesc = f'AUTOCLOSED {"TOUR" if rec["identifier"] in  ["INTERNALTOUR", "EXTERNALTOUR"] else rec["identifier"] } planned on {pdate} not reported in time'
                        # DB OPERATION
                        ticket_data = butils.create_ticket_for_autoclose(
                            rec, jobdesc)
                        logger.info(f'{ticket_data}')
                        if esc := butils.get_escalation_of_ticket(ticket_data) and esc['frequencyvalue'] and esc['frequency']:
                            context['escalation'] = True
                            context['next_escalation'] = f"{esc['frequencyvalue']} {esc['frequency']}"
                        created_at = ticket_data['cdtz'] + \
                            timedelta(minutes=ticket_data['ctzoffset'])
                        created_at = created_at.strftime("%d-%b-%Y %H:%M")

                        context['ticketno'] = ticket_data['ticketno']
                        context['tjobdesc'] = jobdesc
                        context['categoryname'] = rec['ticketcategory__taname']
                        context['priority'] = rec['priority']
                        context['status'] = 'NEW'
                        context['tcreatedby'] = rec['cuser__peoplename']
                        context['created_at'] = created_at
                        context['tkt_assignedto'] = rec['assignedto']

                    html_message = render_to_string(
                        'activity/autoclose_mail.html', context=context)
                    resp['story'] += f"context in email template is {context}\n"
                    msg.body = html_message
                    msg.send()
                    logger.info(f"mail sent, record_id:{rec['id']}")
                resp = butils.update_job_autoclose_status(rec, resp)

    except Exception as e:
        logger.critical(f'context in the template:{context}', exc_info=True)
        logger.error(
            "something went wrong while running autoclose_job()", exc_info=True)
        resp['traceback'] += f"{tb.format_exc()}"
    return resp

# Alias for compatibility with test script
auto_close_jobs = autoclose_job

def ticket_escalation():
    result = {'story': "", 'traceback': "", 'id': []}
    try:
        # get all records of tickets which can be escalated
        tickets = utils.runrawsql(get_query('get_ticketlist_for_escalation'))
        result['story'] = f"Total tickets found for escalation are {len(tickets)}\n"
        # update ticket_history, assignments to people & groups, level, mdtz, modifiedon
        result = butils.update_ticket_data(tickets, result)
    except Exception as e:
        logger.critical("somwthing went wrong while ticket escalation", exc_info=True)
        result['traceback'] = tb.format_exc()
    return result


def send_reminder_email():
    from django.template.loader import render_to_string
    from django.conf import settings
    from apps.reminder.models import Reminder

    resp = {'story': "", "traceback": "", 'id': []}
    # get all reminders which are not sent
    reminders = Reminder.objects.get_all_due_reminders()
    resp['story'] += f"total due reminders are: {len(reminders)}\n"
    logger.info(f"total due reminders are {len(reminders)}")
    try:
        for rem in reminders:
            resp['story'] += f"processing reminder with id: {rem['id']}"
            emails = utils.get_email_addresses(
                [rem['people_id'], rem['cuser_id'], rem['muser_id']], [rem['group_id']])
            resp['story'] += f"emails recipents are as follows {emails}\n"
            recipents = list(set(emails + rem['mailids'].split(',')))
            subject = f"Reminder For {rem['job__jobname']}"
            context = {'job': rem['job__jobname'], 'plandatetime': rem['pdate'], 'jobdesc': rem['job__jobdesc'], 'sitename': rem['bu__buname'],
                       'creator': rem['cuser__peoplename'], 'modifier': rem['muser__peoplename'], 'subject': subject}
            html_message = render_to_string(
                'activity/reminder_mail.html', context=context)
            resp['story'] += f"context in email template is {context}\n"
            logger.info(f"Sending reminder mail with subject {subject}")

            msg = EmailMessage()
            msg.subject = subject
            msg.body = html_message
            msg.from_email = settings.EMAIL_HOST_USER
            msg.to = recipents
            msg.content_subtype = 'html'
            # returns 1 if mail sent successfully else 0
            if is_mail_sent := msg.send(fail_silently=True):
                Reminder.objects.filter(id=rem['id']).update(
                    status="SUCCESS", mdtz=timezone.now())
            else:
                Reminder.objects.filter(id=rem['id']).update(
                    status="FAILED", mdtz=timezone.now())
            resp['id'].append(rem['id'])
            logger.info(
                f"Reminder mail sent to {recipents} with subject {subject}")
    except Exception as e:
        logger.critical("Error while sending reminder email", exc_info=True)
        resp['traceback'] = tb.format_exc()
    return resp


def create_ppm_job(jobid=None):
    F, d = {}, []
    #resp = {'story':"", 'traceback':""}
    startdtz = enddtz = msg = resp = None
    
    from apps.activity.models.job_model import Job
    from apps.activity.models.asset_model import Asset

    from apps.schedhuler.utils import (calculate_startdtz_enddtz_for_ppm, get_datetime_list,
                                       insert_into_jn_and_jnd, get_readable_dates, create_ppm_reminder)
    result = {'story': "", "traceback": "", 'id': []}

    try:
        # atomic transaction
        with transaction.atomic(using=utils.get_current_db_name()):
            if jobid:
                jobs = Job.objects.filter(id=jobid).values(
                    *utils.JobFields.fields)
            else:
                jobs = Job.objects.filter(
                    ~Q(jobname='NONE'),
                    ~Q(asset__runningstatus=Asset.RunningStatus.SCRAPPED),
                    identifier=Job.Identifier.PPM.value,
                    parent_id=1
                ).select_related('asset', 'pgroup', 'cuser', 'muser', 'people', 'qset').values(
                    *utils.JobFields.fields
                )

            if not jobs:
                msg = "No jobs found schedhuling terminated"
                result['story'] += f"{msg}\n"
                logger.warning(f"{msg}", exc_info=True)
            total_jobs = len(jobs)

            if total_jobs > 0 and jobs is not None:
                logger.info("processing jobs started found:= '%s' jobs", (len(jobs)))
                result['story'] += f"total jobs found {total_jobs}\n"
                for job in jobs:
                    result['story'] += f'\nprocessing job with id: {job["id"]}'
                    startdtz, enddtz = calculate_startdtz_enddtz_for_ppm(job)
                    logger.debug(
                        f"Jobs to be schedhuled from startdatetime {startdtz} to enddatetime {enddtz}")
                    DT, is_cron, resp = get_datetime_list(
                        job['cron'], startdtz, enddtz, resp)
                    if not DT:
                        resp = {
                            'msg': "Please check your Valid From and Valid To dates"}
                        continue
                    logger.debug(
                        "Jobneed will going to create for all this datetimes\n %s", (pformat(get_readable_dates(DT))))
                    if not is_cron:
                        F[str(job['id'])] = {'cron': job['cron']}
                    status, resp = insert_into_jn_and_jnd(job, DT, resp)
                    if status:
                        d.append({
                            "job": job['id'],
                            "jobname": job['jobname'],
                            "cron": job['cron'],
                            "iscron": is_cron,
                            "count": len(DT),
                            "status": status
                        })
                create_ppm_reminder(d)
                if F:
                    result['story'] += f'create_ppm_job failed job schedule list {pformat(F)}\n'
                    logger.info(
                        f"create_ppm_job Failed job schedule list:={pformat(F)}")
                    for key, value in list(F.items()):
                        logger.info(
                            f"create_ppm_job job_id: {key} | cron: {value}")
    except Exception as e:
        logger.critical("something went wrong create_ppm_job", exc_info=True)
        F[str(job['id'])] = {'tb': tb.format_exc()}

    return resp, F, d, result


#@app.task(bind=True, default_retry_delay=300, max_retries=5, name='perform_facerecognition_bgt')
def perform_facerecognition_bgt(pel_uuid, peopleid, db='default'):
    result = {'story': "perform_facerecognition_bgt()\n", "traceback": ""}
    result['story'] += f"inputs are {pel_uuid = } {peopleid = }, {db = }\n"
    starttime = time.time()
    # Threshold for 85% similarity (0.15 in cosine distance metric)
    threshold = 0.15
    
    try:
        logger.info("perform_facerecognition ...start [+]")
        with transaction.atomic(using=utils.get_current_db_name()):
            utils.set_db_for_router(db)
            if pel_uuid not in [None, 'NONE', '', 1] and peopleid not in [None, 'NONE', 1, ""]:
                # Retrieve the event picture
                Attachment = apps.get_model('activity', 'Attachment')
                pel_att = Attachment.objects.get_people_pic(pel_uuid, db)  # people event pic
                
                # Retrieve the default profile picture of the person
                People = apps.get_model('peoples', 'People')
                people_obj = People.objects.get(id=peopleid)
                default_peopleimg = f'{settings.MEDIA_ROOT}/{people_obj.peopleimg.url.replace("/youtility4_media/", "")}'
                
                # Use a placeholder image if the default one is blank
                default_peopleimg = static('assets/media/images/blank.png') if default_peopleimg.endswith('blank.png') else default_peopleimg  
                
                if default_peopleimg and pel_att.people_event_pic:
                    images_info = f"default image path:{default_peopleimg} and uploaded file path:{pel_att.people_event_pic}"
                    logger.info(f'{images_info}')
                    result['story'] += f'{images_info}\n'
                    
                    # Perform face verification using DeepFace
                    from deepface import DeepFace
                    fr_results = DeepFace.verify(
                        img1_path=default_peopleimg, 
                        img2_path=pel_att.people_event_pic, 
                        threshold=0.4,
                        enforce_detection=True, 
                        detector_backend='mtcnn', 
                        model_name='Facenet512',  # Using a stronger model
                        distance_metric='cosine'  # Cosine distance metric for similarity comparison
                    )
                    
                    logger.info(f"deepface verification completed and results are {fr_results}")
                    result['story'] += f"deepface verification completed and results are {fr_results}\n"
                    
                    # Manually check the distance against the 85% threshold (0.15)
                    if fr_results['distance'] <= threshold:
                        logger.info(f"Faces match with at least 85% similarity")
                        result['story'] += f"Faces match with at least 85% similarity\n"
                    else:
                        logger.info(f"Faces do not match (distance {fr_results['distance']} > {threshold})")
                        result['story'] += f"Faces do not match (distance {fr_results['distance']} > {threshold})\n"
                    
                    # Update the face recognition results in the event logger
                    PeopleEventlog = apps.get_model('attendance', 'PeopleEventlog')
                    logger.info("%s %s %s",fr_results,pel_uuid,peopleid)
                    if PeopleEventlog.objects.update_fr_results(fr_results, pel_uuid, peopleid, db):
                        logger.info("updation of fr_results in peopleeventlog is completed...")
    except ValueError as v:
        logger.error("face recognition image not found or face is not there...", exc_info=True)
        result['traceback'] += f'{tb.format_exc()}'
    except Exception as e:
        logger.critical("something went wrong! while performing face-recognition in background", exc_info=True)
        result['traceback'] += f'{tb.format_exc()}'
        raise
    endtime = time.time()
    total_time = endtime - starttime
    logger.info(f'Total time take for this function is {total_time}')
    return result



# alert_sendmail
def alert_sendmail(id, event, atts=False):
    '''
    takes uuid, ownername (which is the model name) and event (observation or deviation)
    gets the record from model if record has alerts set to true then send mail based on event
    '''
    Jobneed = apps.get_model('activity', 'Jobneed')
    from .utils import alert_deviation, alert_observation
    obj = Jobneed.objects.filter(id=id).first()
    if event == 'observation' and obj:
        return alert_observation(obj, atts)
    if event == 'deviation' and obj:
        return alert_deviation(obj, atts)


def task_every_min():
    from django.utils import timezone
    return f"task completed at {timezone.now()}"



def send_report_on_email(formdata, json_report):
    
    import mimetypes
    import json
    jsonresp = {"story": "", "traceback": ""}
    try:
        jsonresp['story'] += f'formdata: {formdata}'
        file_buffer = BytesIO()
        jsonrep = json.loads(json_report)
        report_content = base64.b64decode(jsonrep['report'])
        file_buffer.write(report_content)
        file_buffer.seek(0)
        mime_type, encoding = mimetypes.guess_type(f'.{formdata["format"]}')
        email = EmailMessage(
            subject=f"Per your request, please find the report attached from {settings.COMPANYNAME}",
            from_email=settings.EMAIL_HOST_USER,
            to=formdata['to_addr'],
            cc=formdata['cc'],
            body=formdata.get('email_body'),
        )
        email.attach(
            filename=f'{formdata["report_name"]}.{formdata["format"]}',
            content=file_buffer.getvalue(),
            mimetype=mime_type
        )
        email.send()
        jsonresp['story'] += "email sent"
    except Exception as e:
        logger.critical(
            "something went wrong while sending report on email", exc_info=True)
        jsonresp['traceback'] = tb.format_exc()
    return jsonresp



def create_report_history(formdata, userid, buid, EI):
    jsonresp = {'story': "", "traceback": ""}
    try:
        ReportHistory = apps.get_model('reports', "ReportHistory")
        obj = ReportHistory.objects.create(
            traceback=EI[2] if EI[0] else None,
            user_id=userid,
            report_name=formdata['report_name'],
            params={"params": f"{formdata}"},
            export_type=formdata['export_type'],
            bu_id=buid,
            ctzoffset=formdata['ctzoffset'],
            cc_mails=formdata['cc'],
            to_mails=formdata['to_addr'],
            email_body=formdata['email_body'],
        )
        jsonresp['story'] += f"A Report history object created with pk: {obj.pk}"
    except Exception as e:
        logger.critical(
            "something went wron while running create_report_history()", exc_info=True)
        jsonresp['traceback'] += tb.format_exc()
    return jsonresp


def send_email_notification_for_workpermit_approval(womid,approvers,approvers_code,sitename,workpermit_status,permit_name,workpermit_attachment,vendor_name,client_id):
    jsonresp = {'story': "", "traceback": ""}
    try:
        from django.apps import apps 
        from django.template.loader import render_to_string
        Wom = apps.get_model('work_order_management', 'Wom')
        People = apps.get_model('peoples', 'People')
        wp_details = Wom.objects.get_wp_answers(womid)
        wp_obj = Wom.objects.get(id=womid)
        # logger.info(f"wp_details: {wp_details}")
        logger.info(f"Approvers: {approvers}")
        jsonresp['story'] += f"\n{wp_details}"
        logger.info(f"WP Details{wp_details}")
        if wp_details:
            qset = People.objects.filter(peoplecode__in = approvers_code)
            logger.info(f"Qset {qset}")
            for p in qset.values('email','id'):
                logger.info(f"Sending Email to {p['email'] = }")
                logger.info(f"{permit_name}-{wp_obj.other_data['wp_seqno']}-{sitename}-Approval Pending")
                msg = EmailMessage()
                msg.subject = f"{permit_name}-{wp_obj.other_data['wp_seqno']}-{sitename}-Approval Pending"            
                msg.to = [p['email']]
                msg.from_email = settings.EMAIL_HOST_USER
                cxt = {
                    'peopleid':p['id'],
                    'HOST':settings.HOST,
                    'workpermitid':womid,
                    'sitename':sitename,
                    'status':workpermit_status,
                    'permit_no':wp_obj.other_data['wp_seqno'],
                    'permit_name':permit_name,
                    'vendor_name':vendor_name,
                    'client_id':client_id,
                }
                logger.info(f'Context: {cxt}')
                html = render_to_string(
                    'work_order_management/workpermit_approver_action.html',context=cxt
                )
                msg.body = html
                msg.content_subtype = 'html'
                logger.info(f'Attachment {workpermit_attachment}')
                msg.attach_file(workpermit_attachment, mimetype='application/pdf')
                msg.send()
                logger.info(f"Email sent to {p['email'] = }")
                jsonresp['story']+=f"Email sent to {p['email'] = }"
        jsonresp['story'] += f"A {permit_name} email sent of pk: {womid}: "
    except Exception as e:
        logger.critical(
            "Something went wrong while running send_email_notification_for_wp_verifier",exc_info=True
            )
        jsonresp['traceback'] += tb.format_exc()
    return jsonresp

def send_email_notification_for_wp_verifier(womid,verifiers,sitename,workpermit_status,permit_name,vendor_name,client_id,workpermit_attachment=None):
    jsonresp = {'story': "", "traceback": ""}
    try:
        from django.apps import apps 
        from django.template.loader import render_to_string
        Wom = apps.get_model('work_order_management', 'Wom')
        People = apps.get_model('peoples', 'People')
        wp_details = Wom.objects.get_wp_answers(womid)
        wp_obj = Wom.objects.get(id=womid)
        permit_no = wp_obj.other_data['wp_seqno']
        jsonresp['story'] += f"\n{wp_details}"
        if wp_details:
            qset = People.objects.filter(peoplecode__in = verifiers)
            for p in qset.values('email','id'):
                logger.info(f"Sending Email to {p['email'] = }")
                msg = EmailMessage()
                msg.subject = f"{permit_name}-{wp_obj.other_data['wp_seqno']}-{sitename}-Verification Pending"            
                msg.to = [p['email']]
                msg.from_email = settings.EMAIL_HOST_USER
                cxt = {
                    'peopleid':p['id'],
                    'HOST':settings.HOST,
                    'workpermitid':womid,
                    'sitename':sitename,
                    'status':workpermit_status,
                    'permit_no':wp_obj.other_data['wp_seqno'],
                    'permit_name':permit_name,
                    'vendor_name':vendor_name,
                    'client_id':client_id
                }
                html = render_to_string(
                    'work_order_management/workpermit_verifier_action.html',context=cxt
                )
                msg.body = html
                msg.content_subtype = 'html'
                msg.attach_file(workpermit_attachment, mimetype='application/pdf')
                msg.send()
                logger.info(f"Email sent to {p['email'] = }")
                jsonresp['story']+=f"Email sent to {p['email'] = }"
        jsonresp['story'] += f"A {permit_name} email sent of pk: {womid}: "
    except Exception as e:
        logger.critical(
            "Something went wrong while running send_email_notification_for_wp_verifier",exc_info=True
            )
        jsonresp['traceback'] += tb.format_exc()
    return jsonresp
        


def send_email_notification_for_wp_from_mobile_for_verifier(womid,verifiers,sitename,workpermit_status,permit_name,vendor_name,client_id,workpermit_attachment=None):
    jsonresp = {'story': "", "traceback": ""}
    try:
        from django.apps import apps 
        from django.template.loader import render_to_string
        Wom = apps.get_model('work_order_management', 'Wom')
        People = apps.get_model('peoples', 'People')
        wp_details = Wom.objects.get_wp_answers(womid)
        wp_obj = Wom.objects.get(id=womid)
        jsonresp['story'] += f"\n{wp_details}"
        logger.info(f"Vendor name: {vendor_name} , client_id: {client_id}")
        if wp_details:
            qset = People.objects.filter(peoplecode__in = verifiers)
            for p in qset.values('email','id'):
                logger.info(f"Sending Email to {p['email'] = }")
                msg = EmailMessage()
                msg.subject = f"{permit_name}-{wp_obj.other_data['wp_seqno']}-{sitename}-Verification Pending"            
                msg.to = [p['email']]
                msg.from_email = settings.EMAIL_HOST_USER
                cxt = {
                    'peopleid':p['id'],
                    'HOST':settings.HOST,
                    'workpermitid':womid,
                    'sitename':sitename,
                    'status':workpermit_status,
                    'permit_no':wp_obj.other_data['wp_seqno'],
                    'permit_name':permit_name,
                    'vendor_name':vendor_name,
                    'client_id':client_id
                }
                html = render_to_string(
                    'work_order_management/workpermit_verifier_action.html',context=cxt
                )
                msg.body = html
                msg.content_subtype = 'html'
                msg.attach_file(workpermit_attachment, mimetype='application/pdf')
                msg.send()
                logger.info(f"Email sent to {p['email'] = }")
                jsonresp['story']+=f"Email sent to {p['email'] = }"
        jsonresp['story'] += f"A {permit_name} email sent of pk: {womid}: "
    except Exception as e:
        logger.critical(
            "Something went wrong while running send_email_notification_for_wp_verifier",exc_info=True
            )
        jsonresp['traceback'] += tb.format_exc()
    return jsonresp


def send_email_notification_for_wp(womid, qsetid, approvers, client_id, bu_id,sitename,workpermit_status,vendor_name):
    jsonresp = {'story': "", "traceback": ""}
    try:
        from django.apps import apps
        from django.template.loader import render_to_string
        Wom = apps.get_model('work_order_management', 'Wom')
        People = apps.get_model('peoples', 'People')
        wp_details = Wom.objects.get_wp_answers(womid)
        wp_obj = Wom.objects.get(id=womid)
        jsonresp['story'] += f"\n{wp_details}"
        if wp_details:
            qset = People.objects.filter(peoplecode__in = approvers)
            logger.info("Qset: ",qset)
            for p in qset.values('email', 'id'):
                logger.info(f"sending email to {p['email'] = }")
                jsonresp['story'] += f"sending email to {p['email'] = }"
                msg = EmailMessage()
                msg.subject = f"General Work Permit #{wp_obj.other_data['wp_seqno']} needs your approval"
                msg.to = [p['email']]
                msg.from_email = settings.EMAIL_HOST_USER
                cxt = {
                    'peopleid':p['id'],
                    "HOST": settings.HOST, 
                    "workpermitid": womid,
                    'sitename':sitename,
                    'status':workpermit_status,
                    'permit_no':wp_obj.other_data['wp_seqno'],
                    'permit_name':'General Work Permit',
                    'vendor_name':vendor_name}
                html = render_to_string(
                    'work_order_management/workpermit_approver_action.html', context=cxt)
                msg.body = html
                # msg.attach_file(workpermit_attachment,mimetype='application/pdf')
                msg.content_subtype = 'html'
                #msg.attach_file(workpermit_attachment, mimetype='application/pdf')
                msg.send()
                logger.info(f"email sent to {p['email'] = }")
                jsonresp['story'] += f"email sent to {p['email'] = }"
        jsonresp['story'] += f"A Workpermit email sent of pk: {womid}"
    except Exception as e:
        logger.critical(
            "something went wron while running send_email_notification_for_wp", exc_info=True)
        jsonresp['traceback'] += tb.format_exc()
    return jsonresp

def send_email_notification_for_vendor_and_security_of_wp_cancellation(wom_id,sitename,workpermit_status,vendor_name,permit_name,permit_no,submit_work_permit=False,submit_work_permit_from_mobile=False):
    jsonresp = {'story':"", 'traceback':""}
    try:
        from apps.work_order_management.models import Wom,WomDetails
        from apps.onboarding.models import Bt
        from django.template.loader import render_to_string
        from apps.work_order_management.models import Vendor
        from apps.peoples.models import People
        wom = Wom.objects.filter(parent_id=wom_id)
        site_id = wom[0].bu_id
        sitename = Bt.objects.get(id=site_id).buname

        logger.info(f'THe Site Name for vendor and security is {sitename}')
        # sitename = Bt.objects.get((Wom.objects.get(id=wom_id).client.id)).buname
        sections = [x for x in wom]
        if not submit_work_permit_from_mobile:
            if submit_work_permit:
                wom_detail = sections[-2].id
            else:
                wom_detail = sections[-1].id 
        else:
            if submit_work_permit:
                wom_detail = sections[-2].id 
        logger.info(f"sections: {sections}")
        logger.info(f"wom_detail: {wom_detail}")
        vendor_email = Vendor.objects.get(id=wom[0].vendor.id).email
        wom_detail_email_section = WomDetails.objects.filter(wom_id=wom_detail)
        logger.info(f'WOM Detail Answer Section: {wom_detail_email_section}')
        logger.info(f'Vendor Email: {vendor_email}')
        logger.info(f'WOM Detail Email Section: {wom_detail_email_section}')
        parent_wom = Wom.objects.get(id=wom_id).remarks
        cancelled_by = People.objects.get(peoplecode=parent_wom[0].get('people','')).peoplename
        remarks      = parent_wom[0].get('remarks',)
        for emailsection in wom_detail_email_section:
            logger.info(f"email: {emailsection.answer}")
            emails = emailsection.answer.split(',')
            for email in emails:
                msg = EmailMessage()
                msg.subject = f"{permit_name}-{permit_no}-{sitename}-{workpermit_status}"
                msg.to = [email]
                msg.from_email = settings.EMAIL_HOST_USER
                cxt = {
                    'permit_name':permit_name,
                    'sitename':sitename,
                    'status':workpermit_status,
                    'vendor_name':vendor_name,
                    'permit_no':permit_no,
                    'cancelled_by':cancelled_by,
                    'remarks':remarks
                }
                html = render_to_string(
                    'work_order_management/workpermit_cancellation.html', context=cxt)
                msg.body = html
                msg.content_subtype = 'html'
                msg.send()
                logger.info(f"email sent to {email}")
    except Exception as e:
        logger.critical("something went wrong while sending email to vendor and security", exc_info=True)
        jsonresp['traceback'] += tb.format_exc()
    return jsonresp



def send_email_notification_for_vendor_and_security_for_rwp(wom_id,sitename,workpermit_status,vendor_name,pdf_path,permit_name,permit_no):
    jsonresp = {'story':"", 'traceback':""}
    try:
        from apps.work_order_management.models import Wom,WomDetails
        from apps.onboarding.models import Bt
        from django.template.loader import render_to_string
        from apps.work_order_management.models import Vendor
        wom = Wom.objects.filter(parent_id=wom_id).order_by('id')
        site_id = wom[0].bu_id
        sitename = Bt.objects.get(id=site_id).buname

        logger.info(f'THe Site Name for vendor and security is {sitename}')
        # sitename = Bt.objects.get((Wom.objects.get(id=wom_id).client.id)).buname
        sections = [x for x in wom]
        # if not submit_work_permit_from_mobile:
        #     wom_detail = sections[-2].id
        # else:
        #     wom_detail = sections[-2].id

        wom_detail = sections[-2].id
        logger.info(f"sections: {sections}")
        logger.info(f"wom_detail: {wom_detail}")
        vendor_email = Vendor.objects.get(id=wom[0].vendor.id).email
        wom_detail_email_section = WomDetails.objects.filter(wom_id=wom_detail)
        logger.info(f'WOM Detail Answer Section: {wom_detail_email_section}')
        logger.info(f'Vendor Email: {vendor_email}')
        logger.info(f'WOM Detail Email Section: {wom_detail_email_section}')
        for emailsection in wom_detail_email_section:
            logger.info(f"email: {emailsection.answer}")
            emails = emailsection.answer.split(',')
            for email in emails:
                msg = EmailMessage()
                msg.subject = f"{permit_name}-{permit_no}-{sitename}-{workpermit_status}"
                msg.to = [email]
                msg.from_email = settings.EMAIL_HOST_USER
                cxt = {
                    'permit_name':permit_name,
                    'sitename':sitename,
                    'status':workpermit_status,
                    'vendor_name':vendor_name,
                    'permit_no':permit_no,
                }
                html = render_to_string(
                    'work_order_management/workpermit_vendor.html', context=cxt)
                msg.body = html
                msg.content_subtype = 'html'
                msg.attach_file(pdf_path, mimetype='application/pdf')
                msg.send()
                logger.info(f"email sent to {email}")
    except Exception as e:
        logger.critical("something went wrong while sending email to vendor and security", exc_info=True)
        jsonresp['traceback'] += tb.format_exc()
    return jsonresp


def send_email_notification_for_vendor_and_security_after_approval(wom_id,sitename,workpermit_status,vendor_name,pdf_path,permit_name,permit_no):
    jsonresp = {'story':"", 'traceback':""}
    try:
        from apps.work_order_management.models import Wom,WomDetails
        from apps.onboarding.models import Bt
        from django.template.loader import render_to_string
        from apps.work_order_management.models import Vendor
        wom = Wom.objects.filter(parent_id=wom_id).order_by('id')
        site_id = wom[0].bu_id
        sitename = Bt.objects.get(id=site_id).buname

        logger.info(f'THe Site Name for vendor and security is {sitename}')
        sections = [x for x in wom]
        wom_detail = sections[-1].id
        logger.info(f"sections: {sections}")
        logger.info(f"wom_detail: {wom_detail}")
        vendor_email = Vendor.objects.get(id=wom[0].vendor.id).email
        wom_detail_email_section = WomDetails.objects.filter(wom_id=wom_detail)
        logger.info(f'WOM Detail Answer Section: {wom_detail_email_section}')
        logger.info(f'Vendor Email: {vendor_email}')
        logger.info(f'WOM Detail Email Section: {wom_detail_email_section}')
        for emailsection in wom_detail_email_section:
            logger.info(f"email: {emailsection.answer}")
            emails = emailsection.answer.split(',')
            for email in emails:
                msg = EmailMessage()
                msg.subject = f"{permit_name}-{permit_no}-{sitename}-{workpermit_status}"
                msg.to = [email]
                msg.from_email = settings.EMAIL_HOST_USER
                cxt = {
                    'permit_name':permit_name,
                    'sitename':sitename,
                    'status':workpermit_status,
                    'vendor_name':vendor_name,
                    'permit_no':permit_no,
                }
                html = render_to_string(
                    'work_order_management/workpermit_vendor.html', context=cxt)
                msg.body = html
                msg.content_subtype = 'html'
                msg.attach_file(pdf_path, mimetype='application/pdf')
                msg.send()
                logger.info(f"email sent to {email}")
    except Exception as e:
        logger.critical("something went wrong while sending email to vendor and security", exc_info=True)
        jsonresp['traceback'] += tb.format_exc()
    return jsonresp

def send_email_notification_for_sla_vendor(wom_id,report_attachment,sitename):
    jsonresp = {'story':"", 'traceback':""}
    try:
        from apps.work_order_management.models import Wom,WomDetails
        from apps.work_order_management.models import Vendor
        from django.template.loader import render_to_string
        from dateutil.relativedelta import relativedelta
        from apps.work_order_management.utils import approvers_email_and_name,get_peoplecode
        from apps.work_order_management.views import SLA_View
        monthly_choices = SLA_View.MONTH_CHOICES
        wom = Wom.objects.get(uuid=wom_id)
        is_month_present = wom.other_data.get('month',None)
        if not is_month_present:
            month_no = wom.cdtz.month -1
            if month_no == 0:
                month_no = 12
                year = wom.cdtz.year -1
            else:
                year = wom.cdtz.year
            month_name = monthly_choices.get(f'{month_no}')
        else:
            month_name = is_month_present
            year = wom.cdtz.year
            if month_name == 'December':
                year = wom.cdtz.year - 1
        vendor_details = Vendor.objects.filter(id=wom.vendor_id).values('name','email')
        vendor_name = vendor_details[0].get('name')
        vendor_email = vendor_details[0].get('email')
        wp_approvers = wom.other_data['wp_approvers']
        people_codes = get_peoplecode(wp_approvers)
        approver_emails,approver_name = approvers_email_and_name(people_codes)
        msg = EmailMessage()
        sla_seqno = wom.other_data['wp_seqno']
        msg.subject = f" {sitename}: Vendor Performance of {vendor_name} of {month_name}-{year}"
        msg.to = [vendor_email]
        msg.cc = approver_emails
        msg.from_email = settings.EMAIL_HOST_USER
        approvedby = ''
        for name in approver_name:
            approvedby+=name+' '
        
        cxt = {
            "sla_report_no": sla_seqno,
            "sitename": sitename,
            "report_name": "Vendor Performance Report",
            "approvedby": approvedby,
            "service_month":f'{month_name} {year}'
        }
        html = render_to_string(
            'work_order_management/sla_vendor.html', context=cxt)
        msg.body = html
        msg.content_subtype = 'html'

        msg.attach_file(report_attachment, mimetype='application/pdf')
        msg.send()
        logger.info(f"email sent to {vendor_email}")
    except Exception as e:
        logger.critical("something went wrong while sending email to vendor and security", exc_info=True)
        jsonresp['traceback'] += tb.format_exc()
    return jsonresp

def move_media_to_cloud_storage():
    resp = {}
    try:
        logger.info("move_media_to_cloud_storage execution started [+]")
        directory_path = f'{settings.MEDIA_ROOT}/transactions/'
        path_list = get_files(directory_path)
        move_files_to_GCS(path_list, settings.BUCKET)
        del_empty_dir(directory_path)
        pass
    except Exception as exc:
        logger.critical(
            "something went wron while running create_report_history()", exc_info=True)
        resp['traceback'] = tb.format_exc() 
    else:
        resp['msg'] = "Completed without any errors"
    return resp

def create_scheduled_reports():
    state_map = {'not_generated':0, 'skipped':0, 'generated':0, 'processed':0}

    resp = dict()
    try:
        data = get_scheduled_reports_fromdb()
        logger.info(f"Found {len(data)} for reports for generation in background")
        if data:
            for record in data:
                state_map = generate_scheduled_report(record, state_map)
        resp['msg'] = f'Total {len(data)} report/reports processed at {timezone.now()}'
    except Exception as e:
        resp['traceback'] = tb.format_exc()
        logger.critical("Error while creating report:", exc_info=True)
    state_map['processed'] = len(data)
    resp['state_map'] = state_map
    return resp





def send_generated_report_on_mail():
    story = {
        'start_time': timezone.now(),
        'files_processed': 0,
        'emails_sent': 0,
        'errors': [],
        'end_time':timezone.now()
    }

    try:
        for file in walk_directory(settings.TEMP_REPORTS_GENERATED):
           
            story['files_processed'] += 1
            sendmail, filename_without_extension = check_time_of_report(file)
            if sendmail:
                if record := get_report_record(filename_without_extension):
                    utils.send_email(
                    subject='Test Subject',
                        body='Test Body',
                        to=record.to_addr,
                        cc=record.cc,
                        atts=[file]
                    )
                    story['emails_sent'] += 1
                    #file deletion
                    story = remove_reportfile(file, story)
                else:
                    logger.info(f"No record found for file {os.path.basename(file)}")
            else:
                logger.info("No files to send at this moment")
    except Exception as e:
       story['errors'].append(handle_error(e))
       logger.critical("something went wrong", exc_info=True)
    story['end_time'] = timezone.now()
    return story

def send_generated_report_onfly_email(filepath, fromemail, to, cc, ctzoffset):
    story = {'msg':['send_generated_report_onfly_email [started]']}
    try:
        story['msg'].append(f'{filepath = } {fromemail = } {to = } {cc =}')
        currenttime = timezone.now() + timedelta(minutes=int(ctzoffset))
        msg = EmailMessage(
            f"Your Requested report! on {currenttime.strftime('%d-%b-%Y %H:%M:%S')}",
            from_email=fromemail,
            to=to,
            cc=cc
        )
        msg.attach_file(filepath)
        msg.send()
        story['msg'].append('Email Sent')
        remove_reportfile(filepath, story)
        story['msg'].append('send_generated_report_onfly_email [ended]')
    except Exception  as e:
        logger.critical("something went wrong in bg task send_generated_report_onfly_email", exc_info=True)
    return story

def process_graphql_mutation_async(payload):
    """
    Process the incoming payload containing a GraphQL mutation and file data.

    Args:
        payload (str): The JSON-encoded payload containing the mutation query and variables.

    Returns:
        str: The JSON-encoded response containing the mutation result or errors.
    """
    from apps.service.utils import execute_graphql_mutations
    try:
        post_data = json.loads(payload)
        query = post_data.get('mutation')
        variables = post_data.get('variables', {})

        if query and variables:
            resp = execute_graphql_mutations(query, variables)
        else:
            mqlog.warning("Invalid records or query in the payload.")
            resp = json.dumps({'errors': ['No file data found']})
    except Exception as e:
        mqlog.error(f"Error processing payload: {e}", exc_info=True)
        resp = json.dumps({'errors': [str(e)]})
        raise e
    return resp
    


#@app.task(bind=True, name="insert_json_records_async")
def insert_json_records_async(records, tablename):
    from apps.service.utils import get_model_or_form
    from apps.service.validators import clean_record
    if model := get_model_or_form(tablename):
        tlog.info("processing bulk json records for insert/update")
        for record in records:
            record = json.loads(record)
            record = json.loads(record)
            record = clean_record(record)
            tlog.info(f"processing record {pformat(record)}")
            if model.objects.filter(uuid=record['uuid']).exists():
                model.objects.filter(uuid=record['uuid']).update(**record)
                tlog.info("record is already exist so updating it now..")
            else:
                tlog.info("record is not exist so creating new one..")
                model.objects.create(**record)
        return "Records inserted/updated successfully"
    
    
    
#@app.task(bind=True, name="create_save_report_async")
def create_save_report_async(formdata, client_id, user_email, user_id):
    try:
        returnfile = formdata.get('export_type') == 'SEND'
        report_essentials = rutils.ReportEssentials(report_name=formdata['report_name'])
        logger.info(f"report essentials: {report_essentials}")
        ReportFormat = report_essentials.get_report_export_object()
        report = ReportFormat(filename=formdata['report_name'], client_id=client_id,
                                formdata=formdata,  returnfile=True)
        logger.info(f"Report Format initialized, {report}")
        
        if response := report.execute():
            if returnfile:
                rutils.process_sendingreport_on_email(response, formdata, user_email)
                return {"status": 201, "message": "Report generated successfully and email sent", 'alert':'alert-success'}
            filepath = save_report_to_tmp_folder(formdata['report_name'], ext=formdata['format'], report_output=response, dir=f'{settings.ONDEMAND_REPORTS_GENERATED}/{user_id}')
            logger.info(f"Report saved at tmeporary location: {filepath}")
            return {"filepath":filepath, 'filename':f'{formdata["report_name"]}.{formdata["format"]}', 'status':200, "message": "Report generated successfully", 'alert':'alert-success'}
        else:
            return {"status": 404, "message": "No data found matching your report criteria.\
        Please check your entries and try generating the report again", 'alert':'alert-warning'}
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return {"status": 500, "message": "Internal Server Error", "alert":"alert-danger"}
        
            
#@app.task(bind=True, name="cleanup_reports_which_are_12hrs_old")
def cleanup_reports_which_are_12hrs_old(dir_path,hours_old=12):
    for root, dirs, files in os.walk(dir_path):
        for filename in files:
            file_path = os.path.join(root, filename)
            threshold = datetime.now() - timedelta(hours=hours_old)
            try:
                if os.path.isfile(file_path):
                    file_stats = os.stat(file_path)
                    last_modified = datetime.fromtimestamp(file_stats.st_mtime)
                    if last_modified < threshold:
                        os.remove(file_path)
                        logger.info(f"Deleted file: {file_path} as it was older than {hours_old} hours")
            except Exception as e:
                logger.error(f"Error deleting file {file_path}: {e}")
        

#@app.task(bind=True, default_retry_delay=300, max_retries=5, name="process_graphql_download_async")
def process_graphql_download_async(payload):
    """
    Process the incoming payload containing a GraphQL download and file data.

    Args:
        payload (str): The JSON-encoded payload containing the mutation query and variables.

    Returns:
        str: The JSON-encoded response containing the mutation result or errors.
    """
    from apps.service.utils import execute_graphql_mutations
    try:
        post_data = json.loads(payload)
        query = post_data.get('query')

        if query:
            resp = execute_graphql_mutations(query, download=True)
        else:
            mqlog.warning("Invalid records or query in the payload.")
            resp = json.dumps({'errors': ['No file data found']})
    except Exception as e:
        mqlog.error(f"Error processing payload: {e}", exc_info=True)
        resp = json.dumps({'errors': [str(e)]})
        raise e
    return resp


def send_email_notification_for_sla_report(slaid,sitename):
    jsonresp = {'story': "", "traceback": ""}
    try:
        from django.apps import apps
        from django.template.loader import render_to_string
        from apps.reports.report_designs.service_level_agreement import ServiceLevelAgreement
        from apps.work_order_management.models import Vendor
        from dateutil.relativedelta import relativedelta
        from datetime import datetime
        from apps.work_order_management.utils import save_pdf_to_tmp_location
        from apps.work_order_management.views import SLA_View
        monthly_choices = SLA_View.MONTH_CHOICES
        Wom = apps.get_model('work_order_management', 'Wom')
        People = apps.get_model('peoples', 'People')
        sla_details,rounded_overall_score,question_ans,all_average_score,remarks = Wom.objects.get_sla_answers(slaid)
        sla_record = Wom.objects.filter(id=slaid)[0]
        permit_no = sla_record.other_data['wp_seqno']
        approvers = sla_record.approvers 
        status = sla_record.workpermit
        jsonresp['story'] += f"\n{sla_details}"
        report_no = sla_record.other_data['wp_seqno']
        uuid = sla_record.uuid
        wom = Wom.objects.get(id=slaid)
        is_month_present = wom.other_data.get('month',None)
        if not is_month_present:
            month_no = wom.cdtz.month -1
            if month_no == 0:
                month_no = 12
                year = wom.cdtz.year -1
            else:
                year = wom.cdtz.year
            month_name = monthly_choices.get(f'{month_no}')
        else:
            month_name = is_month_present
            year = wom.cdtz.year
            if month_name == 'December':
                year = wom.cdtz.year - 1
        sla_report_obj = ServiceLevelAgreement(returnfile=True,filename='Service Level Agreement', formdata={'id':slaid,'bu__buname':sitename,'submit_button_flow':'true','filename':'Service Level Agreement','workpermit':sla_record.workpermit})
        attachment = sla_report_obj.execute()
        attachment_path = save_pdf_to_tmp_location(attachment,'Vendor performance report',permit_no)
        vendor_id = sla_record.vendor_id
        vendor_name = Vendor.objects.get(id=vendor_id).name
        if sla_details:
            qset = People.objects.filter(peoplecode__in = approvers)
            for p in qset.values('email', 'id'):
                logger.info(f"sending email to {p['email'] = }")
                jsonresp['story'] += f"sending email to {p['email'] = }"
                msg = EmailMessage()
                msg.subject = f"{sitename} Vendor Performance {vendor_name} of {month_name}-{year}: Approval Pending"
                msg.to = [p['email']]
                msg.from_email = settings.EMAIL_HOST_USER
                cxt = {'sections': sla_details, 'peopleid':p['id'],
                    "HOST": settings.HOST, "slaid": slaid,'sitename':sitename,'rounded_overall_score':rounded_overall_score,
                    'peopleid':p['id'],'reportid':uuid,'report_name':'Vendor Performance','report_no':report_no,'status':status,
                    'vendorname':vendor_name,'service_month':(datetime.now() - relativedelta(months=1)).strftime('%B %Y')
                    }
                html = render_to_string(
                    'work_order_management/sla_report_approver_action.html', context=cxt)
                msg.body = html
                msg.content_subtype = 'html'
                msg.attach_file(attachment_path, mimetype='application/pdf')
                msg.send()
                logger.info(f"email sent to {p['email'] = }")
                jsonresp['story'] += f"email sent to {p['email'] = }"
            jsonresp['story'] += f"A Workpermit email sent of pk: {slaid}"
    except Exception as e:
        logger.critical("something went wrong while runing sending email to approvers", exc_info=True)
        jsonresp['traceback'] += tb.format_exc()
    return jsonresp



def send_mismatch_notification(mismatch_data):
    # This task sends mismatch data to the NOC dashboard
    logger.info(f"Mismatched detected: {mismatch_data}")
    # Add logic to send data to NOC dashboard