from django.db import models
from apps.peoples.models import BaseModel
from apps.tenants.models import TenantAwareModel
from django.contrib.gis.db.models import PointField
from django.utils.translation import gettext_lazy as _
import uuid
from django.core.serializers.json import DjangoJSONEncoder
from apps.activity.managers.asset_manager import AssetManager,AssetLogManager
from django.conf import settings


def asset_json():
    return {
        "service": "",
        "ismeter": False,
        "meter": "",
        "bill_val": 0.0,
        "supplier": "",
        "msn": "",
        "bill_date": "",
        "purchase_date": "",
        "model": "",
        "inst_date": "",  # installation date
        "sfdate": "",
        "stdate": "",
        "yom": "",  # year of Mfg
        "tempcode": "",
        "po_number": "",
        "invoice_no": "",
        "invoice_date": "",
        "far_asset_id": "",
        "multifactor": 1,
        "is_nonengg_asset": False,
    }


class Asset(BaseModel,TenantAwareModel):
    class Identifier(models.TextChoices):
       NONE       = ("NONE", "None")
       ASSET      = ("ASSET", "Asset")
       CHECKPOINT = ("CHECKPOINT", "Checkpoint")
       NEA        = ("NEA", "Non Engineering Asset")

    class RunningStatus(models.TextChoices):
        MAINTENANCE = ("MAINTENANCE", "Maintenance")
        STANDBY     = ("STANDBY", "Standby")
        WORKING     = ("WORKING", "Working")
        SCRAPPED    = ("SCRAPPED", "Scrapped")

    uuid          = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    assetcode     = models.CharField(_("Asset Code"), max_length = 50)
    assetname     = models.CharField(_("Asset Name"), max_length = 250)
    enable        = models.BooleanField(_("Enable"), default = True)
    iscritical    = models.BooleanField(_("Critical"))
    gpslocation   = PointField(_('GPS Location'), null = True, geography = True, srid = 4326, blank = True)
    parent        = models.ForeignKey("self", verbose_name = _( "Belongs to"), on_delete = models.RESTRICT, null = True, blank = True)
    identifier    = models.CharField( _('Asset Identifier'), choices = Identifier.choices, max_length = 55, default = Identifier.NONE.value)
    runningstatus = models.CharField(_('Running Status'), choices = RunningStatus.choices, max_length = 55, null=True)
    type          = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Type"), on_delete = models.RESTRICT, null = True, blank = True, related_name='asset_types')
    client        = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete = models.RESTRICT, null = True, blank = True, related_name='asset_clients')
    bu            = models.ForeignKey("onboarding.Bt", verbose_name = _("Site"), on_delete = models.RESTRICT, null = True, blank = True, related_name='asset_bus')
    category      = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Category"), null = True, blank = True, on_delete = models.RESTRICT, related_name='asset_categories')
    subcategory   = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Sub Category"), null = True, blank = True, on_delete = models.RESTRICT, related_name='asset_subcategories')
    brand         = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Brand"), null = True, blank = True, on_delete = models.RESTRICT, related_name='asset_brands')
    unit          = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Unit"), null = True, blank = True, on_delete = models.RESTRICT, related_name='asset_units')
    capacity      = models.DecimalField(_("Capacity"), default = 0.0, max_digits = 18, decimal_places = 2)
    servprov      = models.ForeignKey("onboarding.Bt", verbose_name = _( "Client"), on_delete = models.RESTRICT, null = True, related_name='asset_serv_providers')
    location      = models.ForeignKey("activity.Location", verbose_name=_("Location"), on_delete=models.RESTRICT, null=True, blank=True)
    asset_json    = models.JSONField( encoder = DjangoJSONEncoder, blank = True, null = True, default = asset_json)

    objects = AssetManager()

    class Meta(BaseModel.Meta):
        db_table            = 'asset'
        verbose_name        = 'Asset'
        verbose_name_plural = 'Assets'
        constraints         = [
            models.UniqueConstraint(
                fields = ['assetcode', 'bu', 'client'],
                name='assetcode_client_uk'
            ),
        ]
        
                

    def __str__(self):
        return f'{self.assetname} ({self.assetcode})'

        
class AssetLog(models.Model):
    uuid        = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    oldstatus   = models.CharField(_("Old Status"), max_length=50, null=True)
    newstatus   = models.CharField(_("New Status"), max_length=50)
    asset       = models.ForeignKey("activity.Asset", verbose_name=_("Asset"), on_delete=models.RESTRICT)
    people      = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("People"), on_delete=models.RESTRICT, null=True)
    bu          = models.ForeignKey("onboarding.Bt", verbose_name=_("Bu"), on_delete=models.RESTRICT, null=True)
    client      = models.ForeignKey("onboarding.Bt", verbose_name=_("Client"), on_delete=models.CASCADE, related_name='assetlog_client', null=True)
    cdtz        = models.DateTimeField(_("Created On"), null=True)
    gpslocation = PointField(_('GPS Location'), null = True, geography = True, srid = 4326, blank = True)
    ctzoffset   = models.IntegerField(_("TimeZone"), default=-1)
    
    objects = AssetLogManager()
    
    class Meta:
        db_table = 'assetlog'

    def __str__(self):
        return f'{self.oldstatus} - {self.newstatus}'
    
  