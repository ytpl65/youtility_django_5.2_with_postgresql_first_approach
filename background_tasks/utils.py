from logging import getLogger
from datetime import datetime, timedelta, timezone
from apps.core import utils
from apps.core.raw_queries import get_query
import traceback as tb
from django.apps import apps
from PIL import Image
log = getLogger('mobile_service_log')

def correct_image_orientation(img):
    # Initialize orientation with a default value
    orientation = 1
    # Check the current orientation
    if hasattr(img, '_getexif'):
        orientation = 0x0112
        exif = img._getexif()
        orientation = exif.get(orientation, 1) if exif is not None else 1
    # Rotate the image based on the orientation
    if orientation == 3:
        img = img.rotate(180, expand=True)
    elif orientation == 6:
        img = img.rotate(270, expand=True)
    elif orientation == 8:
        img = img.rotate(90, expand=True)
    return img


def make_square(path1, path2):
    
    try:
        # Open the first image
        img1 = Image.open(path1)
        # Get the aspect ratio
        width, height = img1.size
        aspect_ratio = width / height
        log.info(f"aspect ratio of image 1 is {aspect_ratio}")
        # If the aspect ratio is not 1:1
        if aspect_ratio != 1:
            # Resize the image to make it square
            new_size = (min(width, height), min(width, height))
            img1 = img1.resize(new_size)
            log.info(
                f'new aspect ratio of image1  is {new_size[0]} x {new_size[1]}')
        # Save the new square image
        #img1 = correct_image_orientation(img1)
        img1.save(path1)
        # Repeat the process for the second image
        img2 = Image.open(path2)
        width, height = img2.size
        aspect_ratio = width / height
        log.info(f"aspect ratio of image 2 is {aspect_ratio}")
        if aspect_ratio != 1:
            new_size = (min(width, height), min(width, height))
            img2 = img2.resize(new_size)
            log.info(
                f'new aspect ratio of image2 is {new_size[0]} x {new_size[1]}')

        img2 = correct_image_orientation(img2)
        img2.save(path2)
    except FileNotFoundError:
        log.error("Error: One or both of the provided file paths do not exist.")
    except IOError:
        log.error("Error: One or both of the provided files are not images.")
    except Exception as e:
        log.error("Error: An unknown error occurred. while performing make_square(path1, path2)", e)




def get_email_recipents_for_ticket(ticket):
    from apps.y_helpdesk.models import Ticket
    from apps.peoples.models import Pgbelonging
    emails = []
    group_emails = Pgbelonging.objects.select_related('pgroup', 'people').filter(
        pgroup_id=ticket.assignedtogroup_id
    ).exclude(people_id=1).values('people__email')
    log.debug(f"group emails:{group_emails}")

    temails = Ticket.objects.select_related('people', 'pgroup', 'cuser', 'muser').filter(
        id=ticket.id
    ).values(
        'assignedtopeople__email', 'cuser__email', 'muser__email'
    ).first()
    log.debug(f"ticket emails: {temails}")
    emails += [temails['assignedtopeople__email'],
               temails['cuser__email'], temails['muser__email']]
    emails.extend(email['people__email'] for email in group_emails)
    return list(set(emails))


