from django.db import models
from apps.peoples.models import BaseModel
from apps.tenants.models import TenantAwareModel
from django.utils.translation import gettext_lazy as _
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.postgres.fields import ArrayField
from apps.activity.managers.question_manager import QuestionManager, QuestionSetManager, QsetBlngManager

class Question(BaseModel, TenantAwareModel):

    class AnswerType(models.TextChoices):
        CHECKBOX    = "CHECKBOX"   , _('Checkbox') 
        DATE        = "DATE"       , _('Date')
        DROPDOWN    = "DROPDOWN"   , _('Dropdown')
        EMAILID     = "EMAILID"    , _("Email Id")
        MULTILINE   = "MULTILINE"  , _("Multiline")
        NUMERIC     = "NUMERIC"    , _("Numeric")
        SIGNATURE   = "SIGNATURE"  , _("Signature")
        SINGLELINE  = "SINGLELINE" , _("Single Line")
        TIME        = "TIME"       , _("Time")
        RATING      = "RATING"     , _("Rating")
        PEOPLELIST  = "PEOPLELIST" , _("People List")
        SITELIST    = "SITELIST"   , _("Site List")
        METERREADING = "METERREADING", _("Meter Reading")
        MULTISELECT  = "MULTISELECT", _("Multi Select")
    
    class AvptType(models.TextChoices):
        NONE  = "NONE",  _('NONE')
        BACKCAMPIC  = "BACKCAMPIC",  _('Back Camera Pic')
        FRONTCAMPIC = "FRONTCAMPIC", _('Front Camera Pic')
        AUDIO       = "AUDIO",       _('Audio')
        VIDEO       = "VIDEO",       _("Video")
    
    quesname   = models.CharField(_("Name"), max_length = 500)
    options    = models.TextField(_('Options'), max_length = 2000, null = True)
    min        = models.DecimalField(_("Min"), null = True, blank = True, max_digits = 18, decimal_places = 2, default = 0.00)
    max        = models.DecimalField( _('Max'), null = True, blank = True, max_digits = 18, decimal_places = 2, default = 0.00)
    alerton    = models.CharField(_("Alert on"), max_length = 300, null = True)
    answertype = models.CharField(verbose_name = _("Type"), choices = AnswerType.choices, default="NUMERIC", max_length = 55)  # type in previous
    unit       = models.ForeignKey("onboarding.TypeAssist", verbose_name = _( "Unit"), on_delete = models.RESTRICT, related_name="unit_types", null = True, blank = True)
    client     = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete = models.RESTRICT, null = True, blank = True)
    isworkflow = models.BooleanField(_("WorkFlow"), default = False)
    enable     = models.BooleanField(_("Enable"), default = True)
    category   = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Category"), on_delete = models.RESTRICT, related_name='category_types', null = True, blank = True)
    avpttype   = models.CharField(_("Attachment Type"), max_length = 50, choices = AvptType.choices, null = True, blank = True)
    isavpt     = models.BooleanField(_("Attachment Required"), default = False)

    objects = QuestionManager()
    
    class Meta(BaseModel.Meta):
        db_table = 'question'
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'
        constraints = [models.UniqueConstraint(
            fields=['quesname', 'answertype', 'client'], name='ques_name_type_client_uk')]

    def __str__(self) -> str:
        return f"{self.quesname} | {self.answertype}"

def site_grp_includes():
    return {
        'sitegrp__id': ""  # save this variable as <sitegrp__id> eg: abcd__12
    }

def site_type_includes():
    return {
        'sitetype__id': ""  # save this variable as <sitetype__id> eg: abcd__12
    }

# will save on client level

class QuestionSet(BaseModel, TenantAwareModel):
    class Type(models.TextChoices):
        CHECKLIST                = "CHECKLIST",           _('Checklist')
        RPCHECKLIST              = "RPCHECKLIST",         _('RP Checklist')
        INCIDENTREPORTTEMPLATE   = "INCIDENTREPORT",      _('Incident Report')
        SITEREPORTTEMPLATE       = "SITEREPORT",          _('Site Report')
        WORKPERMITTEMPLATE       = "WORKPERMIT",          _('Work Permit')
        RETURNWORKPERMITTEMPLATE = "RETURN_WORK_PERMIT",  _('Return Work Permit')
        KPITEMPLATE              = "KPITEMPLATE",         _('Kpi')
        SCRAPPEDTEMPLATE         = "SCRAPPEDTEMPLATE",    _('Scrapped')
        ASSETAUDIT               = "ASSETAUDIT",          _('Asset Audit')
        ASSETMAINTENANCE         = "ASSETMAINTENANCE",    _('Asset Maintenance')
        WORKORDER                = "WORK_ORDER",          _('Work Order')
        SLA_TEMPLATE             = "SLA_TEMPLATE",        _('Service Level Agreement')
        POSTINGORDER             = "POSTING_ORDER",       _('Posting Order')

    qsetname           = models.CharField(_("QuestionSet Name"), max_length = 200)
    enable             = models.BooleanField(_("Enable"), default = True)
    assetincludes      = ArrayField(models.CharField(max_length = 100, blank = True), null = True, blank = True, verbose_name= _("Asset Includes"))
    buincludes         = ArrayField(models.CharField(max_length = 100, blank = True), null = True, blank = True, verbose_name= _("Bu Includes"))
    seqno              = models.SmallIntegerField(_("Sl No."), default = 1)
    parent             = models.ForeignKey("self", verbose_name = _("Belongs To"), on_delete = models.RESTRICT, null = True, blank = True)
    type               = models.CharField( _("Type"), choices = Type.choices, null = True, max_length = 50)
    bu                 = models.ForeignKey("onboarding.Bt", verbose_name = _("Site"), on_delete = models.RESTRICT, related_name='qset_bus', null = True, blank = True)
    client             = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete = models.RESTRICT, related_name='qset_clients', null = True, blank = True)
    site_grp_includes  = ArrayField(models.CharField(max_length = 100, blank = True), null = True, blank = True, verbose_name= _("Site Group Includes"))
    site_type_includes = ArrayField(models.CharField(max_length = 100, blank = True), null = True, blank = True, verbose_name= _("Site Type Includes"))
    show_to_all_sites = models.BooleanField(_("Applicable to all sites"), default=False)
    url                = models.CharField(_("Url"), max_length = 250, null = True, blank = True, default="NONE")

    objects = QuestionSetManager()

    class Meta(BaseModel.Meta):
        db_table            = 'questionset'
        verbose_name        = 'QuestionSet'
        verbose_name_plural = 'QuestionSets'
        constraints         = [
            models.UniqueConstraint(
                fields=['qsetname', 'parent', 'type', 'client', 'bu'],
                name='name_type_parent_type_client_bu_uk'
            ),
            models.CheckConstraint(
                condition = models.Q(seqno__gte = 0),
                name='slno_gte_0_ck')
        ]

    def __str__(self) -> str:
        return self.qsetname

