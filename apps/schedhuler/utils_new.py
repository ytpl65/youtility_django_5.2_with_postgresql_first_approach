from django.db.models import Q, F, Subquery
from django.core.exceptions import EmptyResultSet
from django.db import transaction, DatabaseError
from django.http import response as rp
from apps.activity.models.job_model import Job,Jobneed,JobneedDetails
from apps.activity.models.asset_model import Asset
from apps.activity.models.question_model import Question,QuestionSet,QuestionSetBelonging
from apps.y_helpdesk.models import Ticket, EscalationMatrix
from logging import getLogger
from pprint import pformat
from random import shuffle
from apps.core import utils
from datetime import datetime, timezone, timedelta
from django.utils import timezone as dtimezone
from django.db.models.query import QuerySet
from apps.reminder.models import Reminder
import random
import traceback as tb
from intelliwiz_config.celery import app
from celery import shared_task
from celery.utils.log import get_task_logger
from intelliwiz_config.settings import GOOGLE_MAP_SECRET_KEY as google_map_key

log = get_task_logger('__main__')



def get_service_requirements(route):
    """
    Returns start point, end point, waypoints
    required for directions API
    """
    if route:
        start_point = {
            "lat": float(route[0]['cplocation'].coords[1]),
            "lng": float(route[0]['cplocation'].coords[0])
        }

        end_point = {
            "lat": float(route[-1]['cplocation'].coords[1]),
            "lng": float(route[-1]['cplocation'].coords[0])
        }

        waypoints = []
        for i in range(1, len(route) - 1):
            lat, lng = route[i]['cplocation'].coords[1], route[i]['cplocation'].coords[0]
            waypoints.append({"lat": lat, "lng": lng})

        return start_point, end_point, waypoints



def convertto_namedtuple(A,records, freq, btime):
    """
    converts dict to namedtuple
    """
    rec, C = [], records[0].keys()
    from collections import namedtuple
    for i, item in enumerate(records):
        record = namedtuple("Record", C)
        item["seqno"] = i+1
        item["jobname"] = f"[{str(item['seqno'])}]-{item['jobname']}"
        tr = tuple(item.values())
        rec.append(record(**dict(list(zip(C, tr)))))
    
    if freq>1 or btime!=0:
        rec[0] = rec[0]._replace(distance=0) 
        rec[0] = rec[0]._replace(expirytime=0)
        rec[0] = rec[0]._replace(breaktime=0)
    return rec



import googlemaps
import copy

def calculate_route_details(route, job):
    """Calculate route details"""
    data = route
    gmaps = googlemaps.Client(key=google_map_key)

    startpoint, endpoint, waypoints = get_service_requirements(data)

    directions = gmaps.directions(mode='driving', waypoints=waypoints, origin=startpoint, destination=endpoint,
                                  optimize_waypoints=True)
    waypoint_order = directions[0]["waypoint_order"]
    freq, breaktime = job['other_info']['tour_frequency'], job['other_info']['breaktime']

    data[0]['seqno'] = 0 + 1
    checkpoints = [data[0]]
    checkpoints[0]['distance'] = 0
    checkpoints[0]["duration"] = 0
    checkpoints[0]["expirytime"] = 0

    for i, item in enumerate(waypoint_order):
        data[i + 1]['seqno'] = i + 1 + 1
        checkpoints.append(data[item + 1])

    data[len(data) - 1]["seqno"] = len(data) - 1 + 1
    checkpoints.append(data[len(data) - 1])

    legs = directions[0]["legs"]
    dde = []
    for i, leg in enumerate(legs):
        l = []
        checkpoints[i + 1]['distance'] = round(float(leg['distance']["value"] / 1000), 2)
        l.append(checkpoints[i + 1]["distance"])
        checkpoints[i + 1]['duration'] = float(leg["duration"]["value"])
        l.append(checkpoints[i + 1]['duration'])
        checkpoints[i + 1]['expirytime'] = int(leg["duration"]["value"] / 60)
        l.append(checkpoints[i + 1]['expirytime'])
        dde.append(l)

    if freq > 1:
        checkpoints += get_frequency_data(dde, checkpoints, freq, breaktime)
        if breaktime != 0:
            endp = int(len(checkpoints) / freq)
            checkpoints[endp]['breaktime'] = breaktime
    return checkpoints


def get_frequency_data(dde, data, f, breaktime):
    """
    Randomize data based on frequency
    """
    data_copy = copy.deepcopy(data)
    return [data + reverse_frequency_points(dde, data_copy, breaktime) for _ in range(f - 1)]


def reverse_frequency_points(dde, data, breaktime):
    """
    Reverse frequencies data points.
    """
    result, j = [], 0
    dde = dde[::-1]
    for i in reversed(range(len(data))):
        if (i == len(data)-1):
            data[i]['distance'] = data[i]['duration'] = data[i]['expirytime'] = data[i]['breaktime'] = 0
        else:
            data[i]['distance'], data[i]['duration'], data[i]['expirytime'] = dde[j]
            j += 1
        result.append(data[i])
    result[-1]['breaktime'] = breaktime
    return result