def update_ticket_data(tickets, result):
    from django.utils import timezone
    now = timezone.now().replace(microsecond=0, second=0)
    import json
    if tickets:
        result['story'] += "updating ticket data started"
    for tkt in tickets:
        Ticket = apps.get_model('y_helpdesk', 'Ticket')
        # update tkt level, mdtz, modigiedon
        if tkt['escgrpid'] in [1, '1', None] and tkt['escpersonid'] in [1, '1', None]:
            assignedperson_id = tkt['assignedtopeople']
            assignedtogroup_id = tkt['assignedtogroup']
        else:
            assignedperson_id = tkt['escpersonid']
            assignedtogroup_id = tkt['escgrpid']
        ticketlog = json.loads(tkt['ticketlog'])
        history_item = {
            "people_id": tkt['cuser_id'],
            "when": str(now),
            "who": tkt['who'],
            "action": "created",
            "details": [f"Ticket is escalated from level {tkt['level']} to {tkt['level']+1}"],
            "previous_state": ticketlog['ticket_history'][-1]['previous_state'] if ticketlog['ticket_history'] else {},
        }

        if t := Ticket.objects.filter(id=tkt['id']).update(
            mdtz=tkt['exp_time'],
            modifieddatetime=tkt['exp_time'],
            level=tkt['level'] + 1,
            assignedtopeople_id=assignedperson_id,
            assignedtogroup_id=assignedtogroup_id,
            isescalated=True,
        ):

            result['story'] += f"ticket updated with these values mdtz & modifieddatetime \
            {tkt['exp_time']} {tkt['level'] = } {assignedperson_id = } {assignedtogroup_id = } level= {tkt['level']+1}"
            result = update_ticket_log(tkt['id'], history_item, result)
            result = send_escalation_ticket_email(tkt, result)
            result['id'].append(tkt['id'])
    return result



def send_escalation_ticket_email(tkt, result):
    # get records for email sending
    records = utils.runrawsql(get_query('ticketmail'), [tkt['id']])
    from django.template.loader import render_to_string
    from django.conf import settings
    from django.core.mail import EmailMessage
    try:
        for rec in records:
            subject = f"Escalation Level {rec['level']}: Ticket Number {rec['ticketno']}"
            toemails = []
            if rec['creatorid'] != 1:
                toemails.append(rec['creatoremail'])
            if rec['modifierid'] != 1:
                toemails.append(rec['modifiermail'])
            if rec['assignedtopeople_id'] not in [1, None]:
                toemails.append(rec['peopleemail'])
            if rec['assignedtogroup_id'] not in [1, None]:
                toemails.append(rec['pgroupemail'])
            if rec['notify'] not in [1, None, ""]:
                toemails.append(rec['notifyemail'].replace(" ", ''))
            msg = EmailMessage()
            context = {
                'desc': rec['ticketdesc'],
                'template': rec['tescalationtemplate'],
                'priority': rec['priority'],
                'status': rec['status'],
                'createdon': str(rec['cdtz'] + timedelta(hours=5, minutes=30))[:19],
                'modifiedon': str(rec['mdtz'] + timedelta(hours=5, minutes=30))[:19],
                'modifiedby': rec['modifiername'],
                'assignedto': str(rec["peoplename"]) if (rec["assignedtopeople_id"] not in [1, " ", None]) else str(rec["groupname"]),
                'comments': "NA" if rec["comments"] == '' else str(rec["comments"]),
                'isescalated': "True",
                'escdetails': "NA" if rec["body"] == '' else str(rec["body"]),
                'escin': f'{rec["frequencyvalue"]} {rec["frequency"]}',
                'level': rec['level'],
                'next_esc': rec['next_escalation'],
                'subject': subject
            }
            html_message = render_to_string(
                'y_helpdesk/ticket_email.html', context=context)
            msg.body = html_message
            msg.subject = subject
            msg.from_email = settings.EMAIL_HOST_USER
            msg.content_subtype = 'html'
            msg.to = toemails
            msg.send()
            log.info(f"mail sent, record_id:{rec['id']}")
    except Exception as e:
        log.critical(
            "something went wrong while sending escalation email", exc_info=True)
        result['traceback'] = tb.format_exc()
    return result



def update_ticket_log(id, item, result):
    try:
        Ticket = apps.get_model('y_helpdesk', 'Ticket')
        t = Ticket.objects.get(id=id)
        t.ticketlog['ticket_history'].append(item)
        t.save()
        result['story'] += "ticketlog saved"
    except Exception as e:
        log.critical("something went wron while saving ticketlog", exc_info=True)
        result['traceback'] = f"{tb.format_exc()}"
    return result


