import graphene
from graphene_django.types import DjangoObjectType
from graphene_file_upload.scalars import Upload
from .converters import convert_point_field, convert_linestring_field, convert_polygon_field
from apps.activity.models.asset_model import Asset
from apps.activity.models.job_model import Job, Jobneed, JobneedDetails
from apps.activity.models.question_model import Question, QuestionSet, QuestionSetBelonging
from apps.attendance.models import PeopleEventlog, TestGeo, Tracking
from apps.onboarding.models import TypeAssist
from apps.peoples.models import People, Pgbelonging, Pgroup

from .scalars import LineStringScalar, PointScalar, PolygonScalar


class PointFieldType(graphene.ObjectType):
    latitude = graphene.Float(description="Latitude")
    longitude = graphene.Float(description="Longitude")


class LineStringPointType(graphene.ObjectType):
    latitude = graphene.Float(description="Latitude")
    longitude = graphene.Float(description="Longitude")


class PolygonPointType(graphene.ObjectType):
    latitude = graphene.Float(description="Latitude")
    longitude = graphene.Float(description="Longitude")


class PELogType(DjangoObjectType):
    startlocation = PointScalar(description="Start location")
    endlocation = PointScalar(description="End location")
    journeypath = LineStringScalar(description="Journey path")

    class Meta:
        model = PeopleEventlog
        fields = "__all__"
        convert_choices_to_enum = False

    def resolve_startlocation(self, info):
        if self.startlocation:
            return {'latitude': self.startlocation.y, 'longitude': self.startlocation.x}
        return None
    
    def resolve_endlocation(self,info):
        if self.endlocation:
            return {'latitude':self.endlocation.y, 'longitude':self.endlocation.x}
        return None
    
    def resolve_journeypath(self,info):
        if self.journeypath:
            return [[{'latitude': point[1], 'longitude': point[0]} 
                    for point in line.coords] 
                    for line in [self.journeypath]]
        return None


class TrackingType(DjangoObjectType):
    gpslocation = PointScalar(description="GPS location")

    class Meta:
        model = Tracking
        fields = "__all__"
        convert_choices_to_enum = False


class TestGeoType(DjangoObjectType):
    point = PointScalar(description="Point")
    line = LineStringScalar(description="Line")
    poly = PolygonScalar(description="Polygon")

    class Meta:
        model = TestGeo
        fields = "__all__"
        convert_choices_to_enum = False


class PeopleType(DjangoObjectType):
    class Meta:
        model = People
        fields = "__all__"


class VerifyClientOutput(graphene.ObjectType):
    rc = graphene.Int(default_value=0,description="Response code")
    msg = graphene.String(description="Message")
    url = graphene.String(default_value="",description="URL")


class BasicOutput(graphene.ObjectType):
    rc = graphene.Int(default_value=0,description="Response code")
    msg = graphene.String(description="Message")
    email = graphene.String(description="Email")


class DowntimeResponse(graphene.ObjectType):
    message = graphene.String(description="Message")
    startDateTime = graphene.String(default_value="",description="Start date time")
    endDateTime = graphene.String(default_value="",description="End date time")


class LoginResponseType(DjangoObjectType):
    tenantid = graphene.Int(description="Tenant id")
    shiftid = graphene.Int(description="Shift id")

    class Meta:
        model = People
        fields = ["peoplecode", "loginid", "peoplename", "isadmin", "email", "mobno"]


class AssetType(DjangoObjectType):
    gpslocation = graphene.Field(PointFieldType)

    def resolve_gpslocation(self, info):
        if self.gpslocation:
            return PointFieldType(
                latitude=self.gpslocation.y, longitude=self.gpslocation.x
            )
        return None

    class Meta:
        model = Asset
        fields = "__all__"  # Instead of exclude, use fields
        convert_choices_to_enum = False


class QuestionType(DjangoObjectType):
    class Meta:
        model = Question
        fields = "__all__"


class QSetType(DjangoObjectType):
    class Meta:
        model = QuestionSet
        fields = "__all__"


class QSetBlngType(DjangoObjectType):
    class Meta:
        model = QuestionSetBelonging
        fields = "__all__"


class PgBlngType(DjangoObjectType):
    class Meta:
        model = Pgbelonging
        fields = "__all__"


class PgroupType(DjangoObjectType):
    class Meta:
        model = Pgroup
        fields = "__all__"

class AuthInput(graphene.InputObjectType):
    clientcode = graphene.String(required=True,description="Client code")
    loginid = graphene.String(required=True,description="Login id")
    password = graphene.String(required=True,description="Password")
    deviceid = graphene.String(required=True,description="Device id")


class AuthOutput(graphene.ObjectType):
    isauthenticated = graphene.Boolean(description="Is authenticated")
    user = graphene.Field(PeopleType,description="User")
    msg = graphene.String(description="Message")


