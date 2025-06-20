from django.db.models.signals import pre_save
from django.dispatch import receiver
from apps.y_helpdesk.models import Ticket
from django.db.models import Q

@receiver(pre_save, sender=Ticket)
def set_serial_no_for_ticket(sender, instance, **kwargs):
    if instance.id is None and instance.ticketdesc !='NONE':  # if seqno is not set yet
        latest_record = sender.objects.filter(~Q(ticketdesc='NONE') & ~Q(ticketno__isnull=True), client=instance.client, bu = instance.bu).order_by('-id').first()
        if latest_record is None:
            # This is the first record for the client
            instance.ticketno = f'{instance.bu.bucode}#1'
        else:
            next_no = int(latest_record.ticketno.split('#')[1]) + 1
            instance.ticketno = f'{instance.bu.bucode}#{next_no}'
