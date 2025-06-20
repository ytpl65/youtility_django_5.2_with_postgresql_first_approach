import json
import traceback as tb
from logging import getLogger
from pprint import pformat
import os
from django.apps import apps
from django.conf import settings
from django.db import transaction
from django.db.utils import IntegrityError
from apps.activity.models.asset_model import Asset
from apps.activity.models.job_model import Jobneed,JobneedDetails
from apps.work_order_management.models import Wom
from apps.core import utils
from apps.core import exceptions as excp
from apps.service import serializers as sz
from apps.y_helpdesk.models import Ticket
from background_tasks.tasks import alert_sendmail,send_email_notification_for_wp_from_mobile_for_verifier, send_email_notification_for_vendor_and_security_for_rwp,insert_json_records_async
from intelliwiz_config.celery import app
from apps.work_order_management.utils import save_approvers_injson,save_verifiers_injson
from apps.schedhuler.utils import create_dynamic_job
from intelliwiz_config.settings import GOOGLE_MAP_SECRET_KEY as google_map_key
from .auth import Messages as AM
from .types import ServiceOutputType
from .validators import clean_record


log = getLogger('message_q')
tlog = getLogger('tracking')
error_logger = getLogger("error_logger")
err = error_logger.error
from apps.work_order_management import utils as wutils


class Messages(AM):
    INSERT_SUCCESS  = "Inserted Successfully!"
    UPDATE_SUCCESS  = "Updated Successfully!"
    IMPROPER_DATA   = "Failed to insert incorrect tablname or size of columns and rows doesn't match",
    WRONG_OPERATION = "Wrong operation 'id' is passed during insertion!"
    DBERROR         = "Integrity Error!"
    INSERT_FAILED   = "Failed to insert something went wrong!"
    UPDATE_FAILED   = "Failed to Update something went wrong!"
    NOT_INTIATED    = "Insert cannot be initated not provided necessary data"
    UPLOAD_FAILED   = "Upload Failed!"
    NOTFOUND        = "Unable to find people with this pelogid"
    START           = "Mutation start"
    END             = "Mutation end"
    ADHOCFAILED     = 'Adhoc service failed'
    NODETAILS       = ' Unable to find any details record against site/incident report'
    REPORTSFAILED   = 'Failed to generate jasper reports'
    UPLOAD_SUCCESS  = 'Uploaded Successfully!'


# utility functions
def insertrecord_json(records, tablename):
    uuids = []
    try:
        if model := get_model_or_form(tablename):
            for record in records:
                record = json.loads(record)
                record = json.loads(record)
                record = clean_record(record)
                uuids.append(record['uuid'])
            insert_json_records_async.delay(records, tablename)
    except IntegrityError as e:
        tlog.info(f"record already exist in {tablename}")
    except Exception as e:
        tlog.critical("something went wrong", exc_info=True)
        raise e
    return uuids

def get_json_data(file):
    import gzip
    import json
    jsonstring=None
    try:
        s = file.read().decode('utf-8')
        jsonstring = s.replace("'", "")
        if isTrackingRecord := jsonstring.startswith('{'):
            log.info("Tracking record found")
            arr = jsonstring.split('?')
            jsonstring = json.dumps(arr)
        return json.loads(jsonstring)
    except json.decoder.JSONDecodeError:
        log.warning("It is not valid Json String \n %s"%(pformat(jsonstring)))
    except Exception as e:
        log.critical("File unzipping error", exc_info=True)
    return []


def get_model_or_form(tablename):
    if tablename == 'peopleeventlog':
        return apps.get_model('attendance', 'PeopleEventlog')
    if tablename == 'attachment':
        return  apps.get_model('activity', 'Attachment')
    if tablename == 'assetlog':
        return  apps.get_model('activity', 'AssetLog')
    if tablename == 'jobneed':
        return apps.get_model('activity', 'Jobneed')
    if tablename == 'jobneeddetails':
        return apps.get_model('activity', 'JobneedDetails')
    if tablename == 'deviceeventlog':
        return apps.get_model('activity', 'DeviceEventlog')
    if tablename == 'ticket':
        return apps.get_model('y_helpdesk', 'Ticket')
    if tablename == 'asset':
        return  apps.get_model('activity', 'Asset')
    if tablename == 'tracking':
        return apps.get_model('attendance', 'Tracking')
    if tablename == 'typeassist':
        return apps.get_model('onboarding', 'TypeAssist')
    if tablename == 'wom':
        return apps.get_model('work_order_management', 'Wom')
    if tablename == 'womdetails':
        return apps.get_model('work_order_management', 'WomDetails')
    if tablename == 'business unit':
        return apps.get_model('onboarding', 'Bt')

def get_object(uuid, model):
    try:
        return model.objects.get(uuid = uuid)
    except model.DoesNotExist as e:
        raise Exception from e