@shared_task(name="create_job")
def create_job(job_ids=None):
    """
    Create jobs based on the provided job ids
    """

    result = _initialize_result()

    with transaction.atomic(using=utils.get_current_db_name()):
        try:
            jobs = _get_jobs(job_ids)

            if not jobs:
                msg = "No jobs found. Scheduling terminated."
                log.warning(msg, exc_info=True)
                return {'msg': msg}, result

            log.info(f"Processing jobs started. Found '{len(jobs)}' jobs.")
            
            for idx, job in enumerate(jobs):
                result = _process_job(job, result)

            if result['F']:
                log.info(f"Failed job schedule list: {pformat(result['F'])}")

            log.info(
                f"createJob() [end-] [{idx} of {len(jobs) - 1}] "
                f"parent job: {job['jobname']} | job: {job['id']} | cron: {job['cron']}"
            )

        except Exception as e:
            log.error("Something went wrong!", exc_info=True)

    return result['resp'], result

def _initialize_result():
    """Initialize result structure."""
    return {'F': {}, 'd': [], 'story': "", 'id': [], 'resp': None}

def _get_jobs(job_ids):
    """Fetch jobs from the database"""
    jobs = Job.objects.filter(
        ~Q(jobname='NONE'),
        ~Q(asset__runningstatus=Asset.RunningStatus.SCRAPPED),
        parent_id=1,
        enable=True
    ).select_related(
        "asset", "pgroup", "cuser", "muser", "qset", "people",
    ).values(*utils.JobFields.fields)

    if job_ids:
        jobs = jobs.filter(id__in=job_ids)
    
    return jobs

def _process_job(job, result):
    """Process a single job and update result accordingly"""
    result['story'] += f'Processing job with id: {job["id"]}'
    
    startdtz, enddtz = calculate_startdtz_enddtz(job)
    log.debug(f"Jobs to be scheduled from {startdtz} to {enddtz}")

    DT, is_cron, result['resp'] = get_datetime_list(job['cron'], startdtz, enddtz)
    
    if not DT: 
        result['resp'] =  {'msg': "Please check your 'Valid From' and 'Valid To' dates"}
        return result
    
    log.debug(
        "Jobneed will create for all these datetimes:\n %s", 
        pformat(get_readable_dates(DT))
    )
    
    if not is_cron: 
        result['F'][str(job['id'])] = {'cron': job['cron']}
    
    status, result['resp'] = insert_into_jn_and_jnd(job, DT)
    
    if status:
        result['d'].append({
            "job": job['id'],
            "jobname": job['jobname'],
            "cron": job['cron'],
            "iscron": is_cron,
            "count": len(DT),
            "status": status
        })
        result['id'].append(job['id'])
    
    return result


def display_jobs_date_info(cdtz, mdtz, fromdate, uptodate, ldtz):
    padd = "#"*8
    log.info(f"{padd} display_jobs_date_info [start] {padd}")
    log.info(f"created-on:= [{cdtz}] modified-on:=[{mdtz}]")
    log.info(f"valid-from:= [{fromdate}] valid-upto:=[{uptodate}]")
    log.info(f"before lastgeneratedon:= [{ldtz}]")
    log.info(f"{padd} display_jobs_date_info [end] {padd}")

def get_readable_dates(dt_list):
    if (isinstance(dt_list, list)):
        return [dt.strftime("%d-%b-%Y %H:%M") for dt in dt_list]


def calculate_startdtz_enddtz(job):
    """
    Determine or calculate the plan datetime & expiry datetime of a job for the next 2 days or up to a certain date.
    """

    log.info(f"Calculating start and end datetime for job ID: {job['id']}")

    timezone_offset = timedelta(minutes=int(job['ctzoffset']))
    tz = timezone(timezone_offset)
    
    # Applying timezone offset and cleaning up the microseconds for each datetime
    job_datetimes = ['cdtz', 'mdtz', 'fromdate', 'uptodate', 'lastgeneratedon']
    dtz = {item: _apply_timezone_offset(job[item], tz, timezone_offset) for item in job_datetimes}
    
    current_date_utc = datetime.utcnow().replace(tzinfo=timezone.utc, microsecond=0)
    current_date = _apply_timezone_offset(current_date_utc, tz, timezone_offset)
    
    if dtz['mdtz'] > dtz['cdtz']:
        dtz['lastgeneratedon'] = current_date
        delete_old_jobs(job['id'])
        
    startdtz = max(dtz['fromdate'], dtz['lastgeneratedon'], current_date)
    enddtz = min(dtz['uptodate'], startdtz + timedelta(days=2))
    
    return startdtz, enddtz

def _apply_timezone_offset(dt, tz, offset):
    """Apply timezone offset to a datetime and remove microseconds."""
    return dt.replace(microsecond=0, tzinfo=tz) + offset


