import uuid
from django.conf import settings
from django.contrib.gis.db.models import LineStringField, PointField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.activity.managers.job_manager import JobManager,JobneedDetailsManager,JobneedManager
from apps.peoples.models import BaseModel
from apps.tenants.models import TenantAwareModel
from apps.core import utils
from apps.activity.models.question_model import QuestionSet



def other_info():
    return {
        "tour_frequency": 1,
        "is_randomized": False,
        "distance": None,
        "breaktime": 0,
        "deviation": False,
        "ticket_generated": False,
        "email_sent": False,
        "autoclosed_by_server": False,
        "acknowledged_by": "",
        "isAcknowledged": False,
        "istimebound": True,
        "isdynamic": False,
    }


def geojson_jobnjobneed():
    return {"gpslocation": ""}

class Job(BaseModel, TenantAwareModel):
    class Identifier(models.TextChoices):
        TASK             = ('TASK', 'Task')
        TICKET           = ('TICKET', 'Ticket')
        INTERNALTOUR     = ('INTERNALTOUR', 'Internal Tour')
        EXTERNALTOUR     = ('EXTERNALTOUR', 'External Tour')
        PPM              = ('PPM', 'PPM')
        OTHER            = ('OTHER', 'Other')
        SITEREPORT       = ("SITEREPORT", "Site Report")
        INCIDENTREPORT   = ('INCIDENTREPORT', "Incident Report")
        ASSETLOG         = ("ASSETLOG",	"Asset Log")
        ASSETMAINTENANCE = ("ASSETMAINTENANCE",	"Asset Maintenance")
        GEOFENCE         = ('GEOFENCE', 'Geofence')
    
    class Priority(models.TextChoices):
        HIGH   = "HIGH" , _('High')
        LOW    = "LOW"  , _('Low')
        MEDIUM = "MEDIUM", _('Medium')

    class Scantype(models.TextChoices):
        QR      = "QR"     , _('QR')
        NFC     = "NFC"    , _('NFC')
        SKIP    = "SKIP"   , _('Skip')
        ENTERED = "ENTERED", _('Entered')

    class Frequency(models.TextChoices):
        NONE        = "NONE"       , _('None')
        DAILY       = "DAILY"      , _("Daily")
        WEEKLY      = "WEEKLY"     , _("Weekly")
        MONTHLY     = "MONTHLY"    , _("Monthly")
        BIMONTHLY   = "BIMONTHLY"  , _("Bimonthly")
        QUARTERLY   = "QUARTERLY"  , _("Quarterly")
        HALFYEARLY  = "HALFYEARLY" , _("Half Yearly")
        YEARLY      = "YEARLY"     , _("Yearly")
        FORTNIGHTLY = "FORTNIGHTLY", _("Fort Nightly")
    
    # id          = models.BigIntegerField(_("Job Id"), primary_key = True)
    jobname         = models.CharField(_("Name"), max_length = 200)
    jobdesc         = models.CharField(_("Description"), max_length = 500)
    fromdate        = models.DateTimeField( _("From date"), auto_now = False, auto_now_add = False)
    uptodate        = models.DateTimeField( _("To date"), auto_now = False, auto_now_add = False)
    cron            = models.CharField(_("Cron Exp."), max_length = 200, default='* * * * *')
    identifier      = models.CharField(_("Job Type"), max_length = 100, choices = Identifier.choices, null = True)
    planduration    = models.IntegerField(_("Plan duration (min)"))
    gracetime       = models.IntegerField(_("Grace Time"))
    expirytime      = models.IntegerField(_("Expiry Time"))
    lastgeneratedon = models.DateTimeField(_("Last generatedon"), auto_now = False, auto_now_add = True)
    asset           = models.ForeignKey("activity.Asset", verbose_name = _("Asset"), on_delete = models.RESTRICT, null = True, blank = True)
    priority        = models.CharField(_("Priority"), max_length = 100, choices = Priority.choices)
    qset            = models.ForeignKey("activity.QuestionSet", verbose_name = _("QuestionSet"), on_delete = models.RESTRICT, null = True, blank = True)
    people          = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name = _( "Aggresive auto-assign to People"), on_delete = models.RESTRICT, null = True, blank = True, related_name='job_aaatops')
    pgroup          = models.ForeignKey("peoples.Pgroup", verbose_name = _("People Group"), on_delete = models.RESTRICT, null = True, blank = True, related_name='job_pgroup')
    sgroup          = models.ForeignKey("peoples.Pgroup", verbose_name = _("Site Group"), on_delete= models.RESTRICT,  null = True, blank = True, related_name='job_sgroup')
    geofence        = models.ForeignKey("onboarding.GeofenceMaster", verbose_name = _("Geofence"), on_delete = models.RESTRICT, null = True, blank = True)
    parent          = models.ForeignKey("self", verbose_name = _("Belongs to"), on_delete = models.RESTRICT, null = True, blank = True)
    seqno           = models.SmallIntegerField(_("Serial No."))
    client          = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete = models.RESTRICT, related_name='job_clients', null = True, blank = True)
    bu              = models.ForeignKey("onboarding.Bt", verbose_name = _("Site"), on_delete = models.RESTRICT, related_name='job_bus', null = True, blank = True)
    shift           = models.ForeignKey("onboarding.Shift", verbose_name = _("Shift"), on_delete = models.RESTRICT, null = True, related_name="job_shifts")
    starttime       = models.TimeField(_("Start time"), auto_now = False, auto_now_add = False, null = True)
    endtime         = models.TimeField(_("End time"), auto_now = False, auto_now_add = False, null = True)
    ticketcategory  = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Notify Category"), on_delete = models.RESTRICT, null = True, blank = True, related_name="job_tktcategories")
    scantype        = models.CharField(_("Scan Type"), max_length = 50, choices = Scantype.choices)
    frequency       = models.CharField(verbose_name = _("Frequency type"), null = True, max_length = 55, choices = Frequency.choices, default = Frequency.NONE.value)
    other_info      = models.JSONField(_("Other info"), default = other_info, blank = True, encoder = DjangoJSONEncoder)
    geojson         = models.JSONField(default = geojson_jobnjobneed, blank = True, null=True, encoder = DjangoJSONEncoder)
    enable          = models.BooleanField(_("Enable"), default = True)

    objects = JobManager()

    class Meta(BaseModel.Meta):
        db_table            = 'job'
        verbose_name        = 'Job'
        verbose_name_plural = 'Jobs'
        constraints         = [
            models.UniqueConstraint(
                fields=['jobname', 'asset',
                        'qset', 'parent', 'identifier', 'client'],
                name='jobname_asset_qset_id_parent_identifier_client_uk'
            ),
            models.CheckConstraint(
                condition = models.Q(gracetime__gte = 0),
                name='gracetime_gte_0_ck'
            ),
            models.CheckConstraint(
                condition = models.Q(planduration__gte = 0),
                name='planduration_gte_0_ck'
            ),
            models.CheckConstraint(
                condition = models.Q(expirytime__gte = 0),
                name='expirytime_gte_0_ck'
            )
        ]

    def __str__(self):
        return self.jobname

