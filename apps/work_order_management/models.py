from django.db import models
from django.forms.models import model_to_dict

# Create your models here.
import uuid
from apps.peoples.models import BaseModel
from django.contrib.gis.db.models import PointField
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.postgres.fields import ArrayField
from apps.tenants.models import TenantAwareModel
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from .managers import VendorManager, WorkOrderManager, WOMDetailsManager, ApproverManager



def geojson():
    return {
        'gpslocation':""
    }
    
def other_data():
    return {
        'token':None,
        'created_at':None,
        'token_expiration':5, #min
        'reply_from_vendor':"",
        'wp_seqno':0,
        'wp_approvers':[],
        'wp_verifiers':[],
        'section_weightage':0,
        'overall_score':0,
        'remarks':"",
        "uptime_score":0,
    }
    
def wo_history_json():
    return {
        "wo_history":[],
        "wp_history":[]
    }

class Wom(BaseModel, TenantAwareModel):
    class Workstatus(models.TextChoices):
        ASSIGNED   = ('ASSIGNED', 'Assigned')
        REASSIGNED   = ('RE_ASSIGNED', 'Re-Assigned')
        COMPLETED  = ('COMPLETED', 'Completed')
        INPROGRESS = ('INPROGRESS', 'Inprogress')
        CANCELLED  = ('CANCELLED', 'Cancelled')
        CLOSED  = ('CLOSED', 'Closed')
        
    class WorkPermitStatus(models.TextChoices):
        '''
        if value is NOT_REQURED it is work order
        '''
        NOTNEED   = ('NOT_REQUIRED', 'Not Required')
        APPROVED  = ('APPROVED', 'Approved')
        REJECTED = ('REJECTED', 'Rejected')
        PENDING  = ('PENDING', 'Pending')


    class WorkPermitVerifierStatus(models.TextChoices):
        NOTNEED   = ('NOT_REQUIRED', 'Not Required')
        APPROVED  = ('APPROVED', 'Approved')
        REJECTED = ('REJECTED', 'Rejected')
        PENDING  = ('PENDING', 'Pending')
        
    class Priority(models.TextChoices):
        HIGH   = ('HIGH', 'High')
        LOW    = ('LOW', 'Low')
        MEDIUM = ('MEDIUM', 'Medium')

    class Identifier(models.TextChoices):
        WO = ('WO', 'Work Order')
        WP = ('WP', 'Work Permit')
        SLA = ('SLA', 'Service Level Agreement')

    
    uuid            = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    description     = models.CharField(_("Job Description"), max_length = 200)
    plandatetime    = models.DateTimeField(_("Plan date time"), auto_now = False, auto_now_add = False, null=True)
    expirydatetime  = models.DateTimeField(_("Expiry date time"), auto_now = False, auto_now_add = False, null=True)
    starttime       = models.DateTimeField( _("Start time"), auto_now = False, auto_now_add = False, null = True)
    endtime         = models.DateTimeField(_("Start time"), auto_now = False, auto_now_add = False, null = True)
    gpslocation     = PointField(_('GPS Location'),null = True, blank=True, geography = True, srid = 4326)
    asset           = models.ForeignKey("activity.Asset", verbose_name = _("Asset"), on_delete= models.RESTRICT, null = True, blank = True, related_name='wo_assets')
    location        = models.ForeignKey('activity.Location', verbose_name=_('Location'), on_delete=models.RESTRICT, null=True, blank=True)
    workstatus      = models.CharField('Job Status', choices = Workstatus.choices, default=Workstatus.ASSIGNED,  max_length = 60, null = True)
    seqno           = models.SmallIntegerField(_("Serial No."), null=True)
    approvers       = ArrayField(models.CharField(max_length = 100, blank = True), null = True, blank = True, verbose_name= _("Approvers"))
    verifiers       = ArrayField(models.CharField(max_length = 100, blank = True), null = True, blank = True, verbose_name= _("Verifiers"))
    workpermit      = models.CharField(_('Work Permit'), choices=WorkPermitStatus.choices, default=WorkPermitStatus.NOTNEED, max_length=35)
    verifiers_status= models.CharField(_('Verifier Status'),max_length =  50, choices=WorkPermitVerifierStatus.choices,default=WorkPermitVerifierStatus.PENDING)
    priority        = models.CharField(_("Priority"), max_length = 50, choices = Priority.choices,default=Priority.LOW)
    qset            = models.ForeignKey("activity.QuestionSet", verbose_name = _("QuestionSet"), on_delete  = models.RESTRICT, null = True, blank = True)
    vendor          = models.ForeignKey('Vendor', null=True, blank=False, on_delete=models.RESTRICT, verbose_name='Vendor')
    performedby     = models.CharField(max_length=55, verbose_name='Performed By', )
    parent          = models.ForeignKey("self", verbose_name = _("Belongs to"),  on_delete  = models.RESTRICT,  null = True, blank = True)
    alerts          = models.BooleanField(_("Alerts"), default = False, null = True)
    client          = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete= models.RESTRICT, null = True, blank = True, related_name='wo_clients')
    bu              = models.ForeignKey("onboarding.Bt", verbose_name = _("Site"), on_delete = models.RESTRICT, null = True, blank = True, related_name='wo_bus')
    ticketcategory  = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Notify Category"), null= True, blank = True, on_delete = models.RESTRICT)
    ismailsent      = models.BooleanField(_('Mail Sent'), default= False)
    isdenied        = models.BooleanField(_('Denied'), default= False)
    geojson         = models.JSONField(verbose_name=_('Geo Json'), default=geojson, null=True)
    other_data      = models.JSONField(verbose_name=_('Other Data'), default=other_data, null=True)
    attachmentcount = models.IntegerField(_('Attachment Count'), default = 0)
    categories      = ArrayField(models.CharField(max_length = 50, blank = True, default=""), default = list)
    wo_history      = models.JSONField(encoder=DjangoJSONEncoder, default=wo_history_json)
    identifier      = models.CharField(_("Identifier"), max_length=50, choices=Identifier.choices, null=True, blank=True)
    remarks         = models.JSONField(_("Remarks"),blank=True,null=True)
    objects = WorkOrderManager()
    
    def add_history(self):
        self.wo_history['wo_history'].append(
            model_to_dict(self, exclude=['wo_history', 'workpermit', 'gpslocation'])
        )
        self.save()
    
    
    class Meta(BaseModel.Meta):
        db_table = "wom"
        verbose_name = "work order management"
        constraints         = [
            models.UniqueConstraint(
                fields = ['qset', 'client', 'id'],
                name='qset_client'
            ),
        ]



