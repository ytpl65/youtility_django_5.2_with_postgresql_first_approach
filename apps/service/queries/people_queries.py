import graphene
from apps.peoples.models import People, Pgbelonging, Pgroup
from apps.attendance.models import PeopleEventlog
from apps.activity.models.attachment_model import Attachment
from apps.service.pydantic_schemas.people_schema import PeopleModifiedAfterSchema, PeopleEventLogPunchInsSchema, PgbelongingModifiedAfterSchema, PeopleEventLogHistorySchema, AttachmentSchema
from graphql import GraphQLError
from apps.service.inputs.people_input import PeopleModifiedAfterFilterInput, PeopleEventLogPunchInsFilterInput, PgbelongingModifiedAfterFilterInput, PeopleEventLogHistoryFilterInput, AttachmentFilterInput
from apps.service.types import SelectOutputType
from apps.core import utils
from logging import getLogger
from pydantic import ValidationError

log = getLogger("mobile_service_log")

class PeopleQueries(graphene.ObjectType):
    get_peoplemodifiedafter = graphene.Field(
        SelectOutputType,
        filter = graphene.Argument(PeopleModifiedAfterFilterInput, required = True))

    get_people_event_log_punch_ins = graphene.Field(
        SelectOutputType,
        filter = graphene.Argument(PeopleEventLogPunchInsFilterInput, required = True))

    get_pgbelongingmodifiedafter = graphene.Field(
        SelectOutputType,
        filter = graphene.Argument(PgbelongingModifiedAfterFilterInput, required = True))

    get_peopleeventlog_history = graphene.Field(
        SelectOutputType,
        filter = graphene.Argument(PeopleEventLogHistoryFilterInput, required = True))

    get_attachments = graphene.Field(
        SelectOutputType,
        filter = graphene.Argument(AttachmentFilterInput, required = True))

    @staticmethod
    def resolve_get_peoplemodifiedafter(self, info, filter):
        try:
            log.info("request for get_peoplemodifiedafter")
            validated = PeopleModifiedAfterSchema(**filter)
            mdtzinput = utils.getawaredatetime(dt=validated.mdtz, offset=validated.ctzoffset)
            data = People.objects.get_people_modified_after(mdtz = mdtzinput, siteid = validated.buid)
            records, count, msg = utils.get_select_output(data)
            log.info(f"{count} objects returned...")
            return SelectOutputType(nrows = count, records = records, msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info = True)
            raise GraphQLError(f"get_peoplemodifiedafter failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info = True)
            raise GraphQLError(f"get_peoplemodifiedafter failed: {str(e)}")
        
    @staticmethod
    def resolve_get_people_event_log_punch_ins(self, info, filter):
        try:
            log.info("request for get_people_event_log_punch_ins")
            validated = PeopleEventLogPunchInsSchema(**filter)
            data = PeopleEventlog.objects.get_people_event_log_punch_ins(datefor = validated.datefor, buid = validated.buid, peopleid = validated.peopleid)
            records, count, msg = utils.get_select_output(data)
            log.info(f"{count} objects returned...")
            return SelectOutputType(nrows = count, records = records, msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info = True)
            raise GraphQLError(f"get_people_event_log_punch_ins failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info = True)
            raise GraphQLError(f"get_people_event_log_punch_ins failed: {str(e)}")
        
    @staticmethod
    def resolve_get_pgbelongingmodifiedafter(self, info, filter):
        try:
            log.info("request for get_pgbelongingmodifiedafter")
            validated = PgbelongingModifiedAfterSchema(**filter)
            mdtzinput = utils.getawaredatetime(dt=validated.mdtz, offset=validated.ctzoffset)
            data = Pgbelonging.objects.get_modified_after(mdtz = mdtzinput, peopleid = validated.peopleid, buid = validated.buid)
            records, count, msg = utils.get_select_output(data)
            log.info(f"{count} objects returned...")
            return SelectOutputType(nrows = count, records = records, msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info = True)
            raise GraphQLError(f"get_pgbelongingmodifiedafter failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info = True)
            raise GraphQLError(f"get_pgbelongingmodifiedafter failed: {str(e)}")
        
    @staticmethod
    def resolve_get_peopleeventlog_history(self, info, filter):
        try:
            log.info("request for get_peopleeventlog_history")
            validated = PeopleEventLogHistorySchema(**filter)
            mdtzinput = utils.getawaredatetime(dt=validated.mdtz, offset=validated.ctzoffset)
            data = PeopleEventlog.objects.get_peopleeventlog_history(mdtz = mdtzinput, people_id = validated.peopleid, bu_id = validated.buid, client_id = validated.clientid, ctzoffset = validated.ctzoffset, peventtypeid = validated.peventtypeid)
            records, count, msg = utils.get_select_output(data)
            log.info(f"{count} objects returned...")
            return SelectOutputType(nrows = count, records = records, msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info = True)
            raise GraphQLError(f"get_peopleeventlog_history failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info = True)
            raise GraphQLError(f"get_peopleeventlog_history failed: {str(e)}")
        
    @staticmethod
    def resolve_get_attachments(self, info, filter):
        try:
            log.info("request for get_attachments")
            validated = AttachmentSchema(**filter)
            data = Attachment.objects.get_attachements_for_mob(ownerid = validated.owner)
            records, count, msg = utils.get_select_output(data)
            log.info(f"{count} objects returned...")
            return SelectOutputType(nrows = count, records = records, msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info = True)
            raise GraphQLError(f"get_attachments failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info = True)
            raise GraphQLError(f"get_attachments failed: {str(e)}")