class Jobneed(BaseModel, TenantAwareModel):
    class Priority(models.TextChoices):
        HIGH   = ('HIGH', 'High')
        LOW    = ('LOW', 'Low')
        MEDIUM = ('MEDIUM', 'Medium')

    class Identifier(models.TextChoices):
        TASK             = ('TASK', 'Task')
        TICKET           = ('TICKET', 'Ticket')
        INTERNALTOUR     = ('INTERNALTOUR', 'Internal Tour')
        EXTERNALTOUR     = ('EXTERNALTOUR', 'External Tour')
        PPM              = ('PPM', 'PPM')
        OTHER            = ('OTHER', 'Other')
        SITEREPORT       = ("SITEREPORT", "Site Report")
        INCIDENTREPORT   = ('INCIDENTREPORT', "Incident Report")
        ASSETLOG          = ("ASSETLOG",	"Asset Log")
        ASSETAUDIT        = ("ASSETAUDIT",	"Asset Audit")
        ASSETMAINTENANCE = ("ASSETMAINTENANCE",	"Asset Maintenance")
        POSTING_ORDER    = ("POSTING_ORDER", "Posting Order")

    class Scantype(models.TextChoices):
        NONE    = ('NONE', 'None')
        QR      = ('QR', 'QR')
        NFC     = ('NFC', 'NFC')
        SKIP    = ('SKIP', 'Skip')
        ENTERED = ('ENTERED', 'Entered')

    class JobStatus(models.TextChoices):
        ASSIGNED           = ('ASSIGNED', 'Assigned')
        AUTOCLOSED         = ('AUTOCLOSED', 'Auto Closed')
        COMPLETED          = ('COMPLETED', 'Completed')
        INPROGRESS         = ('INPROGRESS', 'Inprogress')
        PARTIALLYCOMPLETED = ('PARTIALLYCOMPLETED', 'Partially Completed')
        MAINTENANCE        = ("MAINTENANCE", "Maintenance")
        STANDBY            = ("STANDBY", "Standby")
        WORKING            = ("WORKING", "Working")
        

    class JobType(models.TextChoices):
        SCHEDULE = ('SCHEDULE', 'Schedule')
        ADHOC    = ('ADHOC', 'Adhoc')


    class Frequency(models.TextChoices):
        NONE        = ('NONE', 'None')
        DAILY       = ("DAILY", "Daily")
        WEEKLY      = ("WEEKLY", "Weekly")
        MONTHLY     = ("MONTHLY", "Monthly")
        BIMONTHLY   = ("BIMONTHLY", "Bimonthly")
        QUARTERLY   = ("QUARTERLY", "Quarterly")
        HALFYEARLY  = ("HALFYEARLY", "Half Yearly")
        YEARLY      = ("YEARLY", "Yearly")
        FORTNIGHTLY = ("FORTNIGHTLY", "Fort Nightly")

    uuid             = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    jobdesc          = models.CharField(_("Job Description"), max_length = 200)
    plandatetime     = models.DateTimeField(_("Plan date time"), auto_now = False, auto_now_add = False, null=True)
    expirydatetime   = models.DateTimeField(_("Expiry date time"), auto_now = False, auto_now_add = False, null=True)
    gracetime        = models.IntegerField(_("Grace time"))
    receivedonserver = models.DateTimeField(_("Recived on server"), auto_now = False, auto_now_add = True)
    starttime        = models.DateTimeField( _("Start time"), auto_now = False, auto_now_add = False, null = True)
    endtime          = models.DateTimeField(_("Start time"), auto_now = False, auto_now_add = False, null = True)
    gpslocation      = PointField(_('GPS Location'),null = True, blank=True, geography = True, srid = 4326)
    journeypath      = LineStringField(geography = True, null = True, blank=True)
    remarks          = models.TextField(_("Remark"), null = True, blank = True)
    remarkstype     = models.ForeignKey("onboarding.TypeAssist", on_delete=models.RESTRICT, null=True, blank=True, related_name='remark_types')
    asset            = models.ForeignKey("activity.Asset", verbose_name = _("Asset"), on_delete= models.RESTRICT, null = True, blank = True, related_name='jobneed_assets')
    frequency        = models.CharField(verbose_name = _("Frequency type"), null = True, max_length = 55, choices = Frequency.choices, default = Frequency.NONE.value)
    job              = models.ForeignKey("activity.Job", verbose_name = _("Job"), on_delete  = models.RESTRICT, null = True, blank = True, related_name='jobs')
    jobstatus        = models.CharField('Job Status', choices = JobStatus.choices, max_length = 60, null = True)
    jobtype          = models.CharField(_("Job Type"), max_length = 50, choices = JobType.choices, null = True)
    performedby      = models.ForeignKey(settings.AUTH_USER_MODEL,verbose_name = _("Performed by"), on_delete = models.RESTRICT, null = True, blank = True, related_name='jobneed_performedby')
    priority         = models.CharField(_("Priority"), max_length = 50, choices = Priority.choices)
    qset             = models.ForeignKey("activity.QuestionSet", verbose_name = _("QuestionSet"), on_delete  = models.RESTRICT, null = True, blank = True)
    scantype         = models.CharField(_("Scan type"), max_length = 50, choices = Scantype.choices, default = Scantype.NONE.value)
    people           = models.ForeignKey(settings.AUTH_USER_MODEL,verbose_name = _("People"), on_delete = models.RESTRICT,  null = True, blank = True)
    pgroup           = models.ForeignKey("peoples.Pgroup", verbose_name = _("People Group"), on_delete= models.RESTRICT,  null = True, blank = True, related_name='jobneed_pgroup')
    sgroup           = models.ForeignKey("peoples.Pgroup", verbose_name = _("Site Group"), on_delete= models.RESTRICT,  null = True, blank = True, related_name='jobneed_sgroup')
    identifier       = models.CharField(_("Jobneed Type"), max_length = 50, choices = Identifier.choices, null = True)
    parent           = models.ForeignKey("self", verbose_name = _("Belongs to"),  on_delete  = models.RESTRICT,  null = True, blank = True)
    alerts           = models.BooleanField(_("Alerts"), default = False, null = True)
    seqno            = models.SmallIntegerField(_("Sl No."))
    client           = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete= models.RESTRICT, null = True, blank = True, related_name='jobneed_clients')
    bu               = models.ForeignKey("onboarding.Bt", verbose_name = _("Site"), on_delete = models.RESTRICT, null = True, blank = True, related_name='jobneedf_bus')
    ticketcategory   = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Notify Category"), null= True, blank = True, on_delete = models.RESTRICT)
    ticket           = models.ForeignKey("y_helpdesk.Ticket", verbose_name=_("Ticket"), on_delete=models.RESTRICT, null=True, blank=True, related_name='jobneed_ticket')
    othersite        = models.CharField(_("Other Site"), max_length = 100, default = None, null = True)
    multifactor      = models.DecimalField(_("Multiplication Factor"), default = 1, max_digits = 10, decimal_places = 6)
    raisedtktflag    = models.BooleanField(_("RaiseTicketFlag"), default = False, null = True)
    ismailsent       = models.BooleanField(_('Mail Sent'), default= False)
    attachmentcount  = models.IntegerField(_('Attachment Count'), default = 0)
    other_info       = models.JSONField(_("Other info"), default = other_info, blank = True, encoder = DjangoJSONEncoder)
    geojson          = models.JSONField(default = geojson_jobnjobneed, blank = True,null=True, encoder = DjangoJSONEncoder)
    deviation        = models.BooleanField(_("Deviation"), default = False, null=True)


    objects = JobneedManager()

    class Meta(BaseModel.Meta):
        db_table            = 'jobneed'
        verbose_name        = 'Jobneed'
        verbose_name_plural = 'Jobneeds'
        constraints         = [
            models.CheckConstraint(
                condition = models.Q(gracetime__gte = 0),
                name='jobneed_gracetime_gte_0_ck'
            ),
        ]
        
    def save(self, *args, **kwargs):
        if self.ticket_id is None:
            self.ticket_id = utils.get_or_create_none_ticket().id
        super().save(*args, **kwargs)


