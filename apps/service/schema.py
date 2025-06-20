
import graphene
import graphql_jwt
from graphql_jwt.decorators import login_required
from apps.service.queries.ticket_queries import TicketQueries
from apps.service.queries.question_queries import QuestionQueries
from apps.service.queries.job_queries import JobQueries
from apps.service.queries.typeassist_queries import TypeAssistQueries
from apps.service.queries.workpermit_queries import WorkPermitQueries
from apps.service.queries.people_queries import PeopleQueries
from apps.service.queries.asset_queries import AssetQueries
from apps.service.queries.bt_queries import BtQueries
from graphene_django.debug import DjangoDebug
from .mutations import (
  InsertRecord, AdhocMutation,
  LoginUser, LogoutUser,
  ReportMutation,  TaskTourUpdate,
  UploadAttMutaion, SyncMutation, InsertJsonMutation
)
from .types import (
    PELogType, TrackingType, TestGeoType, 
)
from apps.attendance.models import (
    PeopleEventlog, Tracking, TestGeo
)
class Mutation(graphene.ObjectType):
    token_auth        = LoginUser.Field()
    logout_user       = LogoutUser.Field()
    insert_record     = InsertRecord.Field()
    update_task_tour  = TaskTourUpdate.Field()
    upload_report     = ReportMutation.Field()
    upload_attachment = UploadAttMutaion.Field()
    sync_upload       = SyncMutation.Field()
    adhoc_record      = AdhocMutation.Field()
    insert_json       = InsertJsonMutation.Field()
    refresh_token = graphql_jwt.Refresh.Field()



class Query(TicketQueries, QuestionQueries, JobQueries, TypeAssistQueries, WorkPermitQueries, PeopleQueries, AssetQueries, BtQueries, graphene.ObjectType):
    PELog_by_id = graphene.Field(PELogType, id = graphene.Int())
    trackings   = graphene.List(TrackingType)
    testcases   = graphene.List(TestGeoType)
    viewer      = graphene.String()

    @staticmethod
    def resolve_PELog_by_id(info, id):
        return PeopleEventlog.objects.get(id = id)
    
    @staticmethod
    def resolve_trackings(info):
        return Tracking.objects.all()
    
    @staticmethod
    def resole_testcases(info):
        objs = TestGeo.objects.all()
        return list(objs)

    @login_required
    def resolve_viewer(self, info, **kwargs):
        return  "validtoken" if info.context.user.is_authenticated else "tokenexpired"



class RootQuery(Query):
    debug = graphene.Field(DjangoDebug, name='_debug')
    pass

class RootMutation(Mutation):
    pass

schema = graphene.Schema(query = RootQuery, mutation = RootMutation)
