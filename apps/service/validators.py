from logging import getLogger
from croniter import croniter, CroniterBadCronError
from django.core.exceptions import ValidationError

import re
log = getLogger("mobile_service_log")
def checkHex(s):
    return not any(((ch < '0' or ch > '9') and (ch < 'A' or ch > 'F')) for ch in s)

def clean_point_field(val):

    from django.contrib.gis.geos import GEOSGeometry
    if not val or val in ['None', 'NONE']: return None
    if checkHex(val): return GEOSGeometry(val)
    if 'SRID' not in val:
        lat, lng = val.split(',')
        return GEOSGeometry(f'SRID=4326;POINT({lng} {lat})')
    return GEOSGeometry(val)

def clean_code(val):
    if val:
        val = str(val)
        return val.upper()

def clean_text(val):
    if val:
        val = str(val)
        return val         

def clean_datetimes(val, offset):
    from datetime import datetime, timedelta, timezone
    
    if val:
        log.info(f"beforing cleaning {val}")
        if val in ['None', 'NONE', ""]:
            return None
        val = val.replace("+00:00", "")
        val = datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
        val =  val.replace(tzinfo = timezone.utc, microsecond = 0)
        log.info(f'after cleaning {val}')
    return val

def clean_date(val):
    from datetime import datetime
    return datetime.strptime(val,  "%Y-%m-%d")


def clean_record(record):
    """
    Cleans the record like code, 
    desc, gps fields, datetime fields etc
    """
    for k, v in record.items():
        if k in ['jobdesc', 'remarks']:
            record[k] = clean_text(v)
        elif k in ['gpslocation' , 'startlocation', 'endlocation']:
            record[k] = clean_point_field(v)
        elif k in ['cdtz', 'mdtz', 'starttime', 'endtime', 'punchintime',
                   'punchouttime', 'plandatetime', 'expirydatetime']:
            record[k] = clean_datetimes(v, record['ctzoffset'])
        elif k in ['geofencecode']:
            record[k] = clean_code(v)
        elif k in ['approvers', 'categories', 'transportmodes', 'approverfor', 'sites']:
            record[k] = clean_array_string(v, service=True)
        elif k in ['answer']:
            record[k] = v.replace('["', "").replace('"]',"")
    return record


def clean_string(input_string, code=False):
    if not input_string: return
    cleaned_string = ' '.join(input_string.split())
    if code:
        cleaned_string = cleaned_string.replace(' ', '_').upper()
    return cleaned_string

def validate_email(email):
    if email:
        email = email.strip()  # Remove any leading or trailing whitespace
        # Regular expression for validating an Email
        regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        # Using re.fullmatch to validate an Email
        return bool(re.fullmatch(regex, email))
    return False
    
def clean_array_string(string, service=False):
    if string:
        string = string.replace(' ', '')
        return string.split(',')
    return []

def validate_cron(cron):
    try:
        croniter(cron)
        if cron.startswith("*"):
                raise ValidationError(f"Warning: Scheduling every minute is not allowed!")
        return True
    except ValueError:
        return False