class Vendor(BaseModel, TenantAwareModel):
    uuid        = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    code        = models.CharField(_("Code"), max_length=50, null=True, blank=False)
    name        = models.CharField(_('Name'), max_length=255, null=True, blank=False)
    type        = models.ForeignKey("onboarding.TypeAssist", verbose_name=_("Type"), null=True, on_delete=models.CASCADE)
    address     = models.TextField(max_length=500, verbose_name='Address', blank=True, null= True)
    gpslocation = PointField(_('GPS Location'),null = True, blank=True, geography = True, srid = 4326)
    enable      = models.BooleanField(_("Enable"), default=True)
    mobno       = models.CharField(_("Mob No"), max_length=15)
    email       = models.CharField(_('Email'), max_length=100)
    client      = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete= models.RESTRICT, null = True, blank = True, related_name='vendor_clients')
    bu          = models.ForeignKey("onboarding.Bt", verbose_name = _("Site"), on_delete = models.RESTRICT, null = True, blank = True, related_name='vendor_bus')
    show_to_all_sites = models.BooleanField(_("Applicable to all sites"), default=False)
    description = models.TextField(_("Description"), max_length=500, null=True, blank=True)
    
    objects = VendorManager()
    
    class Meta(BaseModel.Meta):
        db_table = "vendor"
        verbose_name = "vendor company"
        constraints         = [
            models.UniqueConstraint(
                fields = ['code', 'client'],
                name='code_client'
            ),
        ]
    
    def __str__(self) -> str:
        return f'{self.name} ({self.code}{" - " + self.type.taname + ")" if self.type else ")"}'

        