class JobneedDetails(BaseModel, TenantAwareModel):
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
        METERREADING = "METERREADING", _("Meter Reading")
        MULTISELECT  = "MULTISELECT", _("Multi Select")
        
    
    class AvptType(models.TextChoices):
        BACKCAMPIC    = "BACKCAMPIC"   , _('Back Camera Pic')
        FRONTCAMPIC        = "FRONTCAMPIC"       , _('Front Camera Pic')
        AUDIO    = "AUDIO"   , _('Audio')
        VIDEO     = "VIDEO"    , _("Video")
        NONE = ("NONE", "NONE")

    uuid            = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    seqno           = models.SmallIntegerField(_("SL No."))
    question        = models.ForeignKey("activity.Question", verbose_name = _("Question"),  null = True, blank = True, on_delete = models.RESTRICT)
    answertype      = models.CharField(_("Answer Type"), max_length = 50, choices = AnswerType.choices, null = True)
    answer          = models.CharField(_("Answer"), max_length = 250, default="", null = True)
    isavpt          = models.BooleanField(_("Attachement Required"), default = False)
    avpttype        = models.CharField(_("Attachment Type"), max_length = 50, choices = AvptType.choices, null=True, blank=True)
    options         = models.CharField( _("Option"), max_length = 2000, null = True, blank = True)
    min             = models.DecimalField(_("Min"), max_digits = 18,  decimal_places = 4, null = True)
    max             = models.DecimalField(_("Max"), max_digits = 18, decimal_places = 4, null = True)
    alerton         = models.CharField( _("Alert On"), null = True, blank = True, max_length = 300)
    qset            = models.ForeignKey(QuestionSet, verbose_name=('Question Set'), null=True, blank=True, on_delete=models.RESTRICT, related_name='questions_qset')
    ismandatory     = models.BooleanField(_("Mandatory"), default = True)
    jobneed         = models.ForeignKey("activity.Jobneed", verbose_name = _( "Jobneed"), null = True, blank = True, on_delete = models.RESTRICT)
    alerts          = models.BooleanField(_("Alerts"), default = False)
    attachmentcount = models.IntegerField(_('Attachment count'), default = 0)

    objects = JobneedDetailsManager()

    class Meta(BaseModel.Meta):
        db_table     = 'jobneeddetails'
        verbose_name = 'JobneedDetails'
