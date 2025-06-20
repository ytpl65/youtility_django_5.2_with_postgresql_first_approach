
import os
import django
import pytz
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
django.setup()

from django_celery_beat.models import PeriodicTask

def utc_to_ist(utc_dt):
    """
    Convert a timezone-aware UTC datetime object to IST (UTC+5:30).
    
    Args:
        utc_dt (datetime): A timezone-aware datetime object in UTC

    Returns:
        datetime: The converted datetime object in IST
    """
    if utc_dt is None:
        return "NA"
    if utc_dt.tzinfo is None:
        # Ensure the input datetime is timezone-aware in UTC
        utc_dt = pytz.UTC.localize(utc_dt)
    
    ist = pytz.timezone('Asia/Kolkata')
    ist_dt = utc_dt.astimezone(ist)
    return ist_dt



task_runtime_in_utc = PeriodicTask.objects.get(name="send_report_genererated_on_mail").last_run_at
task_runtime_in_ist = utc_to_ist(task_runtime_in_utc)
print("send_report_genererated_on_mail last run on:",task_runtime_in_ist)

task2_runtime_in_utc = PeriodicTask.objects.get(name="create-reports-scheduled").last_run_at
task2_runtime_in_ist = utc_to_ist(task2_runtime_in_utc)
print("create-reports-scheduled last run on       :",task_runtime_in_ist)

task3_runtime_in_utc = PeriodicTask.objects.get(name="ppm_schedule_at_minute_3_past_hour_3_and_16").last_run_at
task3_runtime_in_ist = utc_to_ist(task3_runtime_in_utc)
print("create_ppm_job last run on                 :",task3_runtime_in_ist)

task4_runtime_in_utc = PeriodicTask.objects.get(name="reminder_emails_at_minute_10_past_every_8th_hour.").last_run_at
task4_runtime_in_ist = utc_to_ist(task4_runtime_in_utc)
print("send_reminder_email last run on            :",task4_runtime_in_ist)

task5_runtime_in_utc = PeriodicTask.objects.get(name="auto_close_at_every_30_minute").last_run_at
task5_runtime_in_ist = utc_to_ist(task5_runtime_in_utc)
print("auto_close_jobs last run on                :",task5_runtime_in_ist)

task6_runtime_in_utc = PeriodicTask.objects.get(name="ticket_escalation_every_30min").last_run_at
task6_runtime_in_ist = utc_to_ist(task6_runtime_in_utc)
print("ticket_escalation last run on              :",task6_runtime_in_ist)

task7_runtime_in_utc = PeriodicTask.objects.get(name="create_job_at_minute_27_past_every_8th_hour.").last_run_at
task7_runtime_in_ist = utc_to_ist(task7_runtime_in_utc)
print("create_job last run on                     :",task7_runtime_in_ist)

task8_runtime_in_utc = PeriodicTask.objects.get(name="move_media_to_cloud_storage").last_run_at
task8_runtime_in_ist = utc_to_ist(task8_runtime_in_utc)
print("move_media_to_cloud_storage last run on    :",task8_runtime_in_ist)



