import uuid
from django.contrib.gis.db.models import PointField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.activity.managers.location_manager import LocationManager
from apps.peoples.models import BaseModel
from apps.tenants.models import TenantAwareModel

def loc_json():
    return {"address": ""}



class Location(BaseModel, TenantAwareModel):
    class LocationStatus(models.TextChoices):
        MAINTENANCE = ("MAINTENANCE", "Maintenance")
        STANDBY     = ("STANDBY", "Standby")
        WORKING     = ("WORKING", "Working")
        SCRAPPED    = ("SCRAPPED", "Scrapped")
    
    uuid        = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    loccode     = models.CharField(_("Asset Code"), max_length = 50)
    locname     = models.CharField(_("Asset Name"), max_length = 250)
    enable      = models.BooleanField(_("Enable"), default = True)
    iscritical  = models.BooleanField(_("Critical"), default=False)
    gpslocation = PointField(_('GPS Location'), null = True, geography = True, srid = 4326, blank = True)
    parent      = models.ForeignKey("self", verbose_name = _( "Belongs to"), on_delete = models.RESTRICT, null = True, blank = True)
    locstatus   = models.CharField(_('Running Status'), choices = LocationStatus.choices, max_length = 55)
    type        = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Type"), on_delete = models.RESTRICT, null = True, blank = True, related_name='location_types')
    client      = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete = models.RESTRICT, null = True, blank = True, related_name='location_clients')
    bu          = models.ForeignKey("onboarding.Bt", verbose_name = _("Site"), on_delete = models.RESTRICT, null = True, blank = True, related_name='location_bus')
    locjson     = models.JSONField(_("Location Json"), encoder=DjangoJSONEncoder, blank=True, null=True, default=loc_json)

    objects = LocationManager()
    
    def __str__(self) -> str:
        return f'{self.locname} ({self.loccode})'
    
    class Meta(BaseModel.Meta):
        db_table = 'location'
        get_latest_by = ["mdtz", 'cdtz']
        constraints         = [
            models.UniqueConstraint(
                fields = ['loccode', 'bu','client'],
                name='loccode_bu_client_uk'
            ),
        ]
     