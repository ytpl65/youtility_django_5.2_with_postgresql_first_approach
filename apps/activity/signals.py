from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.activity.models.asset_model import AssetLog,Asset
from apps.activity.models.attachment_model import Attachment
from apps.activity.models.location_model import Location
from apps.activity.models.question_model import Question,QuestionSet,QuestionSetBelonging
from .serializers import AttachmentSerializer,AssetSerializer,LocationSerializer,QuestionSerializer,QuestionSetSerializer,QuestionSetBelongingSerializer
from django.utils import timezone
import json
import datetime
from background_tasks.tasks import publish_mqtt
TOPIC = "redmine_to_noc"


def convert_dates(obj):
    
    if isinstance(obj, dict):
        return {k: convert_dates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_dates(v) for v in obj]
    elif isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    else:
        return obj

@receiver(post_save, sender=Asset)
def create_asset_log(sender, instance, created, **kwargs):
    if not created:
        last_log = AssetLog.objects.filter(asset_id=instance.id).order_by('-cdtz').first()
        if last_log and last_log.newstatus != instance.runningstatus:
            AssetLog.objects.create(
                asset_id=instance.id,
                oldstatus=last_log.newstatus,
                newstatus=instance.runningstatus,
                cdtz=timezone.now(),
                bu_id=instance.bu_id,
                client_id=instance.client_id,
                ctzoffset=instance.ctzoffset,
                people_id=instance.muser_id
            )
        elif not last_log:
            AssetLog.objects.create(
                asset_id=instance.id,
                oldstatus=None,
                newstatus=instance.runningstatus,
                cdtz=timezone.now(),
                people_id=instance.muser_id,
                bu_id=instance.bu_id,
                client_id=instance.client_id,
                ctzoffset=instance.ctzoffset
            )

def build_payload(instance, model_name, created):
    serializer_cls = {
        "Attachment": AttachmentSerializer,
        "Asset": AssetSerializer,
        "Location": LocationSerializer,
        "Question": QuestionSerializer,
        "QuestionSet": QuestionSetSerializer,
        "QuestionSetBelonging": QuestionSetBelongingSerializer
    }[model_name]
    serializer = serializer_cls(instance)
    json_serializable_data = convert_dates(serializer.data)
    return json.dumps({
        "operation": "CREATE" if created else "UPDATE",
        "app": "Activity",
        "models": model_name,
        "payload": json_serializable_data
    })

@receiver(post_save,sender=Attachment)
def attachment_post_save(sender,instance,created,**kwargs):
    payload = build_payload(instance, "Attachment", created)
    publish_mqtt.delay(TOPIC, payload)


@receiver(post_save,sender=Asset)
def asset_post_save(sender,instance,created,**kwargs):
    payload = build_payload(instance, "Asset", created)
    publish_mqtt.delay(TOPIC, payload)

@receiver(post_save,sender=Location)
def location_post_save(sender,instance,created,**kwargs):
    payload = build_payload(instance, "Location", created)
    publish_mqtt.delay(TOPIC, payload)

@receiver(post_save,sender=Question)
def question_post_save(sender,instance,created,**kwargs):
    payload = build_payload(instance, "Question", created)
    publish_mqtt.delay(TOPIC, payload)

@receiver(post_save,sender=QuestionSet)
def questionset_post_save(sender,instance,created,**kwargs):
    payload = build_payload(instance, "QuestionSet", created)
    publish_mqtt.delay(TOPIC, payload)

@receiver(post_save,sender=QuestionSetBelonging)
def questionsetbelonging_post_save(sender,instance,created,**kwargs):
    payload = build_payload(instance, "QuestionSetBelonging", created)
    publish_mqtt.delay(TOPIC, payload)

    


