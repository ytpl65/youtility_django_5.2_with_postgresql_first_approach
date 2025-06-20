import graphene
from  graphql_jwt.shortcuts import get_token, get_payload, get_refresh_token, create_refresh_token
from graphql_jwt.decorators import login_required
from graphene.types.generic import GenericScalar
from graphql import GraphQLError
from apps.service import utils as sutils
from apps.core import utils as cutils, exceptions as excp
from apps.peoples.models import People
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FileUploadParser, JSONParser
from rest_framework.response import Response
from django.core.serializers.json import DjangoJSONEncoder
from . import types as ty
from graphene_file_upload.scalars import Upload
from rest_framework.permissions import AllowAny
from pprint import pformat
import zipfile
import json
from .utils import get_json_data
from logging import getLogger
import traceback as tb
from graphql_jwt import ObtainJSONWebToken
from apps.core import exceptions as excp

log = getLogger('message_q')
tlog = getLogger('tracking')
error_logger = getLogger("error_logger")
err = error_logger.error


class LoginUser(graphene.Mutation):
    """
    Authenticates user before log in
    """
    token   = graphene.String()
    user    = graphene.JSONString()
    payload = GenericScalar()
    msg     = graphene.String()
    shiftid = graphene.Int()
    refreshtoken = graphene.String()

    class Arguments:
        input =  ty.AuthInput(required = True)

    @classmethod
    def mutate(cls, root, info, input):
        log.warning("login mutations start [+]")
        try:
            log.info("%s, %s, %s", input.deviceid, input.loginid, input.password)
            from .auth import auth_check
            output, user = auth_check(info, input, cls.returnUser)
            cls.updateDeviceId(user, input)
            log.warning("login mutations end [-]")
            return output
        except (excp.MultiDevicesError, excp.NoClientPeopleError, excp.NoSiteError,
            excp.NotBelongsToClientError, excp.NotRegisteredError, excp.WrongCredsError) as exc:
            log.warning(exc, exc_info=True)
            raise GraphQLError(exc) from exc

        except Exception as exc:
            err(exc, exc_info=True)
            raise GraphQLError(exc) from exc


    @classmethod
    def returnUser(cls, user, request):
        user.last_login = timezone.now()
        user.save()
        token = get_token(user)
        request.jwt_refresh_token = create_refresh_token(user)
        log.info(f"user logged in successfully! {user.peoplename}")
        user = cls.get_user_json(user)
        return LoginUser(token = token, user = user, payload = get_payload(token, request), refreshtoken = request.jwt_refresh_token.get_token())

    @classmethod
    def updateDeviceId(cls, user, input):
        People.objects.update_deviceid(input.deviceid, user.id)

    @classmethod
    def get_user_json(cls, user):
        from django.db.models import F
        import json

        emergencycontacts = set(People.objects.get_emergencycontacts(user.bu_id, user.client_id))
        emergencyemails = set(People.objects.get_emergencyemails(user.bu_id, user.client_id))
        log.info(f"emergencycontact: {pformat(emergencycontacts)}")
        log.info(f"emergencyemails: {pformat(emergencyemails)}")
        qset = People.objects.annotate(
            loggername          = F('peoplename'),
            mobilecapability    = F('people_extras__mobilecapability'),
            pvideolength        = F('client__bupreferences__pvideolength'),
            enablesleepingguard = F('client__enablesleepingguard'),
            skipsiteaudit       = F('client__skipsiteaudit'),
            deviceevent         = F('client__deviceevent'),
            isgpsenable         = F('client__gpsenable'),
            clientcode          = F('client__bucode'),
            clientname          = F('client__buname'),
            clientenable        = F('client__enable'),
            sitecode            = F('bu__bucode'),
            sitename            = F('bu__buname'),
            ).values(
                'loggername',  'mobilecapability',
                'enablesleepingguard','peopleimg',
                'skipsiteaudit', 'deviceevent', 'pvideolength',
                'client_id', 'bu_id', 'mobno', 'email', 'isverified',   
                'deviceid', 'id', 'enable', 'isadmin', 'peoplecode', 'dateofjoin',
                'tenant_id', 'loginid', 'clientcode', 'clientname', 'sitecode',
                'sitename', 'clientenable', 'isgpsenable').filter(id = user.id)
        qsetList = list(qset)
        qsetList[0].update({'emergencycontacts': list(emergencycontacts), 'emergencyemails':list(emergencyemails)})
        qsetList[0]['emergencyemails'] = str(qsetList[0]['emergencyemails']).replace('[', '').replace(']', '').replace("'", "")
        qsetList[0]['emergencycontacts'] = str(qsetList[0]['emergencycontacts']).replace('[', '').replace(']', '').replace("'", "")
        qsetList[0]['mobilecapability'] = str(qsetList[0]['mobilecapability']).replace('[', '').replace(']', '').replace("'", "")

        return json.dumps(qsetList[0], cls = DjangoJSONEncoder)