def save_jobneeddetails(data):
    import json
    jobneeddetails_post_data = json.loads(data['jobneeddetails'])


def get_or_create_dir(path):
    import os
    created = True
    if not os.path.exists(path):
        os.makedirs(path)
    else: created= False
    return created

def write_file_to_dir(filebuffer, uploadedfilepath):
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    if hasattr(filebuffer, 'read'):
        # This assumes filebuffer is a file-like object (e.g., InMemoryUploadedFile), so we read its contents.
        content = filebuffer.read()
    elif isinstance(filebuffer, list):  # Check if filebuffer is a list of integers (bytes)
        # Convert list of integers to bytes
        content = bytes(filebuffer)
    else:
        raise ValueError("Unsupported filebuffer type")
    uploadedfilepath = os.path.normpath(uploadedfilepath)
    path = default_storage.save(uploadedfilepath, ContentFile(content))
    log.info(f"file saved to {path}")


def insert_or_update_record(record, tablename):
    try:
        if model := get_model_or_form(tablename):
            record = clean_record(record)
            log.info(f'record after cleaning\n {pformat(record)}')
            if model.objects.filter(uuid = record['uuid']).exists():
                model.objects.filter(uuid = record['uuid']).update(**record)
                log.info("record is already exist so updating it now..")
                return model.objects.filter(uuid = record['uuid']).first()
            else:
                log.info("record does not exist so creating it now..")
                return model.objects.create(**record)
    except IntegrityError as e:
        log.info(f"record already exist in {tablename}")
    except Exception as e:
        log.critical("something went wrong while inserting/updating record", exc_info = True)
        raise e



def update_record(details, jobneed_record, JnModel, JndModel):
    '''
    takes details(jobneeddetails list), jobneed_record, JnModel, JndModel
    updates both jobneed and its jobneeddetails
    '''
    record = clean_record(jobneed_record)
    try:
        instance = JnModel.objects.get(uuid = record['uuid'])
        jn_parent_serializer = sz.JobneedSerializer(data = record, instance = instance)
        if jn_parent_serializer.is_valid():
            jobneed = jn_parent_serializer.save()
            if jobneed.jobstatus == 'COMPLETED' and jobneed.other_info['isdynamic'] and jobneed.parent_id == 1:
                create_dynamic_job([jobneed.job_id])
                log.info("Dynamic job created")
            jobneed.geojson['gpslocation'] = get_readable_addr_from_point(jobneed.gpslocation)
            jobneed.save()
            log.debug(f'after saving the record jobneed_id {jobneed.id} cdtz {jobneed.cdtz} mdtz = {jobneed.mdtz} starttime = {jobneed.starttime} endtime = {jobneed.endtime}')
            log.info("parent jobneed is valid and saved successfully")
            if jobneed.jobstatus == 'AUTOCLOSED' and len(details) == 0:
                return True
            elif isJndUpdated := update_jobneeddetails(details, JndModel):
                log.info('parent jobneed and its details are updated successully')
                alert_sendmail.delay(jobneed.id, 'observation', atts=True)
                return True
        else: 
            log.error(f"parent jobneed record has some errors\n{jn_parent_serializer.errors} ", exc_info = True )
    except Exception:
        log.critical("update_record failed", exc_info = True)
        raise
    return False



def update_jobneeddetails(jobneeddetails, JndModel):
    try:
        if jobneeddetails:
            updated = 0
            log.info(f'total {len(jobneeddetails)} JND records found')
            for detail in jobneeddetails:
                record = clean_record(detail)
                log.info(f'JND record after cleaning\n {pformat(record)}')
                instance = JndModel.objects.get(uuid = record['uuid'])
                jnd_ser = sz.JndSerializers(data = record, instance = instance)
                if jnd_ser.is_valid(): 
                    jnd_ser.save()
                    updated += 1
                else:
                    log.error(f'JND record with this uuid: {record["uuid"]} has some errors!\n {jnd_ser.errors}', exc_info=True)
            if len(jobneeddetails) == updated: 
                log.info(f'All {updated} JND records are updated successfully')
                return True
            else:
                log.warning(f'failed to update all {len(jobneeddetails)} JND records')
    except Exception as e:
        log.critical('jobneed details record failed to save', exc_info= True)
        raise