class WomDetails(BaseModel, TenantAwareModel):
    class AnswerType(models.TextChoices):
        CHECKBOX    = ('CHECKBOX', 'Checkbox')
        DATE        = ('DATE', 'Date')
        DROPDOWN    = ('DROPDOWN', 'Dropdown')
        EMAILID     = ("EMAILID", "Email Id")
        MULTILINE   = ("MULTILINE", "Multiline")
        NUMERIC     = ("NUMERIC", "Numeric")
        SIGNATURE   = ("SIGNATURE", "Signature")
        SINGLELINE  = ("SINGLELINE", "Single Line")
        TIME        = ("TIME", "Time")
        RATING      = ("RATING", "Rating")
        BACKCAMERA  = ("BACKCAMERA", "Back Camera")
        FRONTCAMERA = ("FRONTCAMERA", "Front Camera")
        PEOPLELIST  = ("PEOPLELIST", "People List")
        SITELIST    = ("SITELIST", "Site List")
        NONE        = ("NONE", "NONE")
        MULTISELECT = ("MULTISELECT", "Multi Select")
    
    class AvptType(models.TextChoices):
        BACKCAMPIC    = "BACKCAMPIC"   , _('Back Camera Pic')
        FRONTCAMPIC        = "FRONTCAMPIC"       , _('Front Camera Pic')
        AUDIO    = "AUDIO"   , _('Audio')
        VIDEO     = "VIDEO"    , _("Video")
        NONE = ("NONE", "NONE")
    
    uuid            = models.UUIDField(unique=True, editable=False, blank=True, default=uuid.uuid4)
    seqno           = models.SmallIntegerField(_('SL #'))
    question        = models.ForeignKey("activity.Question", verbose_name=_(""), on_delete=models.RESTRICT)
    answertype      = models.CharField(_("Answer Type"), max_length=50, choices=AnswerType.choices, null=True)
    qset            = models.ForeignKey("activity.QuestionSet", on_delete=models.RESTRICT, null=True, blank=True, related_name='qset_answers')
    answer          = models.CharField(_("Answer"), max_length = 250, default="", null = True)
    isavpt          = models.BooleanField(_("Attachement Required"), default = False)
    avpttype        = models.CharField(_("Attachment Type"), max_length = 50, choices = AvptType.choices, null=True, blank=True)
    options         = models.CharField( _("Option"), max_length = 2000, null = True, blank = True)
    min             = models.DecimalField(_("Min"), max_digits = 18,  decimal_places = 4, null = True)
    max             = models.DecimalField(_("Max"), max_digits = 18, decimal_places = 4, null = True)
    alerton         = models.CharField( _("Alert On"), null = True, blank = True, max_length = 50)
    ismandatory     = models.BooleanField(_("Mandatory"), default = True)
    wom             = models.ForeignKey(Wom, verbose_name = _( "Jobneed"), null = True, blank = True, on_delete = models.RESTRICT)
    alerts          = models.BooleanField(_("Alerts"), default = False)
    attachmentcount = models.IntegerField(_('Attachment count'), default = 0)

    objects = WOMDetailsManager()
    class Meta(BaseModel.Meta):
        db_table = 'womdetails'
        verbose_name = 'Wom Details'
        constraints = [
            models.UniqueConstraint(
                fields = ['question', 'wom'],
                name="question_client"
            )
        ]
        
        
class Approver(BaseModel):
    class Identifier(models.TextChoices):
        APPROVER = ("APPROVER","Approver")
        VERIFIER = ("VERIFIER","Verifier")

    approverfor = ArrayField(models.CharField(_("Approver/Verifier For"),max_length = 50, blank = True), null = True, blank = True)
    sites       = ArrayField(models.CharField(max_length = 50, blank = True), null = True, blank = True, verbose_name= _("Sites"))
    forallsites = models.BooleanField(_("For all sites"), default=True)
    people      = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("Approver"), on_delete=models.RESTRICT, null=True)
    bu          = models.ForeignKey("onboarding.Bt", verbose_name=_(""), on_delete=models.RESTRICT, null=True)
    client      = models.ForeignKey('onboarding.Bt', on_delete=models.RESTRICT, null=True, related_name='approver_clients')
    identifier  = models.CharField(_("Approver/Verifier"),choices=Identifier.choices,max_length=250,null=True,blank=True)
    
    objects     = ApproverManager()
    
    
    class Meta(BaseModel.Meta):
        db_table = 'approver'
        verbose_name = 'approver'
        constraints = [
            models.UniqueConstraint(
                fields=['people', 'approverfor', 'sites'],
                name = 'people_approverfor_forallsites_sites_uk'
            )
        ]