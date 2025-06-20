from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.peoples.models import People
from apps.peoples.serializers import PeopleSerializer
import json

from background_tasks.tasks import publish_mqtt
TOPIC = "redmine_to_noc"


def build_payload(instance, model_name, created):
    serializer_cls = {
        "People": PeopleSerializer
    }[model_name]
    serializer = serializer_cls(instance)
    return json.dumps({
        "operation": "CREATE" if created else "UPDATE",
        "app": "Peoples",
        "models": model_name,
        "payload": serializer.data
    })


@receiver(post_save, sender=People)
def people_post_save(sender, instance, created, **kwargs):
    payload = build_payload(instance, "People", created)
    publish_mqtt.delay(TOPIC, payload)
