import graphene
from apps.y_helpdesk.models import Ticket
from apps.core import utils
from graphql import GraphQLError
from apps.service.inputs.ticket_input import TicketFilterInput
from pydantic import ValidationError
from apps.service.pydantic_schemas.ticket_schema import TicketSchema
from logging import getLogger
from apps.service.types import SelectOutputType

log = getLogger('mobile_service_log')


class TicketQueries(graphene.ObjectType):
    get_tickets = graphene.Field(
        SelectOutputType,
        filter = TicketFilterInput(required=True)
    )
    
    @staticmethod
    def resolve_get_tickets(self, info, filter):
        log.info('request for get_tickets')
        try:
            validated = TicketSchema(**filter)
            data = Ticket.objects.get_tickets_for_mob(
                peopleid = validated.peopleid,
                buid = validated.buid,
                clientid = validated.clientid, 
                mdtz = validated.mdtz, 
                ctzoffset = validated.ctzoffset
                )
            records, count, msg = utils.get_select_output(data)
            log.info(f'{count} objects returned...')
            return SelectOutputType(nrows = count,  records = records,msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_tickets failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError("something went wrong")