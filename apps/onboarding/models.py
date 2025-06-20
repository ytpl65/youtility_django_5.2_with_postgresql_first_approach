from django.conf import settings
from django.urls import reverse
from django.contrib.gis.db.models import PolygonField
from django.db import models
from apps.tenants.models import TenantAwareModel
from apps.peoples.models import BaseModel
from .managers import BtManager, TypeAssistManager, GeofenceManager,ShiftManager, DeviceManager, SubscriptionManger
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import gettext_lazy as _
from django.contrib.gis.db.models import PointField
from django.contrib.postgres.fields import ArrayField
from django.db.models import Q
import uuid
from django.utils import timezone
# Create your models here.



def bu_defaults():
    return {
        "mobilecapability"        : [],
        "validimei"               : "",
        "webcapability"           : [],
        "portletcapability"       : [],
        "validip"                 : "",
        "reliveronpeoplecount"    : 0,
        "reportcapability"        : [],
        "usereliver"              : False,
        "pvideolength"            : 10,
        "guardstrenth"            : 0,
        "malestrength"            : 0,
        "femalestrength"          : 0,
        "siteclosetime"           : "",
        "tag"                     : "",
        "siteopentime"            : "",
        "nearbyemergencycontacts" : [],
        'maxadmins'               : 5,
        'address'                 : "",
        'address2'                : None,
        'permissibledistance'     : 0,
        'controlroom'             : [],
        'ispermitneeded'          : False,
        'no_of_devices_allowed'   : 0,
        'no_of_users_allowed_mob' : 0,
        'no_of_users_allowed_web' : 0,
        'no_of_users_allowed_both': 0,
        'devices_currently_added' : 0,
        'startdate'               : '',
        'enddate'                 : '',
        'onstop'                  : '',
        'onstopmessage'           : '',
        'clienttimezone'          : "",
        'billingtype'             : "",
        'total_people_count'     : 0,
        'contract_designcount'    : {},
        'posted_people'           : []
    }

class Bt(BaseModel, TenantAwareModel):
    
    uuid                = models.UUIDField(default=uuid.uuid4 ,null=True)
    bucode              = models.CharField(_('Code'), max_length = 30)
    solid               = models.CharField(max_length=30, null=True, blank=True, verbose_name='Sol ID')
    siteincharge        = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Site Incharge', on_delete=models.RESTRICT, null=True, blank=True, related_name='siteincharge')
    bupreferences       = models.JSONField(_('bupreferences'), null = True, default = bu_defaults,  encoder = DjangoJSONEncoder, blank = True)
    identifier          = models.ForeignKey('TypeAssist',verbose_name='Identifier',  null = True, blank = True, on_delete = models.RESTRICT, related_name="bu_idfs")
    buname              = models.CharField(_('Name'), max_length = 200)
    butree              = models.CharField(_('Bu Path'), null = True, blank = True, max_length = 300, default="")
    butype              = models.ForeignKey('TypeAssist', on_delete = models.RESTRICT,  null = True, blank = True,  related_name="bu_butypes", verbose_name="Type")
    parent              = models.ForeignKey('self', null = True, blank = True, on_delete = models.RESTRICT, related_name="children", verbose_name="Belongs To")
    enable              = models.BooleanField(_("Enable"), default = True)
    iswarehouse         = models.BooleanField(_("Warehouse"), default = False)
    gpsenable           = models.BooleanField(_("GPS Enable"), default = False)
    enablesleepingguard = models.BooleanField(_("Enable SleepingGuard"), default = False)
    skipsiteaudit       = models.BooleanField(_("Skip SiteAudit"), default = False)
    siincludes          = ArrayField(models.CharField(max_length = 50, blank = True), verbose_name= _("Site Inclides"), null = True, blank = True)
    deviceevent         = models.BooleanField(_("Device Event"), default = False)
    pdist               = models.FloatField(_("Permissible Distance"), default = 0.0, blank = True, null = True)
    gpslocation         = PointField(_('GPS Location'),null = True, blank = True, geography = True, srid = 4326)
    isvendor            = models.BooleanField(_("Vendor"), default = False)
    isserviceprovider   = models.BooleanField(_("ServiceProvider"), default = False)
    
    objects = BtManager()

    class Meta(BaseModel.Meta):
        db_table = 'bt'
        verbose_name = 'Buisiness Unit'
        verbose_name_plural = 'Buisiness Units'
        constraints = [models.UniqueConstraint(
            fields=['bucode', 'parent', 'identifier'],
            name='bu_bucode_parent_identifier_uk')]
        get_latest_by = ["mdtz", 'cdtz']

    def __str__(self) -> str:
        return f'{self.buname} ({self.bucode})'

    def get_absolute_wizard_url(self):
        return reverse("onboarding:wiz_bu_update", kwargs={"pk": self.pk})
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from apps.core import utils
        if self.siteincharge is None: self.siteincharge= utils.get_or_create_none_people()
        if self.butype is None: self.butype = utils.get_none_typeassist()