def alertmails_sendto():
    return {
        "id__code": []
    }

class QuestionSetBelonging(BaseModel, TenantAwareModel):
    class AnswerType(models.TextChoices):
        CHECKBOX    = "CHECKBOX"   , _('Checkbox')
        DATE        = "DATE"       , _('Date')
        DROPDOWN    = "DROPDOWN"   , _('Dropdown')
        EMAILID     = "EMAILID"    , _("Email Id")
        MULTILINE   = "MULTILINE"  , _("Multiline")
        NUMERIC     = "NUMERIC"    , _("Numeric")
        SIGNATURE   = "SIGNATURE"  , _("Signature")
        SINGLELINE  = "SINGLELINE" , _("Single Line")
        TIME        = "TIME"       , _("Time")
        RATING      = "RATING"     , _("Rating")
        BACKCAMERA  = "BACKCAMERA" , _("Back Camera")
        FRONTCAMERA = "FRONTCAMERA", _("Front Camera")
        PEOPLELIST  = "PEOPLELIST" , _("People List")
        SITELIST    = "SITELIST"   , _("Site List")
        NONE        = ("NONE", "NONE")
        MULTISELECT  = "MULTISELECT", _("Multi Select")
        
    class AvptType(models.TextChoices):
        BACKCAMPIC  = "BACKCAMPIC",  _('Back Camera Pic')
        FRONTCAMPIC = "FRONTCAMPIC", _('Front Camera Pic')
        AUDIO       = "AUDIO",       _('Audio')
        VIDEO       = "VIDEO",       _("Video")
        NONE        = ("NONE", "NONE")

    # id               = models.BigIntegerField(_("QSB Id"), primary_key = True)
    ismandatory       = models.BooleanField(_("Mandatory"), default = True)
    isavpt            = models.BooleanField(_("Attachment Required"), default = False)
    seqno             = models.SmallIntegerField(_("Seq No."))
    qset              = models.ForeignKey("activity.QuestionSet", verbose_name = _("Question Set"), on_delete = models.RESTRICT, null = True, blank = True)
    question          = models.ForeignKey("activity.Question", verbose_name = _("Question"), null = True, blank = False,  on_delete = models.RESTRICT)
    answertype        = models.CharField(_("Question Type"), max_length = 50, choices = AnswerType.choices)
    avpttype        = models.CharField(_("Attachment Type"), max_length = 50, choices = AvptType.choices, null = True, blank = True)
    max               = models.DecimalField(_("Max"), null = True,blank=True, max_digits = 18, decimal_places = 2, default = 0.00)
    min               = models.DecimalField(_("Min"), null = True,blank=True, max_digits = 18, decimal_places = 2, default = 0.00)
    alerton           = models.CharField(_("Alert on"), null = True, blank = True, max_length = 300)
    options           = models.CharField(_("Option"), max_length = 2000, null = True, blank = True)
    client            = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete = models.RESTRICT, null = True, blank = True, related_name='qsetbelong_client')
    alertmails_sendto = models.JSONField( _("Alert mails send to"), encoder = DjangoJSONEncoder, default = alertmails_sendto)
    bu                = models.ForeignKey("onboarding.Bt", verbose_name = _("Site"), on_delete = models.RESTRICT, null = True, blank = True, related_name='qsetbelong_bu')
    buincludes        = ArrayField(models.CharField(max_length = 100, blank = True), null = True, blank = True, verbose_name= _("Bu Includes"))

    objects = QsetBlngManager()
    
    class Meta(BaseModel.Meta):
        db_table            = 'questionsetbelonging'
        verbose_name        = 'QuestionSetBelonging'
        verbose_name_plural = 'QuestionSetBelongings'
        constraints         = [
            models.UniqueConstraint(
                fields=['qset', 'question', 'client', 'bu'],
                name='qset_question_client_bu_uk'
            )
        ]

    def __str__(self) -> str:
        return self.answertype

