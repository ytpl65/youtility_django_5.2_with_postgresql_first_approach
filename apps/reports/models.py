from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import gettext_lazy as _
from apps.peoples.models import BaseModel
from django.contrib.postgres.fields import ArrayField

def now():
    return timezone.now().replace(microsecond = 0)

# Create your models here.
class ReportHistory(models.Model):
    class ExportType(models.TextChoices):
        D = ('DOWNLOAD', 'Download')
        E = ('EMAIL', 'Email')
        S = ('SCHEDULED', 'Scheduled')
    
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_(""), on_delete=models.RESTRICT)
    datetime    = models.DateTimeField(default= now)
    export_type = models.CharField(max_length=55, default=ExportType.D.value)
    report_name = models.CharField(max_length=100)
    params      = models.JSONField(encoder=DjangoJSONEncoder, null=True)
    bu          = models.ForeignKey('onboarding.Bt', null=True, on_delete=models.RESTRICT)
    client      = models.ForeignKey('onboarding.Bt', null=True, on_delete=models.RESTRICT, related_name='rh_clients')
    cdtz        = models.DateTimeField(_('cdtz'), default = now)
    mdtz        = models.DateTimeField(_('mdtz'), default = now)
    has_data    = models.BooleanField(_("Has Data in Report"), default=True)
    ctzoffset   = models.IntegerField(_("TimeZone"), default=-1)
    cc_mails    = models.TextField(max_length=250, null=True)
    to_mails    = models.TextField(max_length=250, null=True)
    email_body  = models.TextField(max_length=500, null=True)
    traceback   = models.TextField(null=True)
    
    class Meta:
        db_table = 'report_history'
    
    def __str__(self):
        return f'User: {self.user.peoplename} Report: {self.report_name}'
    


def report_params_json():
    return {'report_params':{}}

class ScheduleReport(BaseModel):
    REPORT_TEMPLATES = [
        ('', 'Select Report'),
        ('TASKSUMMARY', 'Task Summary'),
        ('TOURSUMMARY', 'Tour Summary'),
        ('LISTOFTASKS', 'List of Tasks'),
        ('LISTOFTOURS', 'List of Internal Tours'),
        ('PPMSUMMARY', 'PPM Summary'),
        ('LISTOFTICKETS', 'List of Tickets'),
        ('WORKORDERLIST', 'Work Order List'),
        ('SITEVISITREPORT','Site Visit Report'),
        ('SITEREPORT', 'Site Report'),
        ('PeopleQR', 'People-QR'),
        ('ASSETQR', 'Asset-QR'),
        ('CHECKPOINTQR', 'Checkpoint-QR'),
        ('ASSETWISETASKSTATUS','Assetwise Task Status'),
        ('DetailedTourSummary','Detailed Tour Summary'),
        ('STATICDETAILEDTOURSUMMARY','Static Detailed Tour Summary'),
        ('DYNAMICDETAILEDTOURSUMMARY','Dynamic Detailed Tour Summary'),
        ('DYNAMICTOURDETAILS','Dynamic Tour Details'),
        ('STATICTOURDETAILS','Static Tour Details'),
        ('RP_SITEVISITREPORT','RP Site Visit Report'),
        ('LOGSHEET','Log Sheet'),
        ('PEOPLEATTENDANCESUMMARY','People Attendance Summary')

        ]
    
    WORKINGDAYS = [
        ('5', 'Monday - Friday'),
        ('6', 'Monday - Saturday'),
    ]
    
    
    report_type     = models.CharField(_("Report Type"), max_length=50, choices=REPORT_TEMPLATES)
    filename        = models.CharField(max_length=200, null=True)
    report_name     = models.CharField(_("Report Name"), max_length=55)
    workingdays     = models.CharField(_("Working Days"), max_length=1, blank=True, null=True, choices=WORKINGDAYS)
    cron            = models.CharField(_("Scheduler"), max_length=50, default='* * * * *')
    report_sendtime = models.TimeField(_("Send Time"), auto_now=False, auto_now_add=False)
    cc              = ArrayField(models.CharField(max_length = 90, blank = True, null=True), null = True, blank = True, verbose_name= _("Email-CC"))
    to_addr         = ArrayField(models.CharField(max_length = 90, blank = True, null=True), null = True, blank = True, verbose_name= _("Email=TO"))
    enable          = models.BooleanField(_("Enable"), default=True)
    crontype        = models.CharField(_("Cron Type"), max_length=50, null=True, blank=True)
    fromdatetime    = models.DateTimeField(_("Last Generated On"), null=True)
    uptodatetime    = models.DateTimeField(_("Next Scheduled On"), null=True)
    lastgeneratedon = models.DateTimeField(_("Last Generated On"), null=True)
    report_params   = models.JSONField(null=True, blank=True, default=report_params_json)
    bu              = models.ForeignKey('onboarding.Bt', null=True, on_delete=models.RESTRICT, related_name='schd_sites')
    client          = models.ForeignKey('onboarding.Bt', null=True, on_delete=models.RESTRICT, related_name='schd_clients')
    
    
    class Meta(BaseModel.Meta):
        db_table = 'schedule_report'
        constraints = [
            models.UniqueConstraint(
                fields=['cron', 'report_type', 'bu', 'report_params'],
                name="cron_report_type_report_params_uk"
            ),
            models.UniqueConstraint(
                fields=['cron', 'report_type', 'bu', 'workingdays', 'report_params'],
                name="cron_report_type_workindays_report_params_uk"
            )
        ]

class GeneratePDF(BaseModel):
    class AdditionalFilter(models.TextChoices):
        CUSTOMER   = ('CUSTOMER', 'Customer')
        SITE       = ('SITE', 'Site')
        
    # class NumberOfPeriod(models.TextChoices):
    #     ONE        = ('ONE', 'One')
    #     MULTIPLE   = ('MULTIPLE', 'Multiple')
    
    class Company(models.TextChoices):
        SPS        = ('SPS', 'SPS')
        SFS        = ('SFS', 'SFS')
        TARGET     = ('TARGET', 'TARGET')
    
    class DocumentType(models.TextChoices):
        PF        = ('PF', 'PF')
        ESIC      = ('ESIC', 'ESIC')
        PAYROLL   = ('PAYROLL', 'PAYROLL')

    class FormType(models.TextChoices):
        NORMALFORM = ('NORMAL FORM', 'NORMAL FORM')
        FORM16 = ('FORM 16', 'FORM 16')

    document_type = models.CharField('Document Type', choices = DocumentType.choices, null=True, max_length = 60)    
    company = models.CharField('Company', choices = Company.choices, null=True, max_length = 60)
    additional_filter = models.CharField('Additional Filter', choices = AdditionalFilter.choices, max_length = 60)
    customer = models.CharField(max_length=255, null=True, blank=True, default=None)
    site = models.CharField(max_length=255, null=True, blank=True,default=None)
    # number_of_period = models.CharField('Number Of Period', choices = NumberOfPeriod.choices,  max_length = 60)
    period_from = models.CharField(max_length=255, null=True, default=None, blank=True)
    # period_to = models.CharField(max_length=255, null=True, default=None, blank=True)
    type_of_form = models.CharField('Type Of Form', choices = FormType.choices, null=True, max_length = 60)
    
    class Meta(BaseModel.Meta):
        db_table = 'generatepdf'
    
    @classmethod
    def get_solo(cls):
        """Get the single instance of the model, creating one if it doesn't exist."""
        obj, created = cls.objects.get_or_create(pk=1)  # Use a constant primary key
        return obj