def save_parent_childs(sz, jn_parent_serializer, child, M, tablename, is_return_wp,verifers):
    from apps.onboarding.models import Bt
    from apps.activity.models.question_model import QuestionSet
    from apps.work_order_management.models import Vendor
    from apps.work_order_management.views import WorkPermit
    from apps.work_order_management.utils import save_pdf_to_tmp_location
    try:
        rc,  traceback= 0,  'NA'
        instance = None
        if jn_parent_serializer.is_valid():
            if not is_return_wp:
                parent = jn_parent_serializer.save()
                log.info(f"{verifers},{type(verifers)}")
                parent.verifiers = [verifers]
                log.info(f"Here I am because not jn_parent_serializer: {parent}")
            if is_return_wp:
                log.info('Return Work Permit')
                id = jn_parent_serializer.validated_data.get('parent_id')
                log.info(f'WOM Id: {id}')
                wom = Wom.objects.get(id = jn_parent_serializer.validated_data.get('parent_id'))
                seqno = Wom.objects.filter(parent_id=wom.id).order_by('-seqno').first().seqno + 1
                wom.workstatus = Wom.Workstatus.COMPLETED
                wom.save()
                
                #log.info(f'Return workpermit found parent wrapper ignored and only childs are considered {jn_parent_serializer.validated_data.get('parent_id')}')

            log.info('parent record for report mutation saved')
            allsaved = 0
            log.info(f'Total {len(child)} child records found for report mutation')
            for ch in child:
                details = ch.pop('details')
                log.info(f'Total {len(details)} detail records found for the chid with this uuid:{ch["uuid"]}')
                parent_id = jn_parent_serializer.validated_data.get('parent_id') if is_return_wp else parent.id
                ch.update({'parent_id':parent_id})
                switchedSerializer = sz.WomSerializer if tablename == 'wom' else sz.JobneedSerializer
                log.info(f'switched serializer is {switchedSerializer}')
                child_serializer = switchedSerializer(data = clean_record(ch))
                if child_serializer.is_valid():
                    if is_return_wp:
                        child_serializer.validated_data['seqno'] = seqno
                        seqno+=1
                    child_instance = child_serializer.save()
                    log.info(f"child record with this uuid: {child_instance.uuid} saved for report mutation")
                    for dtl in details:
                        dtl.update({'wom_id':child_instance.id} if tablename == 'wom' else {'jobneed_id':child_instance.id})
                        switchedDetailSerializer = sz.WomDetailsSerializers if tablename == 'wom' else sz.JndSerializers
                        log.info(f'switched serializer is {switchedDetailSerializer}')
                        ch_detail_serializer = switchedDetailSerializer(data = clean_record(dtl))
                        if ch_detail_serializer.is_valid():
                            ch_detail_serializer.save()
                        else:
                            log.error(f"detail record of this child uuid:{child_instance.uuid} has some errors: {ch_detail_serializer.errors}")
                            traceback, msg, rc = str(ch_detail_serializer.errors), M.INSERT_FAILED, 1
                    allsaved += 1
                else:
                    log.error(f'child record has some errors:{child_serializer.errors}')
                    traceback, msg, rc = str(child_serializer.errors), M.INSERT_FAILED, 1
                log.info(f'Child : {child}') 
            if allsaved == len(child):
                from apps.onboarding.models import Bt
                from apps.activity.models.question_model import QuestionSet
                msg= M.INSERT_SUCCESS
                log.info(f'All {allsaved} child records saved successfully,{is_return_wp}')
                if not is_return_wp and  hasattr(parent, 'parent_id') and tablename == 'wom' and parent.workpermit != 'NOT_REQUIRED' and parent.parent_id ==1:
                    parent = save_approvers_injson(parent)
                    parent = save_verifiers_injson(parent)
                    log.info(f'{parent.id = } {parent.uuid = } {parent.description}')
                    wom_id = parent.id
                    verifers = parent.verifiers
                    sitename = Bt.objects.get(id=parent.bu_id).buname
                    worpermit_status = parent.workpermit
                    permit_name = parent.qset.qsetname
                    vendor_name = Vendor.objects.get(id=parent.vendor_id).name
                    client_id = parent.client_id
                    latest_records = Wom.objects.filter(client=parent.client_id,bu=parent.bu_id,parent_id=1,identifier='WP').order_by('-other_data__wp_seqno').first()
                    if latest_records is None:
                        parent.other_data['wp_seqno'] = 1
                    elif parent.other_data['wp_seqno'] != latest_records.other_data['wp_seqno']:
                        parent.other_data['wp_seqno'] = latest_records.other_data['wp_seqno'] + 1
                    parent.other_data['wp_name'] = permit_name
                    parent.identifier='WP'
                    parent.save()
                    report_object = WorkPermit.get_report_object(parent,permit_name)
                    report = report_object(filename=permit_name,client_id=parent.client_id,returnfile=True,formdata = {'id':parent.id},request=None)
                    report_pdf_object = report.execute()
                    pdf_path = save_pdf_to_tmp_location(report_pdf_object,report_name=permit_name,report_number=parent.other_data['wp_seqno'])
                    log.info(f"PDF Path: {pdf_path}")
                    send_email_notification_for_wp_from_mobile_for_verifier.delay(wom_id,verifers,sitename,worpermit_status,permit_name,vendor_name,client_id,workpermit_attachment=pdf_path)      
        if is_return_wp:
            wom = Wom.objects.get(id = jn_parent_serializer.validated_data.get('parent_id'))
            vendor_name = Vendor.objects.get(id=wom.vendor_id).name
            permit_name = QuestionSet.objects.get(id=wom.qset.id).qsetname
            report_object = WorkPermit.get_report_object(wom,permit_name)
            report = report_object(filename=permit_name,client_id=wom.client_id,returnfile=True,formdata = {'id':wom.id},request=None)
            report_pdf_object = report.execute()
            permit_no = wom.other_data['wp_seqno']
            sitename = Bt.objects.get(id=wom.bu.id).buname
            pdf_path = save_pdf_to_tmp_location(report_pdf_object,report_name=permit_name,report_number=wom.other_data['wp_seqno'])
            send_email_notification_for_vendor_and_security_for_rwp.delay(wom.id,sitename,wom.workstatus,vendor_name,pdf_path,permit_name,permit_no)       
        else:
            log.error(jn_parent_serializer.errors)
            traceback, msg, rc = str(jn_parent_serializer.errors), M.INSERT_FAILED, 1
        log.info("save_parent_childs ............end")
        return rc, traceback, msg
    except Exception:
        log.critical("something went wrong",exc_info = True)
        raise


