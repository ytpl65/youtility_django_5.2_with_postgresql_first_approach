
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.activity.models.job_model import Job,Jobneed,JobneedDetails
from apps.schedhuler.serializers import JobSerializers,JobneedSerializers,JobneedDetailsSerializers
import json

from background_tasks.tasks import publish_mqtt
from apps.core.signal_utils import queue_mqtt_task

TOPIC = "redmine_to_noc"


def build_payload(instance, model_name, created):
    serializer_cls = {
        "Job": JobSerializers,
        "JobNeed": JobneedSerializers,
        "JobneedDetails": JobneedDetailsSerializers
    }[model_name]
    serializer = serializer_cls(instance)
    return json.dumps({
        "operation": "CREATE" if created else "UPDATE",
        "app": "Activity",
        "models": model_name,
        "payload": serializer.data
    })


@receiver(post_save, sender=Job)
def job_post_save(sender, instance, created, **kwargs):
    payload = build_payload(instance, "Job", created)
    queue_mqtt_task(TOPIC, payload, priority=3)


@receiver(post_save, sender=Jobneed)
def jobneed_post_save(sender, instance, created, **kwargs):
    payload = build_payload(instance, "JobNeed", created)
    queue_mqtt_task(TOPIC, payload, priority=3)


@receiver(post_save, sender=JobneedDetails)
def jobneeddetails_post_save(sender, instance, created, **kwargs):
    payload = build_payload(instance, "JobneedDetails", created)
    queue_mqtt_task(TOPIC, payload, priority=3)
