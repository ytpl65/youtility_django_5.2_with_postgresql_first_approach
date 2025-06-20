'''
This file contains functions related to executing
reports in background
'''
from apps.reports.utils import ReportEssentials
from apps.reports.models import ScheduleReport
from apps.core.utils import runrawsql
from django.conf import settings
from croniter import croniter
from datetime import datetime , timedelta, timezone
from django.utils import timezone as dtimezone
from django.core.mail import EmailMessage
from logging import getLogger
from pprint import pformat
import json
import traceback as tb
import os
from io import BytesIO


# make it false when u deploy
MOCK=False
now = datetime.now() if not MOCK else datetime(2023,8,19,12,2,0)
now_insql = 'CURRENT_TIMESTAMP' if not MOCK else "'2023-08-19 12:02:00.419091+00'::timestamp"

log = getLogger('reports')
DATETIME_FORMAT = '%d-%b-%Y %H-%M-%S'
DATE_FORMAT = '%d-%b-%Y'
TIME_FORMAT = "%H-%M-%S"



def set_state(state_map, reset=False, set=""):
    if reset:
        for k in state_map:
            state_map[k] = 0
    if set:
        state_map[set] += 1
    return state_map
        
            


# def get_scheduled_reports_fromdb():
#     query =f"""
#         SELECT *
#         FROM schedule_report
#         WHERE enable = TRUE AND
#         (
#             fromdatetime is NULL and uptodatetime is NULL
#             OR
#             (
#                 CASE crontype
#                     WHEN 'daily' THEN lastgeneratedon <= {now_insql} - INTERVAL '1 day'
#                     WHEN 'weekly' THEN lastgeneratedon <= {now_insql} - INTERVAL '1 week'
#                     WHEN 'monthly' THEN lastgeneratedon <= {now_insql} - INTERVAL '1 month'
#                     WHEN 'workingdays' THEN lastgeneratedon <= {now_insql} - INTERVAL '7 days'
#                     WHEN 'workingdays' THEN lastgeneratedon <= {now_insql} - INTERVAL '8 days'
#                 END
#             )
#             AND (fromdatetime <= {now_insql} OR fromdatetime is NULL)
#             AND (uptodatetime <= {now_insql} OR uptodatetime is NULL)
#         )
#     """
#     return runrawsql(query)


def get_scheduled_reports_fromdb():
    now_insql = "NOW()"  # or use a parameter if safer
    query = f"""
        SELECT *
        FROM schedule_report
        WHERE enable = TRUE
        AND (
            (fromdatetime IS NULL AND uptodatetime IS NULL)
            OR (
                (
                    (crontype = 'daily' AND lastgeneratedon <= {now_insql} - INTERVAL '1 day')
                    OR (crontype = 'weekly' AND lastgeneratedon <= {now_insql} - INTERVAL '1 week')
                    OR (crontype = 'monthly' AND lastgeneratedon <= {now_insql} - INTERVAL '1 month')
                    OR (crontype = 'workingdays' AND lastgeneratedon <= {now_insql} - INTERVAL '7 days')
                )
                AND (fromdatetime <= {now_insql} OR fromdatetime IS NULL)
                AND (uptodatetime >= {now_insql} OR uptodatetime IS NULL)
            )
        )
    """
    return runrawsql(query)


def remove_star(li):
    return [item.replace('*', "") for item in li]


def update_record(data, fromdatetime, uptodatetime, lastgeneratedon):
    ScheduleReport.objects.filter(
        pk = data['id']
    ).update(
        fromdatetime=fromdatetime,
        uptodatetime=uptodatetime,
        lastgeneratedon=lastgeneratedon
    )


