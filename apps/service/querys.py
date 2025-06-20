import graphene
from apps.core import utils
from apps.activity.models.location_model import Location
from apps.onboarding.models import GeofenceMaster, DownTimeHistory,Shift
from apps.peoples.models import Pgbelonging, Pgroup
from apps.attendance.models import PeopleEventlog
from django.db import connections
from collections import namedtuple
from logging import getLogger
from contextlib import closing
from django.utils import timezone
log = getLogger('mobile_service_log')
import json

from .types import (VerifyClientOutput, DowntimeResponse, SelectOutputType)

class Query(graphene.ObjectType):
    
    get_locations = graphene.Field(SelectOutputType,
                                                mdtz = graphene.String(required = True),
                                                ctzoffset = graphene.Int(required = True),
                                                buid = graphene.Int(required = True))


    get_groupsmodifiedafter = graphene.Field(SelectOutputType, 
                                            mdtz = graphene.String(required = True),
                                            ctzoffset = graphene.Int(required = True),
                                            buid = graphene.Int(required = True))



    get_gfs_for_siteids = graphene.Field(SelectOutputType,
                                 siteids = graphene.List(graphene.Int))
    
    
    get_shifts = graphene.Field(SelectOutputType,
        mdtz = graphene.String(required=True),
        buid = graphene.Int(required = True),
        clientid = graphene.Int(required = True))
    

    getsitelist  = graphene.Field(SelectOutputType,
                                 clientid = graphene.Int(required = True),
                                 peopleid = graphene.Int(required = True))


    verifyclient = graphene.Field(VerifyClientOutput, clientcode = graphene.String(required = True))

    get_superadmin_message = graphene.Field(
        DowntimeResponse,
        client_id = graphene.Int(required=True)
    )
    get_site_visited_log = graphene.Field(SelectOutputType,
                                 clientid = graphene.Int(required = True),
                                 peopleid = graphene.Int(required = True),
                                 ctzoffset = graphene.Int(required=True))
    

    
    @staticmethod
    def resolve_get_locations(self, info, mdtz, ctzoffset, buid):
        log.info(f'\n\nrequest for location-modified-after inputs : mdtz:{mdtz}, ctzoffset:{ctzoffset}, clientid:{buid}')
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        data = Location.objects.get_locations_modified_after(mdtzinput, buid, ctzoffset)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)


    @staticmethod
    def resolve_get_groupsmodifiedafter(self, info, mdtz, ctzoffset, buid):
        log.info(f'\n\nrequest for groups-modified-after inputs : mdtz:{mdtz}, ctzoffset:{ctzoffset}, buid:{buid}')
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        data = Pgroup.objects.get_groups_modified_after(mdtzinput, buid)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)


    @staticmethod
    def resolve_get_gfs_for_siteids(self, info, siteids):
        log.info(f'\n\nrequest for getgeofence inputs : siteids:{siteids}')
        data = GeofenceMaster.objects.get_gfs_for_siteids(siteids)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)

    @staticmethod
    def resolve_getsitelist(self, info, clientid, peopleid):
        log.info(f'\n\nrequest for sitelis inputs : clientid:{clientid}, peopleid:{peopleid}')
        data = Pgbelonging.objects.get_assigned_sites_to_people(peopleid, forservice=True)
        #change bupreferences back to json
        for i in range(len(data)):
            data[i]['bupreferences'] = json.dumps(data[i]['bupreferences'])
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)

    @staticmethod
    def resolve_verifyclient(self,info, clientcode):
        try:
            url = utils.get_appropriate_client_url(clientcode)
            if not url: raise ValueError
            return VerifyClientOutput(msg = "VALID", url=url)
        except ValueError as e:
            log.error(f"url not found for the specified {clientcode=}")
            return VerifyClientOutput(msg='INVALID', url=None, rc=1)
        except Exception as ex:
            log.critical("something went wrong!", exc_info=True)
            return VerifyClientOutput(msg='INVALID', url=None, rc=1)

    
    def resolve_get_shifts(self,info,buid,clientid,mdtz):
        log.info(f'request get shifts input are: {buid} {clientid}')
        data = Shift.objects.get_shift_data(buid,clientid,mdtz)
        records, count, msg = utils.get_select_output(data)
        log.info(f'total {count} objects returned')
        return SelectOutputType(nrows = count, records = records,msg = msg)
    
    
    def resolve_get_superadmin_message(self, info, client_id):
        log.info(f'resolve_get_superadmin_message {client_id = }')
        record = DownTimeHistory.objects.filter(client_id=client_id).values('reason', 'starttime', 'endtime').order_by('-cdtz').first()
        if timezone.now() < record['endtime']:
            return DowntimeResponse(
                message=record['reason'],
                startDateTime=record['starttime'],
                endDateTime = record['endtime'])
        else:
            return DowntimeResponse(
                message=""
            )
    def resolve_get_site_visited_log(self, info, clientid, peopleid, ctzoffset):
        log.info(f'resolve_get_sitevisited_log {clientid = } {peopleid = } {ctzoffset = }')
        data = PeopleEventlog.objects.get_sitevisited_log(clientid, peopleid, ctzoffset)
        records, count, msg = utils.get_select_output(data)
        log.info(f'total {count} objects returned')
        return SelectOutputType(nrows = count, records = records,msg = msg)