class LogoutUser(graphene.Mutation):
    """
    Logs out user after resetting the deviceid 
    """
    status = graphene.Int(default_value = 404)
    msg    = graphene.String(default_value = "Failed")

    @classmethod
    @login_required
    def mutate(cls, root,info):

        updated = People.objects.reset_deviceid(info.context.user.id)
        if updated: 
            status, msg = 200, "Success"
            # log.info(f'user logged out successfully! {user.}')

        return LogoutUser(status = status, msg = msg)


class TaskTourUpdate(graphene.Mutation):
    """
    Update Task, Tour fields.
    like 'cdtz', 'mdtz', 'jobstatus', 'performedby' etc
    """
    output = graphene.Field(ty.ServiceOutputType)
    class Arguments:
        records = graphene.List(graphene.String,required = True)

    @classmethod
    def mutate(cls, root, info, records):
        log.warning("\n\ntasktour-update mutations start [+]")
        db = cutils.get_current_db_name()
        o = sutils.perform_tasktourupdate(records=records, request = info.context, db=db)
        log.info(f"Response: # records updated:{o.recordcount}, msg:{o.msg}, rc:{o.rc}, traceback:{o.traceback}")
        log.warning("tasktour-update mutations end [-]")
        return TaskTourUpdate(output = o)

class InsertRecord(graphene.Mutation):
    """
    Inserts new record in the specified table.
    """
    output = graphene.Field(ty.ServiceOutputType)

    class Arguments:
        records = graphene.List(graphene.String,required = True)


    @classmethod
    def mutate(cls, root, info, records):
        log.warning("\n\ninsert-record mutations start [+]")
        db = cutils.get_current_db_name()
        log.info(f"Records: {records}")
        o = sutils.perform_insertrecord(records=records, db=db)
        log.info(f"Response: # records updated:{o.recordcount}, msg:{o.msg}, rc:{o.rc}, traceback:{o.traceback}")
        log.warning("insert-record mutations end [-]")
        return InsertRecord(output = o)


class ReportMutation(graphene.Mutation):
    output = graphene.Field(ty.ServiceOutputType)
    class Arguments:
        records = graphene.List(graphene.String,required = True)

    @classmethod
    def mutate(cls, root, info, records):
        log.warning("\n\nreport mutations start [+]")
        db=cutils.get_current_db_name()
        o = sutils.perform_reportmutation(records=records, db=db)
        log.info(f"Response: {o.recordcount}, {o.msg}, {o.rc}, {o.traceback}")
        log.warning("report mutations end [-]")
        return ReportMutation(output = o)

class UploadAttMutaion(graphene.Mutation):
    output = graphene.Field(ty.ServiceOutputType)

    class Arguments:
        bytes    = graphene.List(graphene.Int, required=True)
        biodata = graphene.String(required = True)
        record  = graphene.String(required = True)

    @classmethod
    def mutate(cls,root, info, bytes,  record, biodata):
        log.info("\n\nupload-attachment mutations start [+]")
        try:
            recordcount=0
            log.info(f"type of file is {type(bytes)}")
            record = json.loads(record)
            biodata = json.loads(biodata)
            log.info(f"Record: {record}")
            log.info(f"Bio Data: {biodata}")
            o = sutils.perform_uploadattachment(bytes, record, biodata)
            recordcount += o.recordcount
            log.info(f"Response: {o.recordcount}, {o.msg}, {o.rc}, {o.traceback}")
            o.recordcount = recordcount
            return UploadAttMutaion(output = o)
        except Exception as e:
            err(f"Exception: {e}", exc_info=True)
            return UploadAttMutaion(output = ty.ServiceOutputType(rc = 1, recordcount = 0, msg = 'Upload Failed', traceback = tb.format_exc()))