def get_report_dates_with_working_days(today_date, working_days, cron):
    # Validate working_days input
    if working_days not in [5, 6]:
        raise ValueError("Working days must be either 5 (Mon-Fri) or 6 (Mon-Sat).")
    
    hr, min = cron.split(" ")[:2]

    # Calculate the most recent Monday (or today if it's Monday)
    monday = today_date - timedelta(days=today_date.weekday())

    # Calculate the end of the work week based on working days
    end_of_week_day = 4 if working_days == 5 else 5  # Friday for 5-day week, Saturday for 6-day week
    end_of_week = monday + timedelta(days=end_of_week_day)

    # Format dates with time
    fromdatetime = monday.replace(microsecond=0)
    uptodatetime = end_of_week.replace(microsecond=0)
    return fromdatetime, uptodatetime



def calculate_from_and_upto(data):
    log.info(f"Calculating from and upto dates for data: {data}")
    from datetime import datetime , timedelta, timezone
    days_crontype_map = {'weekly':7, 'monthly':31, 'daily':1, 'workingdays':data['workingdays']}
    tz = timezone(timedelta(minutes = data['ctzoffset']))
    log.info("The report is generating for the first time")
    if data['crontype'] != 'workingdays':
        basedatetime = now - timedelta(days=days_crontype_map[data['crontype']]+1)
        log.info(f'{basedatetime = } {data["cron"] = }')
        cron = croniter(data['cron'], basedatetime)
        fromdatetime = cron.get_prev(datetime)
        log.info(f'{fromdatetime = } {type(fromdatetime)}')
        fromdatetime = fromdatetime.replace(tzinfo=tz, microsecond=0)
        uptodatetime = cron.get_next(datetime)
        uptodatetime = uptodatetime.replace(tzinfo=tz, microsecond=0)
        lastgeneratedon = now
        return fromdatetime, uptodatetime, lastgeneratedon
    else:
        fromdatetime, uptodatetime = get_report_dates_with_working_days(
            now, int(data['workingdays']), data['cron'])
        log.info(f"{fromdatetime = } {uptodatetime = } {now = }")
        if now > uptodatetime:
            return fromdatetime, uptodatetime, now
        log.info(f"The uptodatetime: {uptodatetime} is greater than current datetime {now}")
        # skipped by returning none, because dates are not yet in range,
        return None, None, None
            



def build_form_data(data, report_params, behaviour):
    date_range = None
    fields = remove_star(behaviour['fields'])
    fromdatetime, uptodatetime, lastgeneratedon = calculate_from_and_upto(data)
    if fromdatetime and uptodatetime and lastgeneratedon:
        formdata = {
            'preview':False,
            'format':report_params['format'],
            'ctzoffset':data['ctzoffset'],
        }
        if 'fromdate' in fields:
            formdata.update({'fromdate':fromdatetime.date(), 'uptodate':uptodatetime.date()})
            date_range = f"{formdata['fromdate'].strftime(DATE_FORMAT)}--{formdata['uptodate'].strftime(DATE_FORMAT)}"
        if 'fromdatetime' in fields:
            formdata.update({'fromdatetime':fromdatetime, 'uptodatetime':uptodatetime.date()})
            date_range = f"{formdata['fromdatetime'].strftime(DATETIME_FORMAT)}--{formdata['uptodatetime'].strftime(DATETIME_FORMAT)}"
        log.debug(f'formdata = {pformat(formdata)}, fields = {fields}')
        required_params = {key: report_params[key] for key in fields if key not in formdata}
        formdata.update(required_params)
        updatevalues = {'fromdatetime':fromdatetime, 'uptodatetime':uptodatetime, 'lastgeneratedon':lastgeneratedon}
        return formdata, date_range, updatevalues
    return None, None, None
    
    
def generate_filename(report_type, date_range, sendtime):
    #eg: filename = TaskSummary__2023-DEC-1--2023-DEC-30__23-34-23.pdf
    return f"{report_type}__{date_range}__{sendtime.strftime(TIME_FORMAT)}"
    


