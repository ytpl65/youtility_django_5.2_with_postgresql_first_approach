import graphene
from apps.onboarding.models import GeofenceMaster,Shift,DownTimeHistory
from apps.activity.models.location_model import Location
from apps.peoples.models import Pgbelonging, Pgroup, People
from apps.attendance.models import PeopleEventlog
from graphql.error import GraphQLError
from apps.service.pydantic_schemas.bt_schema import LocationSchema, GeofenceSchema, ShiftSchema, GroupsModifiedAfterSchema, SiteListSchema, SendEmailVerificationLinkSchema, SuperAdminMessageSchema, SiteVisitedLogSchema, VerifyClientSchema
from apps.service.types import SelectOutputType,VerifyClientOutput,BasicOutput
from apps.service.inputs.bt_input import LocationFilterInput, GeofenceFilterInput, ShiftFilterInput, VerifyClientInput,GroupsModifiedAfterFilterInput, SiteListFilterInput, SendEmailVerificationLinkFilterInput, SuperAdminMessageFilterInput, SiteVisitedLogFilterInput
from logging import getLogger
from apps.core import utils
from django.utils import timezone
from apps.service.types import DowntimeResponse
import json
from pydantic import ValidationError


log = getLogger("mobile_service_log")

class BtQueries(graphene.ObjectType):
    get_locations = graphene.Field(
        SelectOutputType,
        filter = LocationFilterInput(required=True)
    )

    get_groupsmodifiedafter = graphene.Field(
        SelectOutputType,
        filter = GroupsModifiedAfterFilterInput(required=True)
    )

    get_gfs_for_siteids = graphene.Field(
        SelectOutputType,
        filter = GeofenceFilterInput(required=True)
    )

    get_shifts = graphene.Field(
        SelectOutputType,
        filter = ShiftFilterInput(required=True)
    )

    getsitelist  = graphene.Field(
        SelectOutputType,
        filter = SiteListFilterInput(required=True)
    )
    send_email_verification_link = graphene.Field(
        BasicOutput,
        filter = SendEmailVerificationLinkFilterInput(required=True)
    )
    get_superadmin_message = graphene.Field(
        SelectOutputType,
        filter = SuperAdminMessageFilterInput(required=True)
    )
    get_site_visited_log = graphene.Field(
        SelectOutputType,
        filter = SiteVisitedLogFilterInput(required=True)
    )

    verifyclient = graphene.Field(
        VerifyClientOutput,
        filter = VerifyClientInput(required=True)
    )
    
    @staticmethod
    def resolve_verifyclient(self, info, filter):
        try:
            log.info('request for verifyclient')
            validated = VerifyClientSchema(**filter)
            url = utils.get_appropriate_client_url(validated.clientcode)
            if not url: raise ValueError
            return VerifyClientOutput(msg = "VALID", url=url)
        except ValueError as e:
            log.error(f"url not found for the specified {validated.clientcode=}")
            return VerifyClientOutput(msg='INVALID', url=None, rc=1)
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"verifyclient failed: {str(ve)}")
        except Exception as ex:
            log.critical("something went wrong!", exc_info=True)
            return VerifyClientOutput(msg='INVALID', url=None, rc=1)

    @staticmethod
    def resolve_get_locations(self, info, filter):
        try:
            log.info('request for get_locations')
            validated = LocationSchema(**filter)
            mdtzinput = utils.getawaredatetime(dt=validated.mdtz, offset=validated.ctzoffset)
            data = Location.objects.get_locations_modified_after(mdtzinput, validated.buid, validated.ctzoffset)
            records, count, msg = utils.get_select_output(data)
            log.info(f'{count} objects returned...')
            return SelectOutputType(nrows = count,  records = records,msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_locations failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_locations failed: {str(e)}")
        

    @staticmethod
    def resolve_get_groupsmodifiedafter(self, info, filter):
        try:
            log.info('request for get_groupsmodifiedafter')
            validated = GroupsModifiedAfterSchema(**filter)
            mdtzinput = utils.getawaredatetime(dt=validated.mdtz, offset=validated.ctzoffset)
            data = Pgroup.objects.get_groups_modified_after(mdtzinput, validated.buid)
            records, count, msg = utils.get_select_output(data)
            log.info(f'{count} objects returned...')
            return SelectOutputType(nrows = count,  records = records,msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_groupsmodifiedafter failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_groupsmodifiedafter failed: {str(e)}")
        
    @staticmethod
    def resolve_get_gfs_for_siteids(self, info, filter):
        try:
            log.info('request for get_gfs_for_siteids')
            validated = GeofenceSchema(**filter)
            data = GeofenceMaster.objects.get_gfs_for_siteids(validated.siteids)
            records, count, msg = utils.get_select_output(data)
            log.info(f'{count} objects returned...')
            return SelectOutputType(nrows = count,  records = records,msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_gfs_for_siteids failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_gfs_for_siteids failed: {str(e)}")
        
    @staticmethod
    def resolve_get_shifts(self, info, filter):
        try:
            log.info('request for get_shifts')
            validated = ShiftSchema(**filter)
            data = Shift.objects.get_shift_data(validated.buid,validated.clientid,validated.mdtz)
            records, count, msg = utils.get_select_output(data)
            log.info(f'{count} objects returned...')
            return SelectOutputType(nrows = count,  records = records,msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_shifts failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_shifts failed: {str(e)}")
        
    @staticmethod
    def resolve_getsitelist(self, info, filter):
        try:
            log.info('request for getsitelist')
            validated = SiteListSchema(**filter)
            data = Pgbelonging.objects.get_assigned_sites_to_people(validated.peopleid, forservice=True)
            for i in range(len(data)):
                data[i]['bupreferences'] = json.dumps(data[i]['bupreferences'])
            records, count, msg = utils.get_select_output(data)
            log.info(f'{count} objects returned...')
            return SelectOutputType(nrows = count, records = records,msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"getsitelist failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"getsitelist failed: {str(e)}")
        
    @staticmethod
    def resolve_send_email_verification_link(self, info, filter):
        try:
            log.info('request for send_email_verification_link')
            from django_email_verification import send_email
            validated = SendEmailVerificationLinkSchema(**filter)
            user = People.objects.filter(loginid = validated.loginid, client__bucode = validated.clientcode).first()
            if user:
                send_email(user, info.context)
                rc, msg = 0, "Success"
            else:
                rc, msg = 1, "Failed"
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"send_email_verification_link failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"send_email_verification_link failed: {str(e)}")
        return BasicOutput(rc=rc, msg=msg, email = user.email)
        
    @staticmethod
    def resolve_get_superadmin_message(self, info, filter):
        try:
            log.info('request for get_superadmin_message')
            validated = SuperAdminMessageSchema(**filter)
            record = DownTimeHistory.objects.filter(client_id=validated.client_id).values('reason', 'starttime', 'endtime').order_by('-cdtz').first()
            if timezone.now() < record['endtime']:
                return DowntimeResponse(
                    message=record['reason'],
                    startDateTime=record['starttime'],
                    endDateTime = record['endtime'])
            else:
                return DowntimeResponse(
                    message=""
                )
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_superadmin_message failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_superadmin_message failed: {str(e)}")
        
    @staticmethod
    def resolve_get_site_visited_log(self, info, filter):
        try:
            log.info('request for get_site_visited_log')
            validated = SiteVisitedLogSchema(**filter)
            data = PeopleEventlog.objects.get_sitevisited_log(validated.clientid, validated.peopleid, validated.ctzoffset)
            records, count, msg = utils.get_select_output(data)
            log.info(f'{count} objects returned...')
            return SelectOutputType(nrows = count,  records = records,msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_site_visited_log failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_site_visited_log failed: {str(e)}")
