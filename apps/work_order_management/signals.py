from django.db.models.signals import pre_save
from django.dispatch import receiver
from apps.work_order_management.models import Wom

@receiver(pre_save, sender=Wom)
def set_serial_no(sender, instance, **kwargs):
    if instance.id is None:  # Ensure the object is new and doesn't already exist in the database
        if instance.description == 'THIS SECTION TO BE COMPLETED ON RETURN OF PERMIT':
            return
        if instance.identifier == 'SLA':
            # Query for SLA condition
            latest_record = sender.objects.filter(
                client=instance.client,
                bu=instance.bu,
                parent_id=1,
                identifier='SLA'
            ).order_by('-other_data__wp_seqno').first()
        elif instance.identifier == 'WP':
            # Query for the null identifier condition
            latest_record = sender.objects.filter(
                client=instance.client,
                bu=instance.bu,
                parent_id=1,  # Example: Adjust this if needed
                identifier='WP'
            ).order_by('-other_data__wp_seqno').first()
        else:
            latest_record = None  # Fallback for unexpected cases (optional)

        if latest_record is None:
            # This is the first record for the client
            instance.other_data['wp_seqno'] = 1
        elif instance.other_data['wp_seqno'] != latest_record.other_data['wp_seqno']:
            instance.other_data['wp_seqno'] = latest_record.other_data['wp_seqno'] + 1