def execute_report(RE, report_type, client_id, formdata):
    report_export = RE(
            filename=report_type,
            client_id=client_id,
            returnfile=True,
            formdata=formdata)
    return report_export.execute()


def save_report_to_tmp_folder(filename, ext, report_output, dir=None):
    if report_output:
        directory = dir or settings.TEMP_REPORTS_GENERATED
        filepath = os.path.join(directory, f"{filename}.{ext}")

        if not os.path.exists(directory):
            os.makedirs(directory)

        mode = 'wb' if ext in ['pdf', 'xlsx'] else 'w'
        try:
            with open(filepath, mode) as f:
                if isinstance(report_output, BytesIO):
                    report_output = report_output.getvalue()
                    if ext in ['csv', 'json', 'html'] and report_output:
                        report_output = report_output.decode('utf-8')
                if report_output:  # Check if report_output is not empty
                    f.write(report_output)
                else:
                    log.error(f"No data to write for {filename}.{ext}")
                    return None  # Return None to indicate no file was saved
        except Exception as e:
            log.error(f"Error while saving file {filename}.{ext}: {e}")
            return None  # Return None on error
    else:
        log.error("No report output provided")
        return None

    return filepath








# def save_report_to_tmp_folder(filename, ext, report_output, dir=None):
#     log.info(" Report Output: %s",report_output)
#     if report_output:
#         directory = dir or settings.TEMP_REPORTS_GENERATED
#         filepath = os.path.join(directory, f"{filename}.{ext}")

#         log.info("File Path: %s",filepath)
#         if not os.path.exists(directory):
#             os.makedirs(directory)
#         log.info("Report Output: %s %s",report_output, type(report_output))
#         mode = 'wb' if ext in ['pdf', 'xlsx'] else 'w'
#         try:
#             with open(filepath, mode) as f:
                
#                 if isinstance(report_output, BytesIO):
#                     log.info("Here I am in bytes")
#                     report_output = report_output.getvalue()
#                     if ext in ['csv', 'json', 'html'] and report_output:
#                         report_output = report_output.decode('utf-8')
#                 if report_output:  # Check if report_output is not empty
#                     with open(report_output, 'r' if mode == 'w' else 'rb') as source_file:
#                         file_content = source_file.read()
#                         f.write(file_content)
#                 else:
#                     log.error(f"No data to write for {filename}.{ext}")
#                     return None  # Return None to indicate no file was saved
#         except Exception as e:
#             log.error(f"Error while saving file {filename}.{ext}: {e}")
#             return None  # Return None on error
#     else:
#         log.error("No report output provided")
#         return None

#     return filepath


def update_report_record(record, updatevalues, filename):
    isupdated = ScheduleReport.objects.filter(id=record['id']).update(
        filename=filename, **updatevalues)
    return isupdated

def generate_scheduled_report(record, state_map):
    """
    Generate a scheduled report based on the provided data.

    Args:
        data (dict): A dictionary containing information about the scheduled report.

    Returns:
        None: This method generates and saves the report but does not return any value.

    Raises:
        Any relevant exceptions: Document any exceptions that may be raised during report generation.
    """
    resp = dict()
    if record:
        report_params = json.loads(record['report_params'])
        re = ReportEssentials(record['report_type'])
        behaviour = re.behaviour_json
        RE = re.get_report_export_object()
        log.info(f"Got RE of type {type(RE)}")
        formdata, date_range, updatevalues = build_form_data(record, report_params, behaviour)
        if formdata and date_range and updatevalues:
            log.info(f"formdata: {pformat(formdata)} {date_range = }")
            report_output = execute_report(RE, record['report_type'], record['client_id'], formdata)
            sendtime = record['report_sendtime']
            report_type = record['report_type']
            filename = generate_filename(report_type, date_range, sendtime)
            log.info(f"filename generated {filename = }")
            ext = report_params['format']
            log.info(f"file extension {ext = }")
            filepath = save_report_to_tmp_folder(filename, ext, report_output)
            if report_output and filepath:
                if isupdated := update_report_record(record, updatevalues, filename):
                    log.info(f"Reoprt Record updated successfully")
                log.info(f"file saved at location {filepath =}")
                resp[str(record['id'])] = filepath
                set_state(state_map, set="generated")
            else:
                set_state(state_map, set="not_generated")
        else:
            set_state(state_map, set="skipped")
            resp['msg'] = "Report cannot be generated due to out of range"
    else:
        resp['msg'] = 'No reports are currently due for being generated'
    return state_map


