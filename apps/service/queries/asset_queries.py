import graphene
from apps.core import utils
from apps.activity.models.asset_model import Asset
from apps.service.types import SelectOutputType
from apps.service.inputs.asset_input import AssetFilterInput
from graphql.error import GraphQLError
from logging import getLogger
from apps.service.querys import get_db_rows
from apps.service.pydantic_schemas.asset_schema import AssetFilterSchema
from pydantic import ValidationError

log = getLogger('mobile_service_log')


class AssetQueries(graphene.ObjectType):
    """Query to fetch asset details based on modification timestamp and business unit."""
    get_assetdetails = graphene.Field(
        SelectOutputType,
        filter = AssetFilterInput(required=True),
        description="Query to fetch asset details based on modification timestamp and business unit."
    )                              

    @staticmethod
    def resolve_get_assetdetails(self, info, filter):
        try:
            log.info('request for get_assetdetails')
            validated = AssetFilterSchema(**filter)
            mdtzinput = utils.getawaredatetime(dt=validated.mdtz, offset=validated.ctzoffset)
            return get_db_rows("select * from fn_getassetdetails(%s, %s)", args=[mdtzinput, validated.buid])
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_assetdetails failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_assetdetails failed: {str(e)}")
        