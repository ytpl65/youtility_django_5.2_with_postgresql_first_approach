from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.peoples.models import BaseModel
from django.conf import settings
from .managers import ReminderManager
# Create your models here.


class Reminder(BaseModel):
    class Priority(models.TextChoices):
        HIGH   = "HIGH" , _('High')
        LOW    = "LOW"  , _('Low')
        MEDIUM = "MEDIU", _('Medium')
        
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
    
    class StatusChoices(models.TextChoices):
        SUCCESS = "SUCCESS", _("Success")
        FAILED = 'FAILED', _('FAILED')
    
    description    = models.TextField(_('Description'), max_length=500)
    bu             = models.ForeignKey("onboarding.Bt", verbose_name=_("Site"), on_delete=models.RESTRICT, blank=True)
    asset          = models.ForeignKey("activity.Asset", verbose_name=_("Asset"), on_delete=models.RESTRICT, blank=True)
    qset           = models.ForeignKey("activity.Questionset", verbose_name=_("Question Set"), on_delete=models.RESTRICT, blank=True)
    people         = models.ForeignKey("peoples.People", verbose_name=_("People"), on_delete=models.RESTRICT, blank=True)
    group          = models.ForeignKey("peoples.Pgroup", verbose_name=_("Group"), on_delete=models.RESTRICT, blank=True)
    priority       = models.CharField(_("Priority"), max_length=50, choices=Priority.choices)
    reminderdate   = models.DateTimeField(_("Reminder Date"), null=True)
    reminderin     = models.CharField(_("Reminder In"), choices=Frequency.choices, max_length=20)
    reminderbefore = models.IntegerField(_("Reminder Before"))
    job            = models.ForeignKey("activity.Job", verbose_name=_("Job"), on_delete=models.RESTRICT, blank=True)
    jobneed        = models.ForeignKey("activity.Jobneed", verbose_name=_("Jobneed"), on_delete=models.RESTRICT, blank=True)
    plandatetime   = models.DateTimeField(_("Plan Datetime"), null=True)
    mailids        = models.TextField(_("Mail Ids"), max_length=500)
    status         = models.CharField(_("Status"), choices=StatusChoices.choices, max_length=50)
    
    
    objects = ReminderManager()

    class Meta(BaseModel.Meta):
        db_table            = 'reminder'
        verbose_name        = 'Reminder'
        verbose_name_plural = 'Reminders'
        
        

    def __str__(self):
        return f'{self.asset}'