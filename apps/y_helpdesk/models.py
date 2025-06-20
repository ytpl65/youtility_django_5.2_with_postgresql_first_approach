from apps.peoples.models import BaseModel, TenantAwareModel
from django.db import models
from .managers import TicketManager, ESCManager
from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict
import uuid
class TicketNumberField(models.AutoField):
    def get_next_value(self, model, created, value, using):
        if not created:
            return value
        if last_ticket := model.objects.order_by('-id').first():
            return 'T{:05d}'.format(last_ticket.id + 1)
        return 'T00001'



def ticket_defaults():
    #elements in ticket_history will be like this:
    #element: {"when":"", "who":"", "action":"", "details":"", "previous_state":""}
    return {"ticket_history":[]}

class Ticket(BaseModel, TenantAwareModel):
    class Priority(models.TextChoices):
        LOW    = ('LOW', 'Low')
        MEDIUM = ('MEDIUM', 'Medium')
        HIGH   = ('HIGH', 'High')

        
    class Identifier(models.TextChoices):
        REQUEST = ('REQUEST', 'Request')
        TICKET = ('TICKET', 'Ticket')

    class Status(models.TextChoices):
        NEW      = ('NEW', 'New')#ticket is created
        CANCEL   = ('CANCELLED', 'Cancel')#ticket is cancelled
        RESOLVED = ('RESOLVED', 'Resolved') #ticket is resolved 
        OPEN     = ('OPEN', 'Open') #tickte is opened
        ONHOLD = ('ONHOLD', 'On Hold') #ticket is opened but need more info before resolve
        CLOSED = ('CLOSED', 'Closed') #ticket is closed by the created user

    class TicketSource(models.TextChoices):
        SYSTEMGENERATED = ('SYSTEMGENERATED', 'New Generated')
        USERDEFINED     = ('USERDEFINED', 'User Defined')


    uuid             = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    ticketno         = models.CharField(unique=True, null=True, blank=False, max_length=200) 
    ticketdesc       = models.TextField()
    assignedtopeople = models.ForeignKey('peoples.People', null=True, blank=True, on_delete=models.RESTRICT, related_name="ticket_people")
    assignedtogroup  = models.ForeignKey('peoples.Pgroup', null=True, blank=True, on_delete=models.RESTRICT, related_name="ticket_grps")
    comments         = models.CharField(max_length=250, null=True)
    identifier       = models.CharField(_("Identifier"), choices=Identifier.choices,  max_length=50, default=Identifier.TICKET.value)
    bu               = models.ForeignKey("onboarding.Bt", null=True,blank=True, on_delete=models.RESTRICT)
    client           = models.ForeignKey("onboarding.Bt", null=True,blank=True, on_delete=models.RESTRICT, related_name='ticket_clients')
    priority         = models.CharField(_("Priority"), max_length=50, choices=Priority.choices, null=True, blank=True)
    ticketcategory   = models.ForeignKey('onboarding.TypeAssist', null=True, blank=True, related_name="ticketcategory_types", on_delete=models.RESTRICT)
    location         = models.ForeignKey('activity.Location', null=True, blank=True, on_delete=models.RESTRICT)
    asset            = models.ForeignKey('activity.Asset', null=True, blank=True, on_delete=models.RESTRICT)
    qset            = models.ForeignKey('activity.QuestionSet', null=True, blank=True, on_delete=models.RESTRICT)
    modifieddatetime = models.DateTimeField(default=timezone.now)
    level            = models.IntegerField(default=0)
    status           = models.CharField(_("Status"), max_length=50, choices=Status.choices,null=True, blank=True, default=Status.NEW.value)
    performedby      = models.ForeignKey('peoples.People', null=True, blank=True, on_delete=models.RESTRICT, related_name="ticket_performedby")
    ticketlog        = models.JSONField(null=True,  encoder=DjangoJSONEncoder, blank=True, default=ticket_defaults)
    events           = models.TextField(null=True, blank=True)
    isescalated      = models.BooleanField(default=False)
    ticketsource     = models.CharField(max_length=50, choices=TicketSource.choices, null=True, blank=True)
    attachmentcount  = models.IntegerField(null=True)

    objects = TicketManager()
    
    def add_history(self):
        self.ticketlog['ticket_history'].append(
            {'record': model_to_dict(self, exclude=['ticketlog', 'uuid', 'id', 'ctzoffset'])}) 
    
     
    def get_changed_keys(self, dict1, dict2):
        """
        This function takes two dictionaries as input and returns a list of keys 
        where the corresponding values have changed from the first dictionary to the second.
        """

        # Handle edge cases where either of the inputs is not a dictionary
        if not isinstance(dict1, dict) or not isinstance(dict2, dict):
            raise TypeError("Both arguments should be of dict type")

        return [key for key in dict1.keys() & dict2.keys() if dict1[key] != dict2[key]]
    
    class Meta(BaseModel.Meta):
        db_table      = 'ticket'
        get_latest_by = ["cdtz", 'mdtz']
        constraints         = [
            models.UniqueConstraint(
                fields=['bu', 'id', 'client'],
                name='bu_id_uk'
            )
        ]

    def __str__(self):
        return self.ticketdesc


class EscalationMatrix(BaseModel, TenantAwareModel):
    class Frequency(models.TextChoices):
        MINUTE = ('MINUTE', 'MINUTE')
        HOUR   = ('HOUR', 'HOUR')
        DAY    = ('DAY', 'DAY')
        WEEK   = ('WEEK', 'WEEK')
    

    # id               = models.BigIntegerField(primary_key = True)
    body               = models.CharField(max_length = 500, null = True)
    job                = models.ForeignKey("activity.Job", verbose_name=_("Job"),null=True, on_delete=models.RESTRICT)
    level              = models.IntegerField(null = True, blank = True)
    frequency          = models.CharField(max_length = 10, default='DAY', choices = Frequency.choices)
    frequencyvalue     = models.IntegerField(null = True, blank = True)
    assignedfor        = models.CharField(max_length = 50)
    assignedperson     = models.ForeignKey(settings.AUTH_USER_MODEL, null = True, blank = True, on_delete = models.RESTRICT, related_name="escalation_people")
    assignedgroup      = models.ForeignKey('peoples.Pgroup', null = True, blank = True, on_delete = models.RESTRICT, related_name="escalation_grps")
    bu                 = models.ForeignKey("onboarding.Bt", null = True,blank = True, on_delete = models.RESTRICT)
    escalationtemplate = models.ForeignKey('onboarding.TypeAssist', null=True, blank=True, related_name="esc_types", on_delete=models.RESTRICT)
    notify             = models.EmailField(blank = True, null = True)
    client             = models.ForeignKey("onboarding.Bt", null = True,blank = True, on_delete = models.RESTRICT, related_name='esc_clients')

    objects = ESCManager() 
    
    class Meta(BaseModel.Meta):
        db_table = 'escalationmatrix'
        get_latest_by = ["mdtz", 'cdtz']
        constraints         = [
            models.CheckConstraint(
                condition = models.Q(frequencyvalue__gte = 0),
                name='frequencyvalue_gte_0_ck'
            ),
            models.CheckConstraint(
                  condition=models.Q(notify__isnull=True) | models.Q(notify='') | models.Q(notify__regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
                name='valid_notify_format'
            ),
         
        ]