def save_linestring_and_update_pelrecord(obj):
    # sourcery skip: identity-comprehension
    from django.contrib.gis.geos import LineString

    from apps.attendance.models import Tracking
    try:

        bet_objs = Tracking.objects.filter(reference = obj.uuid).order_by('receiveddate')
        line = [[coord for coord in obj.gpslocation] for obj in bet_objs]
        if len(line) > 1:
            ls = LineString(line, srid = 4326)
            # transform spherical mercator projection system
            ls.transform(3857)
            #d = round(ls.length / 1000)
            #obj.distance = d
            ls.transform(4326)
            obj.journeypath = ls
            obj.geojson['startlocation'] = get_readable_addr_from_point(obj.startlocation)
            obj.geojson['endlocation'] = get_readable_addr_from_point(obj.endlocation)
            obj.save()
                #bet_objs.delete()
            log.info("save linestring is saved..")
            
    except Exception as e:
        log.critical('ERROR while saving line string', exc_info = True)
        raise




def update_adhoc_record(scheduletask, jobneedrecord, details):
    rc, recordcount, traceback, msg= 1, 0, 'NA', ""
    log.info(f'jobneed record recieved: {pformat(jobneedrecord)}')
    recordcount += 1
    Jobneed.objects.filter(id = scheduletask['id']).update(
        performedby_id  = jobneedrecord['performedby_id'],
        starttime       = jobneedrecord['starttime'],
        endtime         = jobneedrecord['endtime'],
        jobstatus       = jobneedrecord['jobstatus'],
        remarks         = jobneedrecord['remarks'],
        alerts          = jobneedrecord['alerts'],
        attachmentcount = jobneedrecord['attachmentcount'],
        mdtz            = jobneedrecord['mdtz'],
        muser_id        = jobneedrecord['muser_id'])
    log.info(f'record after updation {pformat(Jobneed.objects.filter(id =scheduletask["id"]).values())}')
    log.info('schedule record updated')
    
    JND = JobneedDetails.objects.filter(jobneed_id = scheduletask['id']).values()
    for jnd in JND:
        for dtl in details:
            if jnd['question_id'] == dtl['question_id']:
                obj = JobneedDetails.objects.get(id = jnd['id'])
                record = clean_record(dtl)
                jndsz = sz.JndSerializers(instance = obj, data = record)
                if jndsz.is_valid():
                    jndsz.save()
    recordcount += 1
    rc=0
    alert_sendmail.delay(scheduletask['id'], 'observation', atts=True)
    msg = "Scheduled Record (ADHOC) updated successfully!"
    return rc, traceback, msg, recordcount

def insert_adhoc_record(jobneedrecord, details):
    rc, recordcount, traceback, msg= 1, 0, 'NA', ""
    jnsz = sz.JobneedSerializer(data = jobneedrecord)
    if jnsz.is_valid():
        jn_instance = jnsz.save()
        log.info(f"Jobneed Instance: ------------> {jn_instance}")
        for dtl in details:
            dtl.update({'jobneed_id':jn_instance.id})
            record = clean_record(dtl)
            jndsz = sz.JndSerializers(data = record)
            if jndsz.is_valid():
                jndsz.save()
        msg = "Record (ADHOC) inserted successfully!"
        recordcount += 1
        rc=0
        alert_sendmail.delay(jn_instance.id, 'observation', atts=True)
    else:
        rc, traceback = 1, jnsz.errors
    return rc, traceback, msg, recordcount



