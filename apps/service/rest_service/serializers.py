from rest_framework import serializers
from apps.attendance.models import PeopleEventlog
from apps.peoples.models import People, Pgroup, Pgbelonging
from apps.onboarding.models import Bt, TypeAssist, Shift
from apps.activity.models.job_model import Jobneed, Job
from apps.activity.models.question_model import Question, QuestionSet
from apps.activity.models.location_model import Location
from apps.activity.models.asset_model import Asset

class PeopleEventLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeopleEventlog
        fields = "__all__"


class PeopleSerializer(serializers.ModelSerializer):
    class Meta:
        model = People
        fields = "__all__"


class PgroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pgroup
        fields = "__all__"


class BtSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bt
        fields = "__all__"


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = "__all__"


class TypeAssistSerializer(serializers.ModelSerializer):
    tatype_id = serializers.PrimaryKeyRelatedField(source='tatype', read_only=True)
    bu_id = serializers.PrimaryKeyRelatedField(source='bu', read_only=True)
    client_id = serializers.PrimaryKeyRelatedField(source='client', read_only=True)
    cuser_id = serializers.PrimaryKeyRelatedField(source='cuser', read_only=True)
    muser_id = serializers.PrimaryKeyRelatedField(source='muser', read_only=True)

    class Meta:
        model = TypeAssist
        exclude = ['tenant', 'bu', 'client', 'cuser', 'muser', 'tatype']


class PgbelongingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pgbelonging
        fields = "__all__"


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = "__all__"


class JobneedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Jobneed
        fields = "__all__"


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = "__all__"


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = "__all__"


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = "__all__"


class QuestionSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionSet
        fields = "__all__"
