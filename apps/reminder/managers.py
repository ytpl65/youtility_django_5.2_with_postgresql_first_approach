from django.db import models
from django.db.models import Q, F, Count, Case, When, Value, ExpressionWrapper
from django.db.models.functions import Cast
from datetime import datetime, timedelta, timezone


class ReminderManager(models.Manager):
    use_in_migrations = True
    
    
    def get_all_due_reminders(self):
        qset = self.select_related(
            'bt', 'job', 'asset', 'qset', 'pgroup', 'people'
        ).annotate(
            rdate=ExpressionWrapper(
            F('reminderdate') + timedelta(minutes=1) * Cast('ctzoffset', models.IntegerField()),
            output_field=models.DateTimeField(),
        ),
        pdate=ExpressionWrapper(
            F('plandatetime') + timedelta(minutes=1) * Cast('ctzoffset', models.IntegerField()),
            output_field=models.DateTimeField(),
        ),
        ).filter(
            ~Q(status='SUCCESS'),
            reminderdate__gt = datetime.now(timezone.utc),
        ).values(
            'rdate', 'pdate', 'job__jobname', 'bu__buname', 'asset__assetname', 'job__jobdesc',
            'qset__qsetname', 'priority', 'reminderin', 'people__peoplename', 'cuser__peoplename',
            'group__groupname', 'people_id', 'group_id', 'cuser_id', 'muser_id', 'mailids', 
            'muser__peoplename', 'id'
        ).distinct()
        return qset or self.none()