import uuid
from django.utils import timezone
from django.contrib.gis.db.models import PointField
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.activity.managers.attachment_manager import AttachmentManager
from apps.peoples.models import BaseModel
from apps.tenants.models import TenantAwareModel



class Attachment(BaseModel, TenantAwareModel):
    class AttachmentType(models.TextChoices):
        NONE  = ('NONE', 'NONE')
        ATMT  = ("ATTACHMENT", "Attachment")
        REPLY = ("REPLY", "Reply")
        SIGN  = ("SIGN",  "SIGN")
        METERREADING  = ("METERREADING",  "Meter Reading")
        LOGFILES  = ("LOGFILES",  "Log Files")

    uuid           = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    filepath       = models.CharField(max_length = 100, null = False, blank = False,default = "youtility4_media")
    filename       = models.ImageField(null = False, blank = False,default = "default.jpg")
    ownername      = models.ForeignKey("onboarding.Typeassist", on_delete = models.RESTRICT, null = False, blank = False,default = 1)
    owner          = models.CharField(null= False, max_length = 255,default="None")
    bu             = models.ForeignKey("onboarding.Bt", null = True,blank = False, on_delete = models.RESTRICT)
    datetime       = models.DateTimeField(editable = True, default = timezone.now)
    attachmenttype = models.CharField(choices = AttachmentType.choices, max_length = 55, default = AttachmentType.NONE.value)
    gpslocation    = PointField(_('GPS Location'),null = False, blank=False, geography = True, srid = 4326,default = "POINT(0.0 0.0)")
    size           = models.IntegerField(null=True)
    

    objects = AttachmentManager()
    class Meta(BaseModel.Meta):
        db_table = 'attachment'
        get_latest_by = ["mdtz", 'cdtz']

    def __str__(self):
        return self.filename.name