def get_readable_addr_from_point(point):
    import googlemaps
    try:
        if hasattr(point, 'coords') and point.coords[0] not in [0.0, "0.0"]:
            gmaps = googlemaps.Client(key=google_map_key)
            result = gmaps.reverse_geocode(point.coords[::-1])
            log.info("reverse geocoding complete, results returned")
            return result[0]['formatted_address']
        log.info("Not a valid point, returned empty string")
        return ""
    except Exception as e:
        log.critical("something went wrong while reverse geocoding", exc_info=True)
        return ""
    
def save_addr_for_point(obj):
    if hasattr(obj, 'gpslocation'):
        obj.geojson['gpslocation'] = get_readable_addr_from_point(obj.gpslocation)
    if hasattr(obj, 'startlocation'):
        obj.geojson['startlocation'] = get_readable_addr_from_point(obj.startlocation)
    if hasattr(obj, 'endlocation'):
        obj.geojson['endlocation'] = get_readable_addr_from_point(obj.endlocation)
    obj.save()
    
def call_service_based_on_filename(data, filename, db='default', request=None, user=None):
    log.info(f'filename before calling {filename}')
    if filename == 'insertRecord.gz':
        log.info("calling insertrecord. service..")
        return perform_insertrecord.delay(file=data, db = db, bg=True, userid=user)
    if filename == 'updateTaskTour.gz':
        log.info("calling updateTaskTour service..")
        return perform_tasktourupdate.delay(file=data, db = db, bg=True)
    if filename == 'uploadReport.gz':
        log.info("calling uploadReport service..")
        return perform_reportmutation.delay(file=data, db = db, bg=True)
    if filename == 'adhocRecord.gz':
        log.info("calling adhocRecord service..")
        return perform_adhocmutation.delay(file=data, db = db, bg=True)
    


def get_user_instance(id):
    log.info(f"people id: {id} type: {type(id)}")
    from apps.peoples.models import People
    return People.objects.get(id = int(id))



@app.task(bind = True, default_retry_delay = 300, max_retries = 5, name = "perform_tasktourupdate()")
def perform_tasktourupdate(self, records, request=None, db='default', bg=False):
    rc, recordcount, traceback= 1, 0, 'NA'
    instance, msg = None, Messages.UPDATE_FAILED

    try:
        log.info(
            f"""perform_tasktourupdate(type of file = {type(records) }bg = {bg}, db = {db} runnning in {'background' if bg else "foreground"})"""
        )
        data = [json.loads(record) for record in records]
        log.info(f'data: {pformat(data)}')
        if len(data) == 0: raise excp.NoRecordsFound
        log.info(f'total {len(data)} records found for task tour update')
        for rec in data:
            if rec:
                details = rec.pop('details')
                jobneed = rec
                with transaction.atomic(using = db):
                    if isupdated :=  update_record(details, jobneed, Jobneed, JobneedDetails):
                        recordcount += 1
                        save_journeypath_field(jobneed)
                        log.info(f'{recordcount} task/tour updated successfully')
        if len(data) == recordcount:
            msg = Messages.UPDATE_SUCCESS
            log.info(f'All {recordcount} task/tour records are updated successfully')
            rc=0
    except excp.NoRecordsFound as e:
        log.warning('No records found for task/tour update', exc_info=True)
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
    except IntegrityError as e:
        log.error("Database Error", exc_info = True)
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
    except Exception as e:
        log.error('Something went wrong', exc_info = True)
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
    results = ServiceOutputType(rc = rc, msg = msg, recordcount = recordcount, traceback = traceback)
    return results.__dict__ if bg else results


def save_journeypath_field(jobneed):
    log.info(f"{jobneed['jobstatus']=} {jobneed['identifier']=} {jobneed['parent_id']=}")
    if jobneed.get('parent_id') == 1 \
    and jobneed.get('jobstatus') in ('COMPLETED', 'PARTIALLYCOMPLETED') \
    and jobneed.get('identifier') in ('EXTERNALTOUR', 'INTERNALTOUR'):
        from django.contrib.gis.geos import LineString
        from apps.attendance.models import Tracking
        try:
            log.info(f"saving line string started all conditions met")
            sitetour =  Jobneed.objects.get(uuid=jobneed.get('uuid'))
            between_latlngs = Tracking.objects.filter(reference = jobneed.get('uuid')).order_by('receiveddate')
            line = [[coord for coord in obj.gpslocation] for obj in between_latlngs]
            if len(line) > 1:
                log.info("between lat lngs found for the tour with uuid %s" % jobneed.get('uuid'))
                ls = LineString(line, srid = 4326)
                ls.transform(4326)
                sitetour.journeypath = ls
                sitetour.save()
                info = between_latlngs.delete()
                log.info(f"Between latlngs are deleted and their info is following\n {info}")
                log.info("save linestring is saved..")
        except Exception as e:
            log.critical('ERROR while saving line string', exc_info = True)
            raise
        else:
            sitetour =  Jobneed.objects.get(uuid=jobneed.get('uuid'))
            log.info(f"line string saved printing it {pformat(sitetour.journeypath)} for the tour with uuid {jobneed.get('uuid')}")
    else:
        log.info(f"saving line string ended because conditions not met")
        

