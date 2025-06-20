from rest_framework import serializers
from apps.activity.models.job_model import Job,Jobneed,JobneedDetails
from apps.activity.models.question_model import Question,QuestionSet,QuestionSetBelonging
from datetime import datetime,time

class CustomTimeField(serializers.Field):
    def to_representation(self, value):
        if isinstance(value, datetime):
            return value.time().isoformat()  # Convert datetime to time
        elif isinstance(value, time):
            return value.isoformat()
        return None

    def to_internal_value(self, data):
        try:
            return datetime.strptime(data, '%H:%M:%S').time()
        except ValueError:
            raise serializers.ValidationError("Invalid time format. Use 'HH:MM:SS'.")

class JobSerializers(serializers.ModelSerializer):
    starttime = CustomTimeField()
    endtime = CustomTimeField()
    class Meta:
        model = Job
        fields = '__all__'


class JobneedSerializers(serializers.ModelSerializer):
    class Meta:
        model = Jobneed
        fields = '__all__'


class JobneedDetailsSerializers(serializers.ModelSerializer):
    class Meta:
        model = JobneedDetails
        fields = '__all__'


class QuestionSerializers(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'


class QuestionSetSerializers(serializers.ModelSerializer):
    class Meta:
        model = QuestionSet
        fields = '__all__'


class QuestionSetBelongingSerializers(serializers.ModelSerializer):
    class Meta:
        model = QuestionSetBelonging
        fields = '__all__'