def get_datetime_list(cron_exp, startdtz, enddtz):
    """
    Calculates and returns array of next start times for every day up to enddatetime
    based on given cron expression.
    E.g., returning all start times from 1/01/20xx --> 3/01/20xx based on cron expression.
    """

    log.info(f"Generating datetime list for cron: '{cron_exp}', start time: '{startdtz}', and end time: '{enddtz}'")

    from croniter import croniter, CroniterBadCronError

    datetimes = []
    is_valid_cron = True
    error_message = None

    try:
        cron_iterator = croniter(cron_exp, startdtz)
        while True:
            next_datetime = cron_iterator.get_next(datetime)
            if next_datetime < enddtz:
                datetimes.append(next_datetime)
            else:
                break
    except CroniterBadCronError:
        is_valid_cron = False
        error_message = {"msg": "Bad Cron Error"}
        log.warning("Bad Cron error", exc_info=True)
    except Exception as ex:
        is_valid_cron = False
        error_message = {"msg": "Bad Cron Error"}
        log.critical(f"Error in get_datetime_list for cron expression '{cron_exp}': {str(ex)}", exc_info=True)
        raise ex from ex

    if datetimes:
        log.info(f'Calculated datetime list: {pformat(datetimes, compact=True)}')
    else:
        error_message = {"msg": "Unable to schedule task, check your 'Valid From' and 'Valid To'"}

    return list(set(datetimes)), is_valid_cron, error_message


def dt_local_to_utc(tzoffset, data, mob_or_web):
    log.info('dt_local_to_utc [start]')
    dtlist= udt= cdt= dateFormate= None
    dateRegexMobile= r"[0-9]{4}-[0-9]{2}-[0-9]{02} [0-9]{02}:[0-9]{02}:[0-9]{02}"
    dateRegexWeb= r"[0-9]{2}-[A-Za-z]{3}-[0-9]{4} [0-9]{02}:[0-9]{02}"
    dateFormatMobile= "%Y-%m-%d %H:%M:%S"
    dateFormatWeb= "%d-%b-%Y %H:%M"

    if isinstance(data, dict):
        handle_dict_of_datetimes(dateFormatMobile, dateFormatWeb, data, tzoffset,
                                 dateRegexMobile, dateRegexWeb, mob_or_web)

    else:
        handle_list_of_datetimes(dateFormatMobile, dateFormatWeb, data,  tzoffset,
                                 dateRegexMobile, dateRegexWeb, mob_or_web)
    return data

def handle_dict_of_datetimes(dateFormatMobile, dateFormatWeb, data, tzoffset,
                            dateRegexMobile, dateRegexWeb, mob_or_web):
    import re
    for key, value in data.items():
        value= str(value)
        if mob_or_web.lower() == "mobile":
            dtlist= re.findall(dateRegexMobile, value)
            dateFormate= dateFormatMobile
        elif (
            mob_or_web.lower() != "mobile"
            and mob_or_web.lower() == "web"
            or mob_or_web.lower() != "mobile"
            and mob_or_web.lower() != "web"
            and mob_or_web.lower() == "cron"
        ):
            dtlist= re.findall(dateRegexWeb, value)
            dateFormate= dateFormatWeb
        if dtlist := list(set(dtlist)):
            log.info(f"dt_local_to_utc got all date: {dtlist}")
            try:
                tzoffset= int(tzoffset)
                for item_ in dtlist:
                    udt= cdt= None
                    try:
                        udt = (
                            datetime.strptime(
                                str(item_), dateFormate
                            )
                            .replace(tzinfo = timezone.utc)
                            .replace(microsecond = 0)
                        )
                        cdt= udt - timedelta(minutes= tzoffset)
                        data[key] = str(data[key]).replace(str(item_), str(cdt))
                    except Exception as ex:
                        log.critical("datetime parsing error", exc_info = True)
                        raise
            except ValueError:
                log.error("tzoffset parsing error", exc_info = True)
                raise

def handle_list_of_datetimes(dateFormatMobile, dateFormatWeb, data, tzoffset,
                            dateRegexMobile, dateRegexWeb, mob_or_web):
    import re
    if mob_or_web.lower() == "mobile":
        dtlist= re.findall(dateRegexMobile, str(data))
        dateFormate= dateFormatMobile
    elif (
        mob_or_web.lower() != "mobile"
        and mob_or_web.lower() == "web"
        or mob_or_web.lower() != "mobile"
        and mob_or_web.lower() != "web"
        and mob_or_web.lower() == "cron"
    ):
        dtlist= re.findall(dateRegexWeb, data)
        dateFormate= dateFormatWeb
    if dtlist := list(set(dtlist)):
        log.info(f"got all date {dtlist}")
        try:
            tzoffset= int(tzoffset)
            for item in dtlist:
                udt= cdt= None
                try:
                    udt = (
                        datetime.strptime(str(item), dateFormate)
                        .replace(tzinfo = timezone.utc)
                        .replace(microsecond = 0)
                    )

                    cdt= udt - timedelta(minutes= tzoffset)
                    data = str(data).replace(str(item), str(cdt))
                except Exception as ex:
                    log.critical("datetime parsing error", exc_info = True)
                    raise
        except ValueError:
            log.error("tzoffset parsing error", exc_info = True)
            raise