@app.task(bind = True, default_retry_delay = 300, max_retries = 5, name = 'perform_insertrecord()')
def perform_insertrecord(self, records,  db='default', filebased = True, bg=False, userid=None):
    """
    Insert records in specified tablename.

    Args:
        file (file|json): file object| json data
        tablename (str): name of table
        request (http wsgi request, optional): request object. Defaults to None.
        filebased (bool, optional): type of data, file (True) or json (False) Defaults to True.

    Returns:
        ServiceOutputType: rc, recordcount, msg, traceback
    """
    rc, recordcount, traceback, msg = 1, 0, 'NA', Messages.INSERT_FAILED
    
    instance = None
    log.info(f"""perform_insertrecord( records = {type(records)}, bg = {bg}, db = {db}, filebased = {filebased}  { userid = } runnning in {'background' if bg else "foreground"})""")
    try:
        data = [json.loads(record) for record in records]
        log.info(f'data = {pformat(data)} and length of data {len(data)}')

        if len(data) == 0: raise excp.NoRecordsFound
        with transaction.atomic(using = db):
            for record in data:
                if record:
                    tablename = record.pop('tablename')
                    log.info(f'Table Name: {tablename}')
                    log.info("Record %s",record)
                    obj = insert_or_update_record(record, tablename)
                    if record.get('people_id') == None:
                        id = record.get('muser_id')
                    else:
                        id = record.get('people_id')
                    user = get_user_instance(id)
                    
                    if tablename == 'ticket' and isinstance(obj, Ticket): utils.store_ticket_history(
                        instance = obj,  user=user)
                    if tablename == 'wom':
                        wutils.notify_wo_creation(id = obj.id)
                    allconditions = [
                        hasattr(obj, 'peventtype'), hasattr(obj, 'endlocation'), 
                        hasattr(obj, 'punchintime'), hasattr(obj, 'punchouttime')]

                    if all(allconditions) and all([tablename == 'peopleeventlog',
                            obj.peventtype.tacode in ('CONVEYANCE', 'AUDIT'),
                            obj.endlocation,obj.punchouttime, obj.punchintime]):
                        log.info("save line string is started")
                        save_linestring_and_update_pelrecord(obj)
                    check_for_sitecrisis(obj, tablename, user)
                    recordcount += 1
                    log.info(f'{recordcount} record inserted successfully')
        if len(data) == recordcount:
            msg = Messages.INSERT_SUCCESS
            log.info(f'All {recordcount} records are inserted successfully')
            rc=0
    except excp.NoRecordsFound as e:
        log.warning('No records found for insertrecord service', exc_info=True)
        rc, traceback, msg = 1, tb.format_exc(), Messages.INSERT_FAILED
    except Exception as e:
        log.error("something went wrong!", exc_info = True)
        traceback =  tb.format_exc()
    results = ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback)
    return results.__dict__ if bg else results


def check_for_tour_track(obj, tablename):
    allconditions = [
        hasattr(obj, 'peventtype'), hasattr(obj, 'endlocation'), 
        hasattr(obj, 'punchintime'), hasattr(obj, 'punchouttime')]

    if all(allconditions) and all([tablename == 'peopleeventlog',
            obj.peventtype.tacode in ('CONVEYANCE', 'AUDIT'),
            obj.endlocation,obj.punchouttime, obj.punchintime]):
        log.info("save line string is started")
        save_linestring_and_update_pelrecord(obj)


def check_for_sitecrisis(obj, tablename, user):
    if tablename == 'peopleeventlog':
        model = apps.get_model('attendance', 'PeopleEventlog')
        if obj.peventtype.tacode in model.objects.get_sitecrisis_types():
            log.info("Site Crisis found raising a ticket")
            Ticket = apps.get_model('y_helpdesk', 'Ticket')
            ESM = apps.get_model('y_helpdesk', 'EscalationMatrix')
            # generate ticket sitecrisis appeared
            esc = ESM.objects.select_related('escalationtemplate').filter(
                escalationtemplate__tacode='TC_SITECRISIS',
                escalationtemplate__tatype__tacode='TICKETCATEGORY',
                bu_id=user.bu_id
            ).order_by('level').first()
            if esc:
                raise_ticket(Ticket, user, esc, obj)
                log.info("Ticket raised")
            else:
                esc = create_escalation_matrix_for_sitecrisis(ESM, user)
                log.info("Escalation was not set, so created one")
                raise_ticket(Ticket, user, esc, obj)
                log.info("Ticket raised")
                
                