def get_db_rows(sql, args=None):
    """
    Secure SQL execution function with whitelist validation.
    Only allows execution of pre-approved stored procedures.
    """
    import re
    
    # Whitelist of allowed SQL patterns for stored procedures only
    ALLOWED_SQL_PATTERNS = [
        r'^select \* from fun_getexttourjobneed\(\s*%s\s*,\s*%s\s*,\s*%s\s*\)\s*$',
        r'^select \* from fn_getassetdetails\(\s*%s\s*,\s*%s\s*\)\s*$',
        r'^select \* from fun_getjobneed\(\s*%s\s*,\s*%s\s*,\s*%s\s*\)\s*$',
        r'^select \* from fn_get_schedule_for_adhoc\(\s*%s\s*,\s*%s\s*,\s*%s\s*,\s*%s\s*,\s*%s\s*\)\s*$'
    ]
    
    try:
        # Security validation: Check if SQL matches allowed patterns
        sql_normalized = sql.strip().lower()
        is_allowed = False
        
        for pattern in ALLOWED_SQL_PATTERNS:
            if re.match(pattern, sql_normalized, re.IGNORECASE):
                is_allowed = True
                break
        
        if not is_allowed:
            log.error(f"Security violation: Unauthorized SQL execution attempted: {sql}")
            raise ValueError("SQL execution not allowed: Only approved stored procedures are permitted")
        
        # Security logging: Log all SQL executions for monitoring
        log.info(f"Executing approved SQL: {sql} with args: {args}")
        
        # Define the batch size for fetchmany
        batch_size = 100  # Adjust this based on your needs and memory constraints

        # Using context manager to handle the cursor
        with closing(connections[utils.get_current_db_name()].cursor()) as cursor:
            cursor.execute(sql, args)
            columns = [col[0] for col in cursor.description]
            RowType = namedtuple('Row', columns)

            # Initialize an empty list to collect all rows
            data = []
            while True:
                batch = cursor.fetchmany(batch_size)
                if not batch:
                    break
                data.extend([RowType(*row)._asdict() for row in batch])

        # Convert the list of dictionaries to JSON
        data_json = json.dumps(data, default=str)
        count = len(data)
        log.info(f'{count} objects returned from secure SQL execution')
        return SelectOutputType(records=data_json, msg=f"Total {count} records fetched successfully!", nrows=count)
        
    except ValueError as ve:
        # Security violation - log and raise
        log.error(f"Security violation in get_db_rows: {ve}", exc_info=True)
        raise ve
    except Exception as e:
        log.error("Failed to fetch data", exc_info=True)
        # Optionally re-raise or handle the error appropriately
        raise e


def get_externaltouremodifiedafter(peopleid, siteid, clientid):
    return get_db_rows("select * from fun_getexttourjobneed(%s, %s, %s)", args=[peopleid, siteid, clientid])

def get_assetdetails(mdtz, buid):
    return get_db_rows("select * from fn_getassetdetails(%s, %s)", args=[mdtz, buid])