def process_datetime(dt, duration_mins, params):
    dt = dt.strftime("%Y-%m-%d %H:%M")
    dt = datetime.strptime(dt, '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)
    pdtz = params['pdtz'] = dt
    edtz = params['edtz'] = dt + timedelta(minutes=duration_mins)
    return pdtz, edtz

def process_jobneed(job, params, crontype, people, pdtz, jobstatus, jobtype):
    jobneed = insert_into_jn_for_parent(job, params)
    is_parent = crontype in (Job.Identifier.INTERNALTOUR.value, Job.Identifier.EXTERNALTOUR.value)
    insert_update_jobneeddetails(jobneed.id, job, is_parent=is_parent)
    return jobneed, is_parent

def update_jobneed_expiry(job, jobneed, crontype, pdtz, people, jobstatus, jobtype):
    if isinstance(jobneed, Jobneed):
        log.info(f"Creating parent jobneed: {jobneed.id}")
        if crontype in (Job.Identifier.INTERNALTOUR.value, Job.Identifier.EXTERNALTOUR.value):
            edtz = create_child_tasks(job, pdtz, people, jobneed.id, jobstatus, jobtype, jobneed.other_info)
            if edtz is not None:
                num_updated = Jobneed.objects.filter(id = jobneed.id).update(expirydatetime = edtz)
                if num_updated <= 0:
                    raise ValueError

def insert_into_jn_and_jnd(job, datetimes):
    """
    Calculates expiry datetime for each datetime in 'datetimes' list and
    inserts into jobneed and jobneed-details for all dates in 'datetimes' list.
    """
    log.info("Inserting into jobneed and jobneed-details...")

    if len(datetimes) > 0:
        try:
            # Required variables
            NONE_JN = utils.get_or_create_none_jobneed()
            NONE_P = utils.get_or_create_none_people()
            crontype = job['identifier']
            jobstatus = 'ASSIGNED'
            jobtype = 'SCHEDULE'
            jobdesc = f'{job["jobname"]}'
            asset = Asset.objects.get(id = job['asset_id'])
            multiplication_factor = asset.asset_json['multifactor']
            people = job['people_id']
            duration_mins = job['planduration'] + job['expirytime'] + job['gracetime']
            params = {
                'jobstatus': jobstatus, 
                'jobtype': jobtype, 
                'route_name': job['sgroup__groupname'],
                'm_factor': multiplication_factor, 
                'people': people,
                'NONE_P': NONE_P, 
                'jobdesc': jobdesc, 
                'NONE_JN': NONE_JN
            }
            utc_datetimes = utils.to_utc(datetimes)
            for dt in utc_datetimes:
                pdtz, edtz = process_datetime(dt, duration_mins, params)
                jobneed, is_parent = process_jobneed(job, params, crontype, people, pdtz, jobstatus, jobtype)
                update_jobneed_expiry(job, jobneed, crontype, pdtz, people, jobstatus, jobtype)
            update_lastgeneratedon(job, pdtz)
        except Exception as ex:
            log.critical('Error inserting into jobneed and jobneed-details', exc_info=True)
            return 'failed', {"msg": "Failed to schedule jobs"}

        log.info(f"{len(datetimes)} tasks scheduled successfully!")
        return 'success', {'msg': f'{len(datetimes)} tasks scheduled successfully!', 'count': len(datetimes)}

    log.info("No datetime provided for insertion into jobneed and jobneed-details.")
    return 'failed', {"msg": "No datetime provided."}


def insert_into_jn_for_parent(job, params):
    jobneed_defaults = {
        'ctzoffset': job['ctzoffset'],
        'priority': job['priority'],
        'identifier': job['identifier'],
        'gpslocation': 'POINT(0.0 0.0)',
        'remarks': '',
        'multifactor': params['m_factor'],
        'client_id': job['client_id'],
        'other_info': job['other_info'],
        'cuser_id': job['cuser_id'],
        'muser_id': job['muser_id'],
        'ticketcategory_id': job['ticketcategory_id'],
        'frequency': 'NONE',
        'bu_id': job['bu_id'],
        'seqno': 0,
        'scantype': job['scantype'],
        'gracetime': job['gracetime'],
        'performedby': params['NONE_P'],
        'jobstatus': params['jobstatus'],
        'plandatetime': params['pdtz'],
        'expirydatetime': params['edtz']
    }

    jobneed = Jobneed.objects.create(
        **jobneed_defaults,
        job_id=job['id'],
        parent=params['NONE_JN'],
        jobdesc=params['jobdesc'],
        qset_id=job['qset_id'],
        asset_id=job['asset_id'],
        people_id=params['people'],
        pgroup_id=job['pgroup_id'],
        jobtype=params['jobtype']
    )
    
    return jobneed




from django.core.exceptions import ObjectDoesNotExist

def insert_update_jobneeddetails(jobneed_id, job, is_parent=False):
    """
    Update job details by deleting existing details, retrieving question sets, and inserting new details.
    """

    log.info(f"Started updating job details for JobID: {jobneed_id}, Job: {job}, Is Parent: {is_parent}")

    # Delete existing job details
    try:
        JobneedDetails.objects.filter(jobneed_id=jobneed_id).delete()
        log.info(f"Existing job details for JobneedID: {jobneed_id} are deleted.")
    except ObjectDoesNotExist:
        log.warning(f"No job details found for JobneedID: {jobneed_id} to delete.")

    # Retrieve a set of questions
    try:
        if is_parent:
            question_set = utils.get_or_create_none_qsetblng()
        else:
            question_set = QuestionSetBelonging.objects.select_related('question').filter(qset_id=job['qset_id']).order_by('seqno').values_list(named=True)

        # Check if questions exist
        if not question_set:
            log.error(f"No checklist found for Job: {job}, failed to schedule job.")
            raise EmptyResultSet
        else:
            question_set_length = len(question_set) if isinstance(question_set, QuerySet) else 1
            log.info(f"Checklist found with {question_set_length} questions for Job: {job}.")
            
            # Insert questions into job details
            insert_into_jnd(question_set, job, jobneed_id, is_parent)

    except Exception as e:
        log.error(f"An error occurred while updating job details for JobID: {jobneed_id}, Job: {job}, Is Parent: {is_parent} - {str(e)}", exc_info=True)
        raise

    log.info(f"Finished updating job details for JobID: {jobneed_id}, Job: {job}, Is Parent: {is_parent}")





def insert_into_jnd(qsb, job, jnid, parent=False):
    log.info("insert_into_jnd() [START]")
    qset = qsb if isinstance(qsb, QuerySet) else [qsb]
    for obj in qset:
        answer = 'NONE' if parent else None
        JobneedDetails.objects.create(
            seqno      = obj.seqno,      question_id = obj.question_id,
            answertype = obj.answertype, max         = obj.max,
            min        = obj.min,        alerton     = obj.alerton,
            options    = obj.options,    jobneed_id  = jnid,
            cuser_id   = job['cuser_id'],   muser_id    = job['muser_id'],
            ctzoffset  = job['ctzoffset'], answer = answer,
            isavpt = obj.isavpt, avpttype = obj.avpttype)
    log.info("insert_into_jnd() [END]")

def extract_seq(R):
    return [r['seqno'] for r in R]


def check_sequence_of_prevjobneed(job, current_seq):
    previousJobneedParent = Jobneed.objects.filter(job_id=job['id'], parent_id=1).order_by('-id')
    if previousJobneedParent.count() > 1:
        seqnos = Jobneed.objects.filter(parent_id = previousJobneedParent.values_list('id', flat=True)[1]).values_list('seqno', flat=True)
        return list(seqnos) == current_seq
    return False
    
    


def create_child_tasks(job, initial_plan_datetime, assigned_people, jobneed_id, job_status, job_type, parent_other_info):
    """
    Creates child tasks for a given job.
    """
    log.info(f"Started creating child tasks for Job: {job}, Initial Plan Datetime: {initial_plan_datetime}, Assigned People: {assigned_people}, JobNeedID: {jobneed_id}, Job Status: {job_status}, Job Type: {job_type}, Parent Other Info: {parent_other_info}")

    try:
        NONE_P = utils.get_or_create_none_people()
        previous_expiry_datetime, tour_frequency = initial_plan_datetime, 1

        # Retrieve jobs ordered by sequence number
        jobs = retrieve_jobs(job)
        params = initialize_params(assigned_people, job_status, job_type, jobneed_id, NONE_P, parent_other_info)

        jobs_list = list(jobs)
        jobs, tour_frequency = randomize_and_calculate_routes_if_needed(job, jobs_list)

        breaktime_index = len(jobs) // tour_frequency
        for index, job_data in enumerate(jobs):
            log.info(f"Creating child job {index}: {job_data['jobname']} | Job ID: {job_data['id']} | Cron: {job_data['cron']}")

            params = update_params(job, job_data, params, index)

            if job['other_info'].get('tour_frequency', False) and job['other_info'].get('breaktime', False) and breaktime_index == index:
                plan_datetime = params['pdtz'] = previous_expiry_datetime + timedelta(minutes=int(job['other_info'].get('breaktime')) + job_data['expirytime'])
            else:
                plan_datetime = params['pdtz'] = previous_expiry_datetime + timedelta(minutes=job_data['expirytime'])

            expiry_datetime = params['edtz'] = plan_datetime + timedelta(minutes=job['planduration'] + job['gracetime'])
            previous_expiry_datetime = expiry_datetime
            
            jobneed = insert_into_jn_for_child(job, params, job_data)
            insert_update_jobneeddetails(jobneed.id, job_data)

    except Exception as e:
        log.critical(f"An error occurred while creating child tasks - {str(e)}", exc_info=True)
        raise

    log.info(f"Finished creating child tasks for Job: {job}.")
    return expiry_datetime


def retrieve_jobs(job):
    """
    Retrieves jobs ordered by sequence number
    """
    return Job.objects.annotate(
        cplocation = F('bu__gpslocation')
    ).filter(
        parent_id = job['id']
    ).order_by(
        'seqno'
    ).values(*utils.JobFields.fields, 'cplocation', 'sgroup__groupname', 'bu__solid', 'bu__buname')


def initialize_params(assigned_people, job_status, job_type, jobneed_id, NONE_P, parent_other_info):
    """
    Initializes parameters
    """
    return {
        '_jobdesc': "", 'jnid': jobneed_id, 'pdtz': None, 'edtz': None,
        '_people': assigned_people, '_jobstatus': job_status, '_jobtype': job_type,
        'm_factor': None, 'idx': None, 'NONE_P': NONE_P, 'parent_other_info': parent_other_info
    }


def randomize_and_calculate_routes_if_needed(job, jobs_list):
    """
    Randomizes jobs and calculates routes if needed
    """
    tour_frequency = 1
    if job['other_info'].get('is_randomized', False) and len(jobs_list) > 1:
        # Randomize data if it is a random tour job
        random.shuffle(jobs_list)
        jobs_list = calculate_route_details(jobs_list, job)
        tour_frequency = int(job['other_info'].get('tour_frequency', 1))
    elif job['other_info'].get('tour_frequency') and int(job['other_info'].get('tour_frequency', 1)) > 1:
        tour_frequency = int(job['other_info'].get('tour_frequency', 1))
        jobs_list = calculate_route_details(jobs_list, job)
    return jobs_list, tour_frequency


def update_params(job, job_data, params, index):
    """
    Updates parameters for a given job
    """
    asset = Asset.objects.get(id=job_data['asset_id'])
    params['m_factor'] = asset.asset_json['multifactor']
    job_description = f"{job_data['asset__assetname']} - {job_data['jobname']}" 
    
    if job_data['identifier'] == 'EXTERNALTOUR':
        job_description = f"{job['sgroup__groupname']} - {job_data['bu__solid']} - {job_data['bu__buname']}" 

    params['_people'] = job_data['people_id']
    params['_jobdesc'] = job_description
    params['idx'] = index

    return params


def insert_into_jn_for_child(job, params, r):
    try:
        jn = Jobneed.objects.create(
                job_id         = job['id'],                     parent_id         = params['jnid'],
                jobdesc        = params['_jobdesc'],         plandatetime      = params['pdtz'],
                expirydatetime = params['edtz'],             gracetime         = job['gracetime'],
                asset_id       = r['asset_id'],                 qset_id           = r['qset_id'],
                pgroup_id      = job['pgroup_id'],              frequency         = 'NONE',
                priority       = r['priority'],                 jobstatus         = params['_jobstatus'],
                client_id      = r['client_id'],                jobtype           = params['_jobtype'],
                scantype       = job['scantype'],               identifier        = job['identifier'],
                cuser_id       = r['cuser_id'],                 muser_id          = r['muser_id'],
                bu_id          = r['bu_id'],                    ticketcategory_id = r['ticketcategory_id'],
                gpslocation    = 'SRID=4326;POINT(0.0 0.0)', remarks           = '',
                seqno          = params['idx'],              multifactor       = params['m_factor'],
                performedby    = params['NONE_P'],           ctzoffset         = r['ctzoffset'],
                people_id      = params['_people'],          other_info = params['parent_other_info']
            )
    except Exception:
        log.critical("insert_into_jn_for_child[]", exc_info=True)
        raise
    else:
        return jn


def job_fields(job, checkpoint, external = False):
    data =  {
        'jobname'     : f"{checkpoint.get('bu__buname', '')} :: {job['jobname']}",       'jobdesc'          : f"{checkpoint.get('bu__buname', '')} :: {job['jobname']} :: {checkpoint['qsetname']}",
        'cron'        : job['cron'],                                                    'identifier'       : job['identifier'],
            'expirytime'  : int(checkpoint['expirytime']),                                  'lastgeneratedon'  : job['lastgeneratedon'],
        'priority'    : job['priority'],                                                'qset_id'          : checkpoint['qsetid'],
        'pgroup_id'   : job['pgroup_id'],                                               'geofence'         : job['geofence_id'],
        'endtime'     : datetime.strptime(checkpoint.get('endtime', "00:00"), "%H:%M"), 'ticketcategory_id': job['ticketcategory_id'],
        'fromdate'    : job['fromdate'],                                                'uptodate'         : job['uptodate'],
        'planduration': job['planduration'],                                            'gracetime'        : job['gracetime'],
        'asset_id'    : checkpoint['assetid'],                                          'frequency'        : job['frequency'],
        'people_id'   : job['people_id'],                                               'starttime'        : datetime.strptime(checkpoint.get('starttime', "00:00"), "%H:%M"),
        'parent_id'   : job['id'],                                                      'seqno'            : checkpoint['seqno'],
        'scantype'    : job['scantype'],                                                'ctzoffset'        : job['ctzoffset'],
        'bu_id': job['bu_id'], 'client_id':job['client_id']
    }
    if external:
        jsonData = {
            'distance'      : checkpoint['distance'],
            'breaktime'     : checkpoint['breaktime'],
            'istimebound'   : job['other_info']['istimebound'],
            'is_randomized' : job['other_info']['is_randomized'],
            'tour_frequency': job['other_info']['tour_frequency']}
        data['jobname']    = f"{checkpoint['bu__buname']} :: {job['jobname']}"
        data['jobdesc']    = f"{checkpoint.get('bu__buname', '')} :: {job['jobname']} :: {checkpoint['qsetname']}"
        data['other_info'] = jsonData
    return data

def to_local(val):
    from django.utils.timezone import get_current_timezone
    return val.astimezone(get_current_timezone()).strftime('%d-%b-%Y %H:%M')

def delete_from_job(job, checkpointId, checklistId):
    try:
        Job.objects.get(
            parent     = int(job),
            asset_id = int(checkpointId),
            qset_id  = int(checklistId)).delete()
    except Exception:
        log.critical('delete_from_job() raised  error', exc_info=True)
        raise

def delete_from_jobneed(parentjob, checkpointId, checklistId):
    try:
        Jobneed.objects.get(
            parent     = int(parentjob),
            asset_id = int(checkpointId),
            qset_id  = int(checklistId)).delete()
    except Exception:
        log.critical("delete_from_jobneed() raised error", exc_info=True)
        raise

def update_lastgeneratedon(job, pdtz):
    try:
        log.info('update_lastgeneratedon [start]')
        if rec := Job.objects.filter(id = job['id']).update(
            lastgeneratedon = pdtz
        ):
            log.info(f"after lastgenreatedon:={pdtz}")
        log.info('update_lastgeneratedon [end]')
    except Exception:
        log.critical("update_lastgeneratedon() raised error", exc_info=True)
        raise

def send_email_notication(err):
    raise NotImplementedError()


def delete_old_jobs(job_id, ppm=False):
    """
    Delete old jobs and related data based on the given job ID.
    """
    # Get a list of related job IDs and include the given ID if ppm is True.
    job_ids = Job.objects.filter(parent_id=job_id).values_list('id', flat=True)
    job_ids = [job_id] + list(job_ids)

    # Set the old date to 1970-01-01 00:00:00 UTC.
    old_date = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    # Update jobneeddetails
    jobneed_ids = Jobneed.objects.filter(plandatetime__gt=dtimezone.now(), job_id__in=job_ids).values_list('id', flat=True)
    jnd_count = JobneedDetails.objects.filter(jobneed_id__in=jobneed_ids).update(cdtz=old_date, mdtz=old_date)

    # Update jobneeds
    jn_count = Jobneed.objects.filter(
        job_id__in=job_ids, plandatetime__gt=dtimezone.now()).update(
            cdtz=old_date, mdtz=old_date, plandatetime=old_date, expirydatetime=old_date)

    # Update job
    Job.objects.filter(id=job_id).update(cdtz=F('mdtz'))

    # Log the results
    log.info('Deleted %s jobneedetails and %s jobneeds for job ID %s', jnd_count, jn_count, job_id)


def del_ppm_reminder(jobid):
    log.info('del_ppm_reminder start +')
    Reminder.objects.filter(reminderdate__gt = datetime.now(timezone.utc), job_id = jobid).delete()
    log.info('del_ppm_reminder end -')


def calculate_startdtz_enddtz_for_ppm(job): 
    log.info(f"calculating startdtz, enddtz for job:= [{job['id']}]")
    tz = timezone(timedelta(minutes = int(job['ctzoffset'])))
    ctzoffset = job['ctzoffset']

    current_date = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=tz) + timedelta(minutes=ctzoffset)
    cdtz         = job['cdtz'].replace(microsecond=0, tzinfo=tz) + timedelta(minutes=ctzoffset)
    mdtz         = job['mdtz'].replace(microsecond=0, tzinfo=tz) + timedelta(minutes=ctzoffset)
    vfrom        = job['fromdate'].replace(microsecond=0, tzinfo=tz) + timedelta(minutes=ctzoffset)
    vupto        = job['uptodate'].replace(microsecond=0, tzinfo=tz) + timedelta(minutes=ctzoffset)
    ldtz         = job['lastgeneratedon'].replace(microsecond=0, tzinfo=tz) + timedelta(minutes=ctzoffset)

    if mdtz > cdtz:
        ldtz = current_date
        delete_old_jobs(job['id'], True)
        del_ppm_reminder(job['id'])

    startdtz = max(current_date, vfrom)
    enddtz = vupto
    startdtz = max(startdtz, ldtz)

    if startdtz < current_date:
        ldtz = current_date
    return startdtz, enddtz
    
    