def raise_ticket(Ticket, user, esc, obj):
    
    Ticket.objects.create(
        ticketdesc=f'{obj.remarks}',
        assignedtopeople=esc.assignedperson,
        assignedtogroup_id=1,
        identifier=Ticket.Identifier.TICKET,
        client=user.client,
        bu=user.bu,
        priority=Ticket.Priority.HIGH,
        ticketcategory_id=esc.escalationtemplate_id,
        level=1,
        status=Ticket.Status.NEW,
        isescalated=False,
        ticketsource=Ticket.TicketSource.SYSTEMGENERATED,
        ctzoffset=obj.ctzoffset
    )

def create_escalation_matrix_for_sitecrisis(ESM, user):
    People = apps.get_model('peoples', 'People')
    assigneduser = People.objects.get_sitemanager_or_emergencycontact(user.bu) or user.bu.cuser
    if assigneduser:
        TypeAssist = apps.get_model('onboarding', 'TypeAssist')
        site_crisis_obj = TypeAssist.objects.filter(tacode='TC_SITECRISIS', tatype__tacode='TICKETCATEGORY').first()
        return ESM.objects.create(
            cuser=user, muser=user, level=1, job_id=1, 
            frequency='MINUTE', frequencyvalue=30, assignedfor='PEOPLE',
            bu=user.bu, client=user.client, escalationtemplate = site_crisis_obj,
            assignedperson=assigneduser, assignedgroup_id=1
        )

            
    


@app.task(bind = True, default_retry_delay = 300, max_retries = 5,  name = 'perform_reportmutation')
def perform_reportmutation(self, records, db= 'default', bg=False):
    rc, recordcount, traceback, msg= 1, 0, 'NA', Messages.INSERT_FAILED
    instance = None
    try:
        log.info(
            f"""perform_reportmutation(records = {type(records)}, bg = {bg}, db = {db}, runnning in {'background' if bg else "foreground"})"""
        )
        data = [json.loads(record) for record in records]
        log.info(f'data: {pformat(data)}')
        if len(data) == 0: raise excp.NoRecordsFound
        log.info(f"'data = {pformat(data)} {len(data)} Number of records found in the file")
        for record in data:
            if record:
                tablename = record.pop('tablename', None)
                is_return_workpermit = record.pop('isreturnwp', None)
                child = record.pop('child', None)
                parent = record

                log.info(f"Parent: ------------> {parent}")
                log.info(f"Child: ------------> {child}")
                verifers = record.pop('verifier',None)
                log.info(f"Verifier: ------------> {verifers}")
                try:
                    switchedSerializer = sz.WomSerializer if tablename == 'wom' else sz.JobneedSerializer
                    log.info(f"Switched Serializer: ------------> {switchedSerializer}")
                    with transaction.atomic(using = db):
                        if child and len(child) > 0 and parent:
                            jobneed_parent_post_data = parent
                            jn_parent_serializer = switchedSerializer(data = clean_record(jobneed_parent_post_data))
                            log.info(f'switched serializer is {switchedSerializer}')
                            rc,  traceback, msg = save_parent_childs(sz, jn_parent_serializer, child, Messages, tablename, is_return_workpermit,verifers)
                            if rc == 0: recordcount += 1
                        else:
                            log.error(Messages.NODETAILS)
                            msg, rc = Messages.NODETAILS, 1
                except Exception as e:
                    log.error('something went wrong while saving \
                            parent and child for report mutations', exc_info = True)
                    raise
        if len(data) == recordcount:
            msg = Messages.UPDATE_SUCCESS
            log.info(f'All {recordcount} report records are updated successfully')
            rc=0
        log.info(f'Data, {data}')
    except excp.NoRecordsFound as e:
        log.warning('No records found for report mutation', exc_info=True)
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
    except Exception as e:
        msg, traceback, rc = Messages.INSERT_FAILED, tb.format_exc(), 1
        log.error('something went wrong', exc_info = True)
    results = ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback)
    return results.__dict__ if bg else results