def check_for_checkpoints_status(obj, Jobneed):
    for checkpoint in Jobneed.objects.filter(parent_id = obj.id, identifier__in = ['INTERNALTOUR','EXTERNALTOUR']):
        log.info(f'checkpoint status {checkpoint.jobstatus = }')
        if checkpoint.jobstatus == 'ASSIGNED':
            checkpoint.jobstatus = 'AUTOCLOSED'
            checkpoint.other_info['autoclosed_by_server'] = True
            checkpoint.save()
            log.info(f'checkpoint status after update {checkpoint.jobstatus = }')

def check_child_of_jobneed_status(obj,Jobneed):
    pass 


def update_job_autoclose_status(record, resp):
    Jobneed = apps.get_model('activity', 'Jobneed')
    obj = Jobneed.objects.get(id=record['id'])
    obj.mdtz = datetime.now(timezone.utc)
    log.info(f'Before status update of job with id {record['id']}  is {obj.jobstatus = }')
    if obj.jobstatus == 'INPROGRESS':
        checkpoints = Jobneed.objects.filter(parent_id=obj.id, identifier__in=['INTERNALTOUR', 'EXTERNALTOUR'])
        total = checkpoints.count()
        completed = checkpoints.filter(jobstatus='COMPLETED').count()
        if completed > 0 and completed < total:
            obj.jobstatus='PARTIALLYCOMPLETED'
            obj.save()
            log.info(f'The Status is updated to {obj.jobstatus}')
    if obj.jobstatus != 'PARTIALLYCOMPLETED' and obj.jobstatus!='COMPLETED':
        obj.jobstatus = 'AUTOCLOSED'
        obj.other_info['email_sent'] = record['ticketcategory__tacode'] == 'AUTOCLOSENOTIFY'
        obj.other_info['ticket_generated'] = record['ticketcategory__tacode'] == 'RAISETICKETNOTIFY'
        obj.other_info['autoclosed_by_server'] = True
        obj.save()
        log.info(f'After status update {obj.jobstatus = }')
    
    check_for_checkpoints_status(obj, Jobneed)
    log.info(f'jobneed object with id = {record["id"]} is {obj.jobstatus = } {obj.other_info["email_sent"] = } {obj.other_info["ticket_generated"] = } {obj.other_info["autoclosed_by_server"] = }')
    resp['id'].append(record['id'])
    return resp


def get_escalation_of_ticket(tkt):
    if tkt:
        EscalationMatrix = apps.get_model('y_helpdesk', 'EscalationMatrix')
        return EscalationMatrix.objects.filter(
            bu_id=tkt['bu_id'],
            escalationtemplate_id=tkt['ticketcategory_id'],
            client_id=tkt['client_id'],
            level=tkt['level'] + 1
        ).select_related('escalationtemplate', 'client', 'bu').values(
            'level', 'frequencyvalue', 'frequency'
        ).order_by('level').first() or []
    return []



def create_ticket_for_autoclose(jobneedrecord, ticketdesc):
    try:
        Ticket = apps.get_model('y_helpdesk', 'Ticket')
        tkt, _ = Ticket.objects.get_or_create(
            bu_id=jobneedrecord['bu_id'],
            status="NEW",
            client_id=jobneedrecord['client_id'],
            asset_id=jobneedrecord['asset_id'],
            ticketcategory_id=jobneedrecord['ticketcategory_id'],
            ticketsource=Ticket.TicketSource.SYSTEMGENERATED,
            ticketdesc=ticketdesc,
            priority=jobneedrecord['priority'],
            assignedtopeople_id=jobneedrecord['people_id'],
            assignedtogroup_id=jobneedrecord['pgroup_id'],
            qset_id = jobneedrecord['qset_id']
        )
        return Ticket.objects.filter(
            id=tkt.id
        ).select_related('bu', 'client', 'escalationtemplate').values(
            'ticketcategory_id', 'client_id', 'level', 'bu_id', 'ticketno',
            'cdtz', 'ctzoffset'
        ).first()
    except Exception as e:
        log.critical(
            "something went wrong in create_ticket_for_autoclose", exc_info=True)


