from rest_framework import serializers
from apps.activity.models.job_model import JobneedDetails
import apps.service.validators as vs
from apps.work_order_management.models import Wom, WomDetails
from apps.activity.models.job_model import Jobneed
class Messages:
    AUTHFAILED     = "Authentication Failed "
    AUTHSUCCESS    = "Authentication Successfull"
    NOSITE         = "Unable to find site!"
    INACTIVE       = "Inactive client or people"
    NOCLIENTPEOPLE = "Unable to find client or People or User/Client are not verified"
    MULTIDEVICES   = "Cannot login on multiple devices, Please logout from the other device"
    WRONGCREDS     = "Incorrect Username or Password"
    NOTREGISTERED  = "Device Not Registered"
    INSERT_SUCCESS  = "Inserted Successfully!"
    UPDATE_SUCCESS  = "Updated Successfully!"
    IMPROPER_DATA   = "Failed to insert incorrect tablname or size of columns and rows doesn't match",
    WRONG_OPERATION = "Wrong operation 'id' is passed during insertion!"
    DBERROR         = "Integrity Error!"
    INSERT_FAILED   = "Failed to insert something went wrong!"
    UPDATE_FAILED   = "Failed to Update something went wrong!"
    NOT_INTIATED    = "Insert cannot be initated not provided necessary data"
    UPLOAD_FAILED   = "Upload Failed!"
    NOTFOUND        = "Unable to find people with this pelogid"
    START           = "Mutation start"
    END             = "Mutation end"
    ADHOCFAILED     = 'Adhoc service failed'
    NODETAILS       = ' Unable to find any details record against site/incident report'
    REPORTSFAILED   = 'Failed to generate jasper reports'
    NOTABLEFOUND    = 'Unable to find table!'



class StringToListField(serializers.ListField):
    def to_internal_value(self, data):
        if isinstance(data, str):
            # Clean the string and convert it to a list
            cleaned_data = data.split(',')
            return super().to_internal_value(cleaned_data)

        return super().to_internal_value(data)

class InsertSerializer(serializers.Serializer):

    record = serializers.JSONField()
    tablename = serializers.CharField()

    tablenames = [
        'jobneed', 'jobneeddetails', 'peopleeventlog', 
        'tracking', 'attachment'
    ]

    def validate_tablename(self, value):
        if value not in self.tablenames:
            raise serializers.ValidationError(
                Messages.NOTABLEFOUND
            )
        return value

    @staticmethod
    def validate_record(value):
        return vs.clean_record(record = value)

class JndSerializers(serializers.ModelSerializer):
    jobneed_id  = serializers.IntegerField()
    question_id = serializers.IntegerField()
    cuser_id    = serializers.IntegerField()
    muser_id    = serializers.IntegerField()
    class Meta:
        model = JobneedDetails
        exclude = ['question', 'jobneed', 'cuser', 'muser']

class WomDetailsSerializers(serializers.ModelSerializer):
    wom_id  = serializers.IntegerField()
    question_id = serializers.IntegerField()
    qset_id           = serializers.IntegerField()
    cuser_id    = serializers.IntegerField()
    muser_id    = serializers.IntegerField()
    class Meta:
        model = WomDetails
        exclude = ['question', 'qset', 'wom', 'cuser', 'muser']

class JobneedSerializer(serializers.ModelSerializer):
    asset_id          = serializers.IntegerField()
    job_id            = serializers.IntegerField()
    performedby_id    = serializers.IntegerField()
    client_id         = serializers.IntegerField()
    bu_id             = serializers.IntegerField()
    ticketcategory_id = serializers.IntegerField()
    parent_id         = serializers.IntegerField()
    pgroup_id         = serializers.IntegerField()
    people_id         = serializers.IntegerField()
    qset_id           = serializers.IntegerField()
    cuser_id          = serializers.IntegerField()
    muser_id          = serializers.IntegerField()
    ticket_id         = serializers.IntegerField()
    remarkstype_id   = serializers.IntegerField()

    class Meta:
        model = Jobneed
        exclude = ['receivedonserver', 'other_info', 'parent', 'people', 'pgroup', 'qset', 'geojson', 'ticket', 'remarkstype',
                   'asset', 'job', 'performedby', 'client', 'bu', 'ticketcategory', 'cuser', 'muser', 'id', 'journeypath']        

class WomSerializer(serializers.ModelSerializer):
    asset_id          = serializers.IntegerField()
    location_id            = serializers.IntegerField()
    vendor_id    = serializers.IntegerField()
    client_id         = serializers.IntegerField()
    bu_id             = serializers.IntegerField()
    ticketcategory_id = serializers.IntegerField()
    parent_id         = serializers.IntegerField()
    qset_id           = serializers.IntegerField()
    cuser_id          = serializers.IntegerField()
    muser_id          = serializers.IntegerField()
    categories = StringToListField()
    approvers = StringToListField()

    class Meta:
        model = Wom
        exclude = [ 'parent', 'qset', 'vendor', 'location',
                   'asset',  'client', 'bu', 'ticketcategory', 'cuser', 'muser', 'id' ]        

class PELSerializer(serializers.ModelSerializer):
    pass


class VideoFileUpload(serializers.Serializer):
    file    = serializers.FileField()
    biodata = serializers.JSONField()
    record  = serializers.JSONField()