def shiftdata_json():
    return{
    }

class Shift(BaseModel, TenantAwareModel):
    bu                  = models.ForeignKey('Bt', verbose_name='Buisiness View', null = True, on_delete = models.RESTRICT, related_name="shift_bu")
    client              = models.ForeignKey('Bt', verbose_name='Buisiness View', null = True, on_delete = models.RESTRICT, related_name="shift_client")
    shiftname           = models.CharField(max_length = 50, verbose_name="Name")
    shiftduration       = models.IntegerField(null = True, verbose_name="Shift Duration")
    designation         = models.ForeignKey('TypeAssist', verbose_name='Buisiness View', null=True, blank=True, on_delete = models.RESTRICT)
    peoplecount         = models.IntegerField(null=True, blank=True, verbose_name='People Count')
    starttime           = models.TimeField(verbose_name="Start time")
    endtime             = models.TimeField(verbose_name='End time')
    nightshiftappicable = models.BooleanField(default = True, verbose_name="Night Shift Applicable")
    captchafreq         = models.IntegerField(default = 10, null = True)
    enable              = models.BooleanField(verbose_name='Enable', default = True)
    shift_data          = models.JSONField( encoder = DjangoJSONEncoder, blank = True, null = True, default = shiftdata_json)


    objects = ShiftManager()
    class Meta(BaseModel.Meta):
        db_table = 'shift'
        constraints = [models.UniqueConstraint(
            fields=['shiftname', 'bu', 'designation', 'client'], name='shiftname_bu_desgn_client_uk')]
        get_latest_by = ['mdtz', 'cdtz']

    def __str__(self):
        return f'{self.shiftname} ({self.starttime} - {self.endtime})'

    def get_absolute_wizard_url(self):
        return reverse("onboarding:wiz_shift_update", kwargs={"pk": self.pk})

class TypeAssist(BaseModel, TenantAwareModel):
    id= models.BigAutoField(primary_key = True)
    tacode = models.CharField(_("tacode"), max_length = 50)
    taname = models.CharField(_("taname"),   max_length = 100)
    tatype = models.ForeignKey( "self", verbose_name='TypeAssist', null = True, blank = True, on_delete = models.RESTRICT, related_name='children')
    bu     = models.ForeignKey("Bt",verbose_name='Buisiness View',  null = True, blank = True, on_delete = models.RESTRICT, related_name='ta_bus')
    client = models.ForeignKey("onboarding.Bt", verbose_name='Client',  null = True, blank = True, on_delete = models.RESTRICT, related_name='ta_clients')
    enable = models.BooleanField(_("Enable"), default = True)

    objects = TypeAssistManager()

    class Meta(BaseModel.Meta):
        db_table = 'typeassist'
        constraints = [
            models.UniqueConstraint(
                fields=['tacode', 'tatype', 'client'], name='code_unique'
            ),
        ]
    
    def __str__(self):
        return f'{self.taname} ({self.tacode})'

    def get_absolute_url(self):
        return reverse("onboarding:ta_update", kwargs={"pk": self.pk})

    def get_all_children(self):
        if self.pk is None:
            return []  
        children = [self]
        try:
            child_list = self.children.all()
        except AttributeError:
            return children
        for child in child_list:
            children.extend(child.get_all_children())
        return children

    def get_all_parents(self):
        parents = [self]
        if self.tatype is not None:
            parent = self.tatype
            parents.extend(parent.get_all_parents())
        return parents

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.tatype in self.get_all_children():
            raise ValidationError("A user cannot have itself \
                    or one of its' children as parent.")

def wizard_default():
    return {'wizard_data': {}}

def formData_default():
    return {'form_id': {}}

