from apps.peoples.models import BaseModel
import uuid
from apps.tenants.models import TenantAwareModel
from django.db import models
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.gis.db.models import LineStringField, PointField, PolygonField
from django.utils.translation import gettext_lazy as _
from .managers import PELManager
from django.contrib.postgres.fields import ArrayField

# Create your models here.

def peventlog_json():
    return {
        'verified_in': False,
        'distance_in':None,
        'verified_out': False,
        'distance_out':None,
        'threshold': '0.3',
        'model':'Facenet512',
        'similarity_metric':'cosine'
    }

def pel_geojson():
    return {
        'startlocation':"",
        'endlocation':""
    }

############## PeopleEventlog Table ###############

class PeopleEventlog(BaseModel, TenantAwareModel):

    class TransportMode(models.TextChoices):
        BIKE     = ('BIKE', 'Bike')
        RICKSHAW = ('RICKSHAW', 'Rickshaw')
        BUS      = ('BUS', 'Bus')
        TRAIN    = ('TRAIN', 'Train')
        TRAM     = ('TRAM', 'Tram')
        PLANE    = ('PLANE', 'Plane')
        FERRY    = ('FERRY', 'Ferry')
        NONE     = ('NONE', 'NONE')
        CAR      = ('CAR', 'Car')
        TAXI     = ('TAXI', 'Taxi')
        OLA_UBER = ('OLA_UBER', 'Ola/Uber')

    uuid               = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    people             = models.ForeignKey(settings.AUTH_USER_MODEL, null = True, blank = True, on_delete = models.RESTRICT, verbose_name='People')
    client             = models.ForeignKey("onboarding.Bt",  null = True, blank = True, on_delete = models.RESTRICT, related_name='clients')
    bu                 = models.ForeignKey("onboarding.Bt",  null = True, blank = True, on_delete = models.RESTRICT, related_name='bus')
    shift              = models.ForeignKey('onboarding.Shift', null = True, blank = True, on_delete = models.RESTRICT)
    verifiedby         = models.ForeignKey(settings.AUTH_USER_MODEL, null = True, blank = True, on_delete = models.RESTRICT, related_name='verifiedpeoples', verbose_name='Verified By')
    geofence           = models.ForeignKey('onboarding.GeofenceMaster', null = True, blank = True, on_delete = models.RESTRICT)
    peventtype         = models.ForeignKey('onboarding.TypeAssist', null = True, blank = True, on_delete = models.RESTRICT)
    transportmodes     = ArrayField(models.CharField(max_length = 50, blank = True, choices = TransportMode.choices, default = TransportMode.NONE.value), default = list)
    punchintime        = models.DateTimeField(_('In'), null = True)
    punchouttime       = models.DateTimeField(_('Out'), null = True)
    datefor            = models.DateField(_("Date"), null = True)
    distance           = models.FloatField(_("Distance"), null = True, blank = True)
    duration           = models.IntegerField(_("Duration"), null = True, blank = True)
    expamt             = models.FloatField(_("exampt"), default = 0.0  ,null = True, blank = True)
    accuracy           = models.FloatField(_("accuracy"), null = True, blank = True)
    deviceid           = models.CharField(_("deviceid"), max_length = 50, null = True, blank = True)
    startlocation      = PointField(_("GPS-In"), null = True, geography = True, blank=True, srid = 4326)
    endlocation        = PointField(_("GPS-Out"), null = True, geography = True, blank = True, srid = 4326)
    journeypath        = LineStringField(geography = True, null = True, blank=True)
    remarks            = models.CharField(_("remarks"), null = True, max_length = 500, blank = True)
    facerecognitionin  = models.BooleanField(_("Enable Face-Recognition In"), default = False, null=True, blank=True)
    facerecognitionout = models.BooleanField(_("Enable Face-Recognition Out"), default = False, null=True, blank=True)
    peventlogextras    = models.JSONField(_("peventlogextras"), encoder = DjangoJSONEncoder, default = peventlog_json)
    otherlocation      = models.CharField(_("Other Location"), max_length = 50, null=True)
    reference          = models.CharField('Reference', max_length = 55, null = True)
    geojson            = models.JSONField(default=pel_geojson, null=True, blank=True)

    objects = PELManager()

    class Meta(BaseModel.Meta):
        db_table = 'peopleeventlog'

# temporary table
class Tracking(models.Model):
    class Identifier(models.TextChoices):
        NONE         = ('NONE', 'None')
        CONVEYANCE   = ('CONVEYANCE', 'Conveyance')
        EXTERNALTOUR = ('EXTERNALTOUR', 'External Tour')
        INTERNALTOUR = ('INTERNALTOUR', 'Internal Tour')
        SITEVISIT    = ('SITEVISIT', 'Site Visit')
        TRACKING     = ('TRACKING', 'Tracking')
    
    # id           = models.BigIntegerField(primary_key = True)
    uuid          = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    deviceid      = models.CharField(max_length = 40)
    gpslocation   = PointField(geography = True,null=True,blank=True, srid = 4326)
    receiveddate  = models.DateTimeField(editable = True, null = True)
    people        = models.ForeignKey(settings.AUTH_USER_MODEL, null = True, blank = True, on_delete = models.RESTRICT, verbose_name='People')
    transportmode = models.CharField(max_length = 55)
    reference     = models.CharField(max_length = 255, default = None)
    identifier    = models.CharField(max_length = 55, choices = Identifier.choices, default = Identifier.NONE.value)

    class Meta:
        db_table = 'tracking'


class TestGeo(models.Model):
    # id= models.BigIntegerField(primary_key = True)
    code = models.CharField(max_length = 15)
    poly = PolygonField(geography = True, null = True)
    point = PointField(geography = True, blank=True, null = True)
    line = LineStringField(geography = True, null = True, blank=True)