class TyType(DjangoObjectType):
    class Meta:
        model = TypeAssist
        fields = ["id", "tacode", "taname"]


class BaseReturnType:
    user = graphene.Field(PeopleType,description="User")
    status = graphene.Int(description="Status")
    msg = graphene.String(description="Message")


class RowInput(graphene.InputObjectType):
    columns = graphene.List(graphene.String,description="Columns")
    values = graphene.List(graphene.String,description="Values")
    tablename = graphene.String(description="Table name")


class RowOutput(graphene.ObjectType):
    id = graphene.Int(description="Id")
    msg = graphene.JSONString(description="Message")


class TemplateReportInput(graphene.InputObjectType):
    questionsetid = graphene.Int(required=True,description="Question set id")
    tablename = graphene.String(required=True,description="Table name")
    columns = graphene.List(graphene.String,description="Columns")
    values = graphene.List(graphene.String,description="Values")
    childs = graphene.List(graphene.String,description="Childs")


class AttachmentInput(graphene.InputObjectType):
    file = Upload(required=True,description="File")
    pelogid = graphene.Int(required=True,description="People event log id")
    peopleid = graphene.Int(required=True,description="People id")
    filename = graphene.String(required=True,description="File name")
    path = graphene.String(required=True,description="Path")


class AdhocInputType(graphene.InputObjectType):
    plandatetime = graphene.String(required=True,description="Plan date time")
    jobdesc = graphene.String(required=True,description="Job description")
    bu_id = graphene.Int(required=True,description="Business unit id")
    people_id = graphene.Int(required=True,description="People id")
    site_id = graphene.Int(required=True,description="Site id")
    qset_id = graphene.Int(required=True,description="Question set id")
    remarks = graphene.String(required=False,description="Remarks")


class TestJsonInput(graphene.InputObjectType):
    file = Upload(required=True,description="File")
    sevicename = graphene.String(required=True,description="Service name")


class ServiceOutputType(graphene.ObjectType):
    rc = graphene.Int(default_value=0,description="Response code")
    msg = graphene.String(description="Message")
    recordcount = graphene.Int(description="Record count")
    traceback = graphene.String(default_value="NA",description="Trace back")
    uuids = graphene.List(graphene.String, default_value=(),description="UUIDs")


class JobType(DjangoObjectType):
    class Meta:
        model = Job
        exclude = ["other_info"]  # Only using exclude, removed fields='__all__'


class JobneedDetailsType(DjangoObjectType):
    class Meta:
        model = JobneedDetails
        fields = "__all__"


class JobneedType(DjangoObjectType):
    details = graphene.List(JobneedDetailsType)

    class Meta:
        model = Jobneed
        exclude = ["other_info", "receivedonserver"]  # Only using exclude

    def resolve_details(self, info):
        return JobneedDetails.objects.filter(jobneed=self)


class JobneedMdtzAfter(graphene.ObjectType):
    jobneedid = graphene.Int(description="Job need id")
    jobdesc = graphene.String(description="Job description")
    plandatetime = graphene.String(description="Plan date time")
    expirydatetime = graphene.String(description="Expiry date time")
    receivedonserver = graphene.String(description="Received on server")
    starttime = graphene.String(description="Start time")
    endtime = graphene.String(description="End time")
    gpslocation = PointScalar(description="GPS location")
    remarks = graphene.String(description="Remarks")
    cdtz = graphene.String(description="Created date time")
    mdtz = graphene.String(description="Modified date time")
    jobstatus = graphene.String(description="Job status")
    jobtype = graphene.String(description="Job type")
    pgroup_id = graphene.Int(description="People group id")
    asset_id = graphene.Int(description="Asset id")
    cuser_id = graphene.Int(description="Created user id")
    muser_id = graphene.Int(description="Modified user id")
    performedby_id = graphene.Int(description="Performed by id")
    bu_id = graphene.Int(description="Business unit id")
    job_id = graphene.Int(description="Job id")
    seqno = graphene.Int(description="Sequence number")
    ticketcategory_id = graphene.Int(description="Ticket category id")
    ctzoffset = graphene.Int(description="Client timezone offset")
    multifactor = graphene.Decimal(description="Multi factor")
    frequency = graphene.String(description="Frequency")


class SelectOutputType(graphene.ObjectType):
    nrows = graphene.Int(description="Number of rows")
    ncols = graphene.Int(description="Number of columns")
    msg = graphene.String(description="Message")
    rc = graphene.Int(default_value=0,description="Response code")
    records = graphene.JSONString(description="Records")


class UploadAttType(graphene.InputObjectType):
    record = graphene.JSONString(required=True,description="Record")
    tablname = graphene.String(required=True,description="Table name")
    file = Upload(description="File")


class GetPdfUrl(graphene.ObjectType):
    url = graphene.String(description="URL")