@app.task(bind = True, default_retry_delay = 300, max_retries = 5, name = 'perform_adhocmutation')
def perform_adhocmutation(self, records, db='default', bg=False):  # sourcery skip: remove-empty-nested-block, remove-redundant-if, remove-redundant-pass
    rc, recordcount, traceback, msg= 1, 0, 'NA', Messages.INSERT_FAILED
    try:
        log.info(
            f"""perform_adhocmutation(records = {records}, bg = {bg}, db = {db}, runnning in {'background' if bg else "foreground"})"""
        )
        data = [json.loads(record) for record in records]
        for record in data:
            if record:
                details = record.pop('details')
                jobneedrecord = record

                with transaction.atomic(using = db):
                    if jobneedrecord['asset_id'] ==  1:
                        # then it should be NEA
                        assetobjs = Asset.objects.filter(bu_id = jobneedrecord['bu_id'],
                                        assetcode = jobneedrecord['remarks'])
                        jobneedrecord['asset_id']= 1 if assetobjs.count()  !=  1 else assetobjs[0].id
                    
                    jobneedrecord = clean_record(jobneedrecord)
                    scheduletask = Jobneed.objects.get_schedule_for_adhoc(
                        jobneedrecord['qset_id'], jobneedrecord['people_id'], jobneedrecord['asset_id'], jobneedrecord['bu_id'], jobneedrecord['starttime'], jobneedrecord['endtime'])

                    log.info(f"schedule task: {pformat(scheduletask)}")
                    log.info(f"jobneed record: {pformat(jobneedrecord)}")
                    # have to update to scheduled task/reconsilation
                    if(len(scheduletask) > 0) and scheduletask['identifier'] == 'TASK' :
                        log.info("schedule task found, updating it now")
                        rc, traceback, msg, recordcount = update_adhoc_record(scheduletask, jobneedrecord, details)
                    # have to insert/create to adhoc task
                    else:
                        log.info("schedule task not found, creating a new one")
                        rc, traceback, msg, recordcount = insert_adhoc_record(jobneedrecord, details)
    except excp.NoDataInTheFileError as e:
        rc, traceback = 1, tb.format_exc()
        log.error('No data in the file error', exc_info = True)
        raise
    except Exception as e:
        rc, traceback = 1, tb.format_exc()
        log.error('something went wrong', exc_info = True)
    results = ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback)
    return results.__dict__ if bg else results

def perform_uploadattachment(file,  record, biodata):
    rc, traceback, resp = 1,  'NA', 0
    recordcount, msg = None, Messages.UPLOAD_FAILED
    
    
    file_buffer = file
    filename    = biodata['filename']
    peopleid    = biodata['people_id']
    path        = biodata['path']
    ownerid     = biodata['owner']
    onwername   = biodata['ownername']
    home_dir    = f'{settings.MEDIA_ROOT}/'
    filepath    = home_dir + path
    uploadfile  = f'{filepath}/{filename}'
    db          = utils.get_current_db_name()
    log.info(f"Upload File: {filepath}, {filename}")
    log.info(f"Length file_buffer: '{len(file_buffer)}' \n'onwername':{onwername}, \nownerid: '{ownerid}' \npeopleid: '{peopleid}' \npath: {path} \nhome_dir: '{home_dir}' \nfilepath: '{filepath}' \nuploadfile: '{uploadfile}'")
    try:
        with transaction.atomic(using = db):
            iscreated = get_or_create_dir(filepath)
            log.info(f'Is FilePath created? {iscreated}')
            relative_path = path + filename
            #write_file_to_dir(file_buffer, uploadfile)
            write_file_to_dir(file_buffer, relative_path)
            rc, traceback, msg = 0, tb.format_exc(), Messages.UPLOAD_SUCCESS
            recordcount = 1
            log.info('file uploaded success')
    except Exception as e:
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
        log.error('something went wrong', exc_info = True)
    try:
        log.info(f'Record Attachment: {record}')
        if record.get('localfilepath'): record.pop('localfilepath')
        obj = insert_or_update_record(record, 'attachment')        
        eobj = log_event_info(onwername, ownerid)
        if hasattr(eobj, 'peventtype') and eobj.peventtype.tacode in ['SELF', 'MARK', 'MARKATTENDANCE', 'SELFATTENDANCE']:
            from background_tasks.tasks import perform_facerecognition_bgt
            results = perform_facerecognition_bgt.delay(ownerid, peopleid, db)
            log.warning(f"face recognition status {results.state} and {results} and task_id={results.task_id}")
    except Exception as e:
        log.error('something went wrong while perform_uploadattachment', exc_info = True)
    return ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback)


def log_event_info(onwername, ownerid):
    log.info(f"ownername:{onwername} and owner:{ownerid}")
    model = get_model_or_form(onwername.lower())
    eobj = model.objects.get(uuid=ownerid)
    log.info(f"object retrived of type {type(eobj)}")
    if hasattr(eobj, 'peventtype'): log.info(f'Event Type: {eobj.peventtype.tacode}')
    return eobj


def execute_graphql_mutations(mutation_query, variables=dict(), download=False):
    from apps.service.schema import schema


    # Execute the GraphQL mutation with the file object
    result = schema.execute(
        mutation_query,
        variable_values=variables
    )

    log.info(f"Mutation query: {mutation_query}")
    if result.errors:
        # Handle errors
        error_messages = [error.message for error in result.errors]
        log.error(f"Mutation errors: {pformat(error_messages)}", exc_info=True)
        resp = json.dumps({'errors': error_messages})
        raise Exception(f"GraphQL mutation failed with errors {resp}")
    else:
        if download:
            resp = {'data': result.data}
        else:
            resp = json.dumps({'data': result.data})
    log.info(f'Response Data: ,{resp}')
    return resp