def get_email_recipients(buid, clientid=None):
    from apps.peoples.models import People
    from apps.onboarding.models import Bt
    
    #get email of siteincharge
    emaillist = People.objects.get_siteincharge_emails(buid)
    #get email of client admins
    if clientid:
        adm_emails = People.objects.get_admin_emails(clientid)
        emaillist += adm_emails
    return emaillist

def get_context_for_mailtemplate(jobneed, subject):
    from apps.activity.models.job_model import JobneedDetails
    from datetime import timedelta
    when = jobneed.endtime + timedelta(minutes=jobneed.ctzoffset)
    return  {
        'details'     : list(JobneedDetails.objects.get_e_tour_checklist_details(jobneedid=jobneed.id)),
        'when'        : when.strftime("%d-%m-%Y %H:%M"),
        'tourtype'    : jobneed.identifier,
        'performedby' : jobneed.performedby.peoplename,
        'site'        : jobneed.bu.buname,
        'subject'     : subject,
        'jobdesc': jobneed.jobdesc
    }




def add_attachments(jobneed, msg, result):
    from django.conf import settings
    JobneedDetails = apps.get_model('activity', 'JobneedDetails')
    Jobneed = apps.get_model('activity', 'Jobneed')
    JND = JobneedDetails.objects.filter(jobneed_id = jobneed.id)

    jnd_atts = []
    for jnd in JND:
        if att := list(JobneedDetails.objects.getAttachmentJND(jnd.id)):
            jnd_atts.append(att[0])
    jn_atts = list(Jobneed.objects.getAttachmentJobneed(jobneed.id))
    total_atts = jn_atts + jnd_atts
    if total_atts: result['story'] += f'Total {total_atts} are added to the mail'
    for att in total_atts:
        msg.attach_file(f"{settings.MEDIA_ROOT}/{att['filepath']}{att['filename']}")
        log.info("attachments are attached....")
    return msg
    

def alert_observation(jobneed, atts=False):
    from django.template.loader import render_to_string
    from django.core.mail import EmailMessage
    from django.conf import settings

    try:
        result = {'story':"", 'traceback':""}
        if jobneed.alerts and not jobneed.ismailsent:
            result['story'] += 'Sending Mail...'
            recipents = get_email_recipients(jobneed.bu_id, jobneed.client_id)
            if jobneed.identifier == 'EXTERNALTOUR':
                subject = f"[READINGS ALERT] Site:{jobneed.bu.buname} having checklist [{jobneed.qset.qsetname}] - readings out of range"
            elif jobneed.identifier == 'INTERNALTOUR':
                subject = f"[READINGS ALERT] Checkpoint:{jobneed.asset.assetname} at Site:{jobneed.bu.buname} having checklist [{jobneed.qset.qsetname}] - readings out of range"
            else:
                subject = f"[READINGS ALERT] Site:{jobneed.bu.buname} having checklist [{jobneed.qset.qsetname}] - readings out of range"
            context = get_context_for_mailtemplate(jobneed, subject)

            html_message = render_to_string('activity/observation_mail.html', context)
            log.info(f"Sending alert mail with subject {subject}")
            msg = EmailMessage()
            msg.subject = subject
            msg.body  = html_message
            msg.from_email = settings.EMAIL_HOST_USER
            msg.to = recipents
            msg.content_subtype = 'html'
            if atts:
                log.info('Attachments are going to attach')
                #add attachments to msg
                msg = add_attachments(jobneed, msg, result)
            msg.send()
            log.info(f"Alert mail sent to {recipents} with subject {subject}")
            result['story'] += 'Mail sent'
            jobneed.ismailsent=True
            jobneed.save()
        else:
            result['story'] += "Alerts not found"
    except Exception as e:
        log.critical("Error while sending alert mail", exc_info=True)
        result['traceback'] += tb.format_exc()
    return result
        
        

def alert_deviation(uuid, ownername):
    pass

