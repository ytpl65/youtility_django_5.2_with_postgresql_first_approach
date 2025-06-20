from rest_framework import serializers
from apps.activity.models.attachment_model import Attachment
from apps.activity.models.question_model import Question,QuestionSet,QuestionSetBelonging
from apps.activity.models.asset_model import Asset
from apps.activity.models.location_model import Location

class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = '__all__'

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'

class QuestionSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionSet
        fields = '__all__'

class QuestionSetBelongingSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionSetBelonging
        fields = '__all__'

class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = '__all__'

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'