def create_ppm_reminder(jobs):
    try:
        #FOR EVERY JOB
        for job in jobs:
            if job['count'] <= 0:
                continue
            #EXTRACT REMINDER CONFIG (FROM ESCMATRIX)
            esm = EscalationMatrix.objects.select_related('job', 'assignedgroup', 'assignedperson', 'bu').filter(job_id=job['job'])
            #RETRIVE JOBNEEDS
            jobneeds = Jobneed.objects.select_related('job', 'asset', 'qset', 'bu', 'client', 'people', 'pgroup').filter(
                plandatetime__gt=datetime.now(), job_id=job['job'])
            
            if not esm or not jobneeds:
                continue
            
            #FOR EVERY JOBNEED
            for jn in jobneeds:
                log.info(f'create_ppm_reminder() jobneed:{jn.id} plandatetime {jn.plandatetime} jobdesc {jn.jobdesc} buid {jn.bu_id} asset_id {jn.asset_id} qsetid {jn.qset_id}')
                assignto = "GROUP" if jn.pgroup_id != 1 else "PEOPLE"
                #FOR EVERY REMINDER IN REMINDER CONFIG
                for r in esm:
                    log.debug(f"reminder : {pformat(r)}")
                    reminderdate = jn.plandatetime.replace(microsecond=0)

                    if r.frequency == "WEEK":
                        reminderbefore = int(r.frequencyvalue) * 7 * 24 * 60
                    elif r.frequency == "DAY":
                        reminderbefore = int(r.frequencyvalue) * 24 * 60
                    elif r.frequency == "HOUR":
                        reminderbefore = int(r.frequencyvalue) * 60
                    elif r.frequency == "MINUTE":
                        reminderbefore = int(r.frequencyvalue)
                    
                    reminderdate = reminderdate - timedelta(minutes=reminderbefore)
                    #CREATE REMINDER
                    Reminder.objects.create(
                        description    = jn.jobdesc,
                        bu_id          = jn.bu_id,
                        asset_id       = jn.asset_id,
                        qset_id        = jn.qset_id,
                        people_id      = jn.people_id,
                        group_id       = jn.pgroup_id,
                        priority       = jn.priority,
                        reminderin     = r.frequency,
                        reminderbefore = r.frequencyvalue,
                        reminderdate = reminderdate,
                        job_id         = jn.job_id,
                        jobneed_id     = jn.id,
                        plandatetime   = jn.plandatetime,
                        cuser_id       = jn.cuser_id,
                        muser_id       = jn.muser_id,
                        ctzoffset      = jn.ctzoffset,
                        mailids        = r.notify
                    )
    except Exception as e:
        log.critical("something went wrong inside create_ppm_reminder", exc_info=True)


