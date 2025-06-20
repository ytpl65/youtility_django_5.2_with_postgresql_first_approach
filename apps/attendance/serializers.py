from rest_framework import serializers
from apps.attendance.models import PeopleEventlog


class PeopleEventlogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeopleEventlog
        fields = '__all__'

