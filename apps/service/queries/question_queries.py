import graphene
from apps.activity.models.question_model import Question, QuestionSet, QuestionSetBelonging 
from graphql import GraphQLError
from apps.service.pydantic_schemas.question_schema import QuestionModifiedSchema, QuestionSetModifiedSchema, QuestionSetBelongingModifiedSchema

from apps.service.inputs.questions_input import QuestionModifiedFilterInput, QuestionSetModifiedFilterInput, QuestionSetBelongingModifiedFilterInput
from apps.service.types import SelectOutputType
from logging import getLogger   
from apps.core import utils
from pydantic import ValidationError

log = getLogger('mobile_service_log')

class QuestionQueries(graphene.ObjectType):
    get_questionsmodifiedafter = graphene.Field(
        SelectOutputType,
        filter = QuestionModifiedFilterInput(required=True)
    )

    get_qsetmodifiedafter = graphene.Field(
        SelectOutputType,
        filter = QuestionSetModifiedFilterInput(required=True)
    )

    get_qsetbelongingmodifiedafter = graphene.Field(
        SelectOutputType,
        filter = QuestionSetBelongingModifiedFilterInput(required=True)
    )

    @staticmethod
    def resolve_get_questionsmodifiedafter(self, info, filter):
        try:
            log.info('request for get_questions_modified_after')
            validated = QuestionModifiedSchema(**filter)
            data = Question.objects.get_questions_modified_after(mdtz=validated.mdtz,clientid = validated.clientid)
            records, count, msg = utils.get_select_output(data)
            log.info(f'{count} objects returned...')
            return SelectOutputType(nrows = count,  records = records,msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_questions_modified_after failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_questions_modified_after failed: {str(e)}")


    @staticmethod
    def resolve_get_qsetmodifiedafter(self, info, filter):
        try:
            log.info('request for get_questionset_modified_after')
            validated = QuestionSetModifiedSchema(**filter)
            data = QuestionSet.objects.get_qset_modified_after(mdtz = validated.mdtz,buid = validated.buid,clientid = validated.clientid, peopleid = validated.peopleid)
            records, count, msg = utils.get_select_output(data)
            log.info(f'{count} objects returned...')
            return SelectOutputType(nrows = count,  records = records,msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_questionset_modified_after failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_questionset_modified_after failed: {str(e)}")
        
    @staticmethod
    def resolve_get_qsetbelongingmodifiedafter(self, info, filter):
        try:
            log.info('request for get_questionsetbelonging_modified_after')
            validated = QuestionSetBelongingModifiedSchema(**filter)
            data = QuestionSetBelonging.objects.get_modified_after(mdtz = validated.mdtz,buid = validated.buid)
            records, count, msg = utils.get_select_output(data)
            log.info(f'{count} objects returned...')
            return SelectOutputType(nrows = count,  records = records,msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_questionsetbelonging_modified_after failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_questionsetbelonging_modified_after failed: {str(e)}")