#@shared_task(name="create_ppm_job")
def create_ppm_job(jobid=None):
    F, d = {}, []
    startdtz = enddtz = msg = resp = None
    try:
        with transaction.atomic(using=utils.get_current_db_name()):
            jobs = Job.objects.filter(
                ~Q(jobname='NONE'),
                ~Q(asset__runningstatus = Asset.RunningStatus.SCRAPPED),
                identifier = Job.Identifier.PPM.value,
                parent_id = 1
            ).select_related('asset', 'pgroup', 'cuser', 'muser', 'people', 'qset').values(
                *utils.JobFields.fields
            )
            if jobid:
                jobs = jobs.filter(id = jobid).values(*utils.JobFields.fields)


            if not jobs:
                msg = "No jobs found schedhuling terminated"
                resp = rp.JsonResponse(f"{msg}", status = 404)
                log.warning(f"{msg}", exc_info = True)
            total_jobs = len(jobs)

            if total_jobs > 0 and jobs is not None:
                log.info("processing jobs started found:= '%s' jobs", (len(jobs)))
                for job in jobs:
                    startdtz, enddtz = calculate_startdtz_enddtz_for_ppm(job)
                    log.debug(f"Jobs to be schedhuled from startdatetime {startdtz} to enddatetime {enddtz}")
                    DT, is_cron, resp = get_datetime_list(job['cron'], startdtz, enddtz, resp)
                    log.debug(
                        "Jobneed will going to create for all this datetimes\n %s", (pformat(get_readable_dates(DT))))
                    if not is_cron: F[str(job['id'])] = job['cron']
                    status, resp = insert_into_jn_and_jnd(job, DT, resp)
                    if status:
                        d.append({
                            "job"   : job['id'],
                            "jobname" : job['jobname'],
                            "cron"    : job['cron'],
                            "iscron"  : is_cron,
                            "count"   : len(DT),
                            "status"  : status
                        })
                create_ppm_reminder(d)
                if F:
                    log.info(f"create_ppm_job Failed job schedule list:={pformat(F)}")
                    for key, value in list(F.items()):
                        log.info(f"create_ppm_job job_id: {key} | cron: {value}")
    except Exception as e:
        log.critical("something went wrong create_ppm_job", exc_info=True)
        
                

def send_reminder_email():
    #get all reminders which are not sent
    from django.template.loader import render_to_string
    from django.conf import settings
    from django.core.mail import  EmailMessage

    reminders = Reminder.objects.get_all_due_reminders()
    try:
        for rem in reminders:
            emails = utils.get_email_addresses([rem['people_id'], rem['cuser_id'], rem['muser_id']], [rem['group_id']])
            recipents = list(set(emails + rem['mailids'].split(',')))
            subject = f"Reminder For {rem['job__jobname']}"
            context = {'job':rem['job__jobname'], 'plandatetime':rem['pdate'], 'jobdesc':rem['job__jobdesc'],
                    'creator':rem['cuser__peoplename'],'modifier':rem['muser__peoplename']}
            html_message = render_to_string('reminder_mail.html', context=context)
            log.info(f"Sending reminder mail with subject {subject}")
            msg = EmailMessage()
            msg.subject = subject
            msg.body  = html_message
            msg.from_email = settings.EMAIL_HOST_USER
            msg.to = recipents
            msg.content_subtype = 'html'
            msg.send()
            log.info(f"Reminder mail sent to {recipents} with subject {subject}")
    except Exception as e:
        log.critical("Error while sending reminder email", exc_info=True)