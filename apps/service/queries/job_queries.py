import graphene
from apps.activity.models.job_model import Jobneed, JobneedDetails
from apps.service.pydantic_schemas.job_schema import JobneedModifiedAfterSchema, JobneedDetailsModifiedAfterSchema, ExternalTourModifiedAfterSchema
from apps.service.inputs.job_input import JobneedModifiedAfterInput, JobneedDetailsModifiedAfterInput, ExternalTourModifiedAfterInput
from apps.service.types import SelectOutputType
from logging import getLogger
from apps.core import utils
from graphql import GraphQLError
from pydantic import ValidationError

log = getLogger('mobile_service_log')

class JobQueries(graphene.ObjectType):
    get_jobneedmodifiedafter = graphene.Field(
        SelectOutputType,
        filter = JobneedModifiedAfterInput(required=True)
    )

    get_jndmodifiedafter = graphene.Field(
        SelectOutputType,
        filter = JobneedDetailsModifiedAfterInput(required=True)
    )

    get_externaltourmodifiedafter = graphene.Field(
        SelectOutputType,
        filter = ExternalTourModifiedAfterInput(required=True)
    )

    @staticmethod
    def resolve_get_jobneedmodifiedafter(self, info, filter):
        try:
            log.info('request for get_jobneedmodifiedafter')
            validated = JobneedModifiedAfterSchema(**filter)
            data = Jobneed.objects.get_job_needs(people_id = validated.peopleid, bu_id = validated.buid, client_id = validated.clientid)
            records, count, msg = utils.get_select_output(data)
            log.info(f'{count} objects returned...')
            return SelectOutputType(nrows = count,  records = records,msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_jobneedmodifiedafter failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_jobneedmodifiedafter failed: {str(e)}")

    @staticmethod   
    def resolve_get_jndmodifiedafter(self, info, filter):
        try:
            log.info('request for get_jndmodifiedafter')
            validated = JobneedDetailsModifiedAfterSchema(**filter)
            data = JobneedDetails.objects.get_jndmodifiedafter(jobneedid = validated.jobneedids)
            records, count, msg = utils.get_select_output(data)
            log.info(f'{count} objects returned...')
            return SelectOutputType(nrows = count,  records = records,msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_jndmodifiedafter failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_jndmodifiedafter failed: {str(e)}")
        

    @staticmethod
    def resolve_get_externaltourmodifiedafter(self, info, filter):
        try:
            log.info('request for get_externaltourmodifiedafter')
            validated = ExternalTourModifiedAfterSchema(**filter)
            data = Jobneed.objects.get_external_tour_job_needs(people_id = validated.peopleid, bu_id = validated.buid, client_id = validated.clientid)
            records, count, msg = utils.get_select_output(data)
            log.info(f'{count} objects returned...')
            return SelectOutputType(nrows = count,  records = records,msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_externaltourmodifiedafter failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_externaltourmodifiedafter failed: {str(e)}")
        