class GeofenceMaster(BaseModel):
    # id= models.BigIntegerField(primary_key = True)
    gfcode        = models.CharField(_("Code"), max_length = 100)
    gfname        = models.CharField(_("Name"), max_length = 100)
    alerttext     = models.CharField(_("Alert Text"), max_length = 100)
    geofence      = PolygonField(_("GeoFence"), srid = 4326, geography = True, null = True,)
    alerttogroup  = models.ForeignKey("peoples.Pgroup",null = True, verbose_name = _( "Alert to Group"), on_delete = models.RESTRICT)
    alerttopeople = models.ForeignKey(settings.AUTH_USER_MODEL,null = True, verbose_name = _(""), on_delete = models.RESTRICT)
    client        = models.ForeignKey("onboarding.Bt",null = True, verbose_name = _("Client"), on_delete = models.RESTRICT, related_name="for_clients")
    bu            = models.ForeignKey("onboarding.Bt", null = True, verbose_name = _( "Site"), on_delete = models.RESTRICT, related_name='for_sites')
    enable        = models.BooleanField(_("Enable"), default = True)

    objects = GeofenceManager()

    class Meta(BaseModel.Meta):
        db_table = 'geofencemaster'
        constraints = [
            models.UniqueConstraint(
                fields=['gfcode', 'bu'], name='gfcode_bu_uk')
        ]
        get_latest_by = ['mdtz']

    def __str__(self):
        return f'{self.gfname} ({self.gfname})'



class DownTimeHistory(BaseModel):
    reason = models.TextField(_("Downtime Reason"))
    starttime = models.DateTimeField(_("Start"), default=timezone.now)
    endtime = models.DateTimeField(_("End"),  default=timezone.now)
    client        = models.ForeignKey("onboarding.Bt",null = True, verbose_name = _("Client"), on_delete = models.RESTRICT)
    
    class Meta(BaseModel.Meta):
        db_table = 'downtime_history'
        get_latest_by = ['mdtz']

    
    def __str__(self):
        return self.reason

class Device(BaseModel, TenantAwareModel):
    # id     = models.BigIntegerField(_("Device Id"), primary_key = True)
    handsetname = models.CharField(_("Handset Name"), max_length=100)
    modelname = models.CharField(_("Model"), max_length=50)
    dateregistered = models.DateField(_("Date Registered"), default=timezone.now)
    lastcommunication = models.DateTimeField(_("Last Communication"), auto_now=False, auto_now_add=False)
    imeino = models.CharField(_("IMEI No"), max_length=15, null=True, blank=True, unique=True)
    lastloggedinuser = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name = _("Last Logged In User"), null = True, blank = True, on_delete = models.RESTRICT)
    phoneno = models.CharField(_("Phone No"), max_length=15, null=True, blank=True)
    isdeviceon = models.BooleanField(_("Is Device On"), default=True)
    client = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), null = True, blank = True, on_delete = models.RESTRICT)
    
    
    
    objects = DeviceManager()
    class Meta(BaseModel.Meta):
        db_table = 'device'
        get_latest_by = ["mdtz", 'cdtz']

    def __str__(self):
        return self.handsetname


class Subscription(BaseModel, TenantAwareModel):
    class StatusChoices(models.TextChoices):
        A  = ('Active', 'Active')
        IA = ('In Active', 'In Active')

    
    startdate = models.DateField(_("Start Date"), auto_now=False, auto_now_add=False)
    enddate = models.DateField(_("End Date"), auto_now=False, auto_now_add=False)
    terminateddate = models.DateField(_("Terminated Date"), auto_now=False, null=True, auto_now_add=False)
    reason = models.TextField(_("Reason"), null=True, blank=True)
    status = models.CharField(_("Status"), max_length=50, choices=StatusChoices.choices, default=StatusChoices.A.value)
    assignedhandset = models.ForeignKey(Device, verbose_name = _("Assigned Handset"), null = True, blank = True, on_delete = models.RESTRICT)
    client = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), null = True, blank = True, on_delete = models.RESTRICT)
    istemporary = models.BooleanField(_("Is Temporary"), default=False)
    
    objects = SubscriptionManger()
    
    class Meta(BaseModel.Meta):
        db_table = 'subscription'
        constraints = [
            models.UniqueConstraint(
                fields=['startdate', 'enddate', 'client'], name='startdate_enddate_client_uk')
        ]


