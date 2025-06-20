import graphene
from apps.onboarding.models import TypeAssist
from apps.core.utils import get_type_data
from apps.service.types import SelectOutputType
from apps.core import utils
from logging import getLogger
from apps.service.inputs.typeassist_input import TypeAssistModifiedFilterInput
from pydantic import ValidationError
from apps.service.pydantic_schemas.typeassist_schema import TypeAssistModifiedFilterSchema
from graphql import GraphQLError

log = getLogger("mobile_service_log")

class TypeAssistQueries(graphene.ObjectType):
    get_typeassistmodifiedafter = graphene.Field(
        SelectOutputType,
        filter = TypeAssistModifiedFilterInput(required = True)
    )

    @staticmethod
    def resolve_get_typeassistmodifiedafter(self, info, filter):
        try:
            log.info("request for get_typeassistmodifiedafter")
            validated = TypeAssistModifiedFilterSchema(**filter)
            mdtzinput = utils.getawaredatetime(dt=validated.mdtz, offset=validated.ctzoffset)
            data = TypeAssist.objects.get_typeassist_modified_after(
                mdtz = mdtzinput, clientid = validated.clientid
            )
            records, count, msg = utils.get_select_output(data)
            log.info(f"{count} objects returned...")
            return SelectOutputType(nrows = count, records = records, msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info = True)
            raise GraphQLError(f"get_typeassistmodifiedafter failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info = True)
            raise GraphQLError(f"get_typeassistmodifiedafter failed: {str(e)}") 
        