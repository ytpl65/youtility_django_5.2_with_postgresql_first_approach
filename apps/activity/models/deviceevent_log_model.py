import uuid
from django.contrib.gis.db.models import PointField
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.activity.managers.deviceeventlog_manager import DELManager
from apps.peoples.models import BaseModel



class DeviceEventlog(BaseModel, models.Model):
    class DeviceEvent(models.TextChoices):
        STEPCOUNT     = ('stepcount', 'Step Count')
        LOCATIONALERT = ('locationalert', 'Location Alert')
        DEVICEOGS     = ('devicelogs', 'Device Logs')
        LOGIN         = ('login', 'Log In')
        LOGOUT        = ('logout', 'Log Out')
    
    class NetworkProviderChoices(models.TextChoices):
        BLUETOOTH = ('bluetooth', 'Bluetooth')
        WIFI      = ('wifi', 'WIFI')
        ETHERNET  = ('ethernet', 'Ethernet')
        MOB       = ('mobile', 'Mobile')
        NONE      = ('none', 'None')
        
    class LocationAllowedChoices(models.TextChoices):
        LOCATIONALWAYS = ('locationalways', 'Location Always')
        ONLYWHILEUSING = ('onlywhileyusing', 'Only While Using')
        NONE           = ('NONE', 'NONE')
        

    uuid                   = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    deviceid               = models.CharField(_("Device Id"), max_length = 55)
    eventvalue             = models.CharField(_("Device Event"), max_length = 50, choices = DeviceEvent.choices)
    locationserviceenabled = models.BooleanField(_("Location Serivice Enabled"),default=False)
    islocationmocked       = models.BooleanField(_("Location Spoofed"),default=False)
    locationpermission     = models.CharField(max_length=25, choices=LocationAllowedChoices.choices, default=LocationAllowedChoices.NONE.value)
    gpslocation            = PointField(null=True, srid=4326, blank=True, geography = True)
    accuracy               = models.CharField(max_length=25, default="-")
    altitude               = models.CharField(max_length=25, default='-')
    bu                     = models.ForeignKey("onboarding.Bt", null = True,blank = True, on_delete = models.RESTRICT)
    client                 = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete= models.RESTRICT, null = True, blank = True, related_name='deviveevents_clients')
    receivedon             = models.DateTimeField(_("Received On"), auto_now = False, auto_now_add = True)
    people                 = models.ForeignKey('peoples.People', null = True, blank = True, on_delete = models.RESTRICT, related_name="deviceevent_people")
    batterylevel           = models.CharField(_("Battery Level"), max_length = 50, default = 'NA')
    signalstrength         = models.CharField(_("Signal Strength"), max_length = 50, default = 'NA')
    availintmemory         = models.CharField(_("Available Internal Memory"), max_length = 50, default = 'NA')
    availextmemory         = models.CharField(_("Available External Memory"), max_length = 50, default = 'NA')
    signalbandwidth        = models.CharField(_("Signal Bandwidth"), max_length = 50, default = 'NA')
    platformversion        = models.CharField(_("Android Version"), max_length = 50, default = 'NA')
    applicationversion     = models.CharField(_("App Version"), max_length = 50, default = 'NA')
    networkprovidername    = models.CharField(max_length=55, choices=NetworkProviderChoices.choices, default=NetworkProviderChoices.NONE.value)
    modelname              = models.CharField(_("Model Name"), max_length = 50, default = 'NA')
    installedapps          = models.TextField(_("Installed Apps"), default = 'NA')
    stepcount              = models.CharField(max_length = 55, default='No Steps')

    objects = DELManager()
    class Meta(BaseModel.Meta): 
        db_table = 'deviceeventlog'
        get_latest_by = ["mdtz", 'cdtz']
    
    def __str__(self) -> str:
        return f'{self.deviceid} {self.eventvalue}'
