from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.attendance.models import PeopleEventlog
from apps.attendance.serializers import PeopleEventlogSerializer
import json
from background_tasks.tasks import publish_mqtt
TOPIC="redmine_to_noc"


def build_payload(instance, model_name, created):
    serializer_cls = {
        "PeopleEventlog": PeopleEventlogSerializer
    }[model_name]
    serializer = serializer_cls(instance)
    return json.dumps({
        "operation": "CREATE" if created else "UPDATE",
        "app": "Attendance",
        "models": model_name,
        "payload": serializer.data
    })

@receiver(post_save, sender=PeopleEventlog)
def peopleeventlog_post_save(sender, instance, created, **kwargs):
    payload = build_payload(instance, "PeopleEventlog", created)
    publish_mqtt.delay(TOPIC, payload)