def walk_directory(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            yield os.path.join(root, file)


def get_report_record(filename_without_extension):
    return ScheduleReport.objects.filter(filename=filename_without_extension).first()


def send_email(record, file):
    log.info(f"Sending email to {record.to_addr} with file {os.path.basename(file)}")
    email = EmailMessage(
        "Test Subject",
        'Test Body',
        settings.EMAIL_HOST_USER,
        [record.to_addr]
    )
    email.attach_file(file)
    email.send()
    log.info(f"Email sent to {record.to_addr} with file {os.path.basename(file)}")


def handle_error(e):
    return {
        'time': dtimezone.now(),
        'error': str(e),
        'traceback': tb.format_exc(),
    }
import pytz
from django.utils import timezone


def check_time_of_report(filename):
    log.info('Checking time of report for file: %s', filename)

    filename_with_extension = os.path.basename(filename)
    filename_without_extension, _ = os.path.splitext(filename_with_extension)
    parts = filename_without_extension.split("__")

    try:
        sendtime_str = parts[-1]  # e.g., '17:35'
        ist_zone = pytz.timezone("Asia/Kolkata")

        # Parse IST time and convert to UTC
        ist_time = datetime.strptime(sendtime_str, TIME_FORMAT).time()
        today = timezone.now().date()

        ist_datetime = datetime.combine(today, ist_time)
        ist_aware = ist_zone.localize(ist_datetime)
        utc_send_time = ist_aware.astimezone(pytz.UTC)

        # Current UTC time
        now_utc = timezone.now()
        time_diff = abs(now_utc - utc_send_time)

        log.info(f"Now UTC: {now_utc}, Scheduled UTC: {utc_send_time}, Diff: {time_diff}")

        if time_diff <= timedelta(minutes=30):
            return True, filename_without_extension

    except Exception as e:
        log.warning(f"Time parse error for file {filename}: {e}")

    return False, None


# def check_time_of_report(filename):
#    log.info('Checking time of report for file: %s', filename)

#    filename_with_extension = os.path.basename(filename)
#    filename_without_extension, _ = os.path.splitext(filename_with_extension)
#    parts = filename_without_extension.split("__")
#    sendtime_str = parts[-1]
#    dt = datetime.strptime(sendtime_str, TIME_FORMAT)
#    T1 = dt.time()
#    current_time = timezone.localtime(timezone.now()).time()


#    # Convert datetime.time to datetime.datetime
#    today = datetime.today().date()
#    T1_datetime = datetime.combine(today, T1)
#    current_time_datetime = datetime.combine(today, current_time)

#    # Subtract datetime.datetime objects to get a timedelta
#    time_difference = current_time_datetime - T1_datetime
#    log.info('Time difference between current time and report time: %s', time_difference)

#    if abs(time_difference) <= timedelta(minutes=30):
#        log.info('Time difference is less than or equal to 30 minutes. Returning True for file: %s', filename_without_extension)
#        return True, filename_without_extension

#    log.info('Time difference is more than 30 minutes. Returning False for file: %s', filename)
#    return False, None

def remove_reportfile(file, story=None):
    try:
        os.remove(file)
        log.info(f"Successfully deleted file: {os.path.basename(file)}")
    except Exception as e:
        log.critical(f"Error deleting file {os.path.basename(file)}: {e}")
        if story:
            story['errors'].append(str(e))
            return story