class UploadFile(APIView):
    parser_classes = [MultiPartParser, FileUploadParser, JSONParser]
    permission_classes = [AllowAny]
    
    def post(self, request, format=None):
        file    = request.data.get('file')
        biodata = json.loads(request.data.get('biodata'))
        record  = json.loads(request.data.get('record'))
        
        if file and biodata and record:
            output = sutils.perform_uploadattachment(file, record, biodata)
        else: return Response(data={'rc':1, 'msg':'No data', 'recordcount':0})
        resp = Response(data={'rc':output.rc, 'msg':output.msg, 
            'recordcount':output.recordcount, 'traceback':output.traceback})
        log.warning(f'Response:{pformat(resp.data)}')
        return resp
        


class AdhocMutation(graphene.Mutation):
    output = graphene.Field(ty.ServiceOutputType)
    class Arguments:
        records = graphene.List(graphene.String,required = True)

    @classmethod
    def mutate(cls, root, info, records):
        db = cutils.get_current_db_name()
        o = sutils.perform_adhocmutation(records=records, db=db)
        log.info(f"Response: {o.recordcount}, {o.msg}, {o.rc}, {o.traceback}")
        return AdhocMutation(output = o)


class InsertJsonMutation(graphene.Mutation):
    output = graphene.Field(ty.ServiceOutputType)

    class Arguments:
        jsondata = graphene.List(graphene.String,required = True)
        tablename = graphene.String(required = True)

    @classmethod
    def mutate(cls, root, info, jsondata, tablename):
        # sourcery skip: instance-method-first-arg-name
        from .utils import insertrecord_json
        from apps.core.utils import get_current_db_name
        import json
        tlog.info('\n\n\ninsert jsondata mutations start[+]')
        rc, traceback, resp, recordcount = 1,  'NA', 0, 0
        msg = 'Insert Failed!'
        uuids = []
        try:
            db = get_current_db_name()
            tlog.info(f'=================== jsondata:============= \n{jsondata}')
            uuids = insertrecord_json(jsondata, tablename)
            recordcount, msg, rc = 1, 'Inserted Successfully', 0
        except Exception as e:
            err('something went wrong', exc_info = True)
            msg, rc, traceback = 'Insert Failed!',1, tb.format_exc()
        
        o = ty.ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback, uuids=uuids)
        tlog.info(f"\n\n\nResponse: {o.recordcount}, {o.msg}, {o.rc}, {o.traceback} {uuids=}")
        return InsertJsonMutation(output = o)



class SyncMutation(graphene.Mutation):
    rc = graphene.Int()

    class Arguments:
        file         = Upload(required = True)
        filesize     = graphene.Int(required = True)
        totalrecords = graphene.Int(required = True)

    @classmethod
    def mutate(cls, root, info, file, filesize, totalrecords):
        # sourcery skip: avoid-builtin-shadow
        from apps.core.utils import get_current_db_name
        log.info("\n\nsync now mutation is running")
        import zipfile
        from apps.service.utils import call_service_based_on_filename
        try:
            id = file.name.split('_')[1].split('.')[0]
            log.info(f"sync inputs: totalrecords:{totalrecords} filesize:{filesize} typeof file:{type(file)} by user with id {id}")
            db = get_current_db_name()
            log.info(f'the type of file is {type(file)}')
            with zipfile.ZipFile(file) as zip:
                log.debug(f'{file = }')
                zipsize = TR = 0
                for file in zip.filelist:
                    log.debug(f'{file = }')
                    zipsize += file.file_size
                    log.info(f'filename: {file.filename} and size: {file.file_size}')
                    with zip.open(file) as f:
                        data = get_json_data(f)
                        # raise ValueError
                        TR += len(data)
                        call_service_based_on_filename(data, file.filename, db = db, request=info.context, user=id)
                log.info(f"file size given: {filesize = } and calculated {zipsize = }")
                if filesize !=  zipsize:
                    log.error(f"file size is not matched with the actual zipfile {filesize} x {zipsize}")
                    raise excp.FileSizeMisMatchError
                if TR !=  totalrecords:
                    log.error(f"totalrecords is not matched with th actual totalrecords after extraction... {totalrecords} x {TR}")
                    raise excp.TotalRecordsMisMatchError
        except Exception:
            err("something went wrong!", exc_info = True)
            return SyncMutation(rc = 1)
        else:
            return SyncMutation(rc = 0)


class TestMutation(graphene.Mutation):
    class Arguments:
        name = graphene.String(required = True)
    output = graphene.String()
    
    @classmethod
    def mutate(cls, root, info, name):
        return TestMutation(output = f'Hello {name}')