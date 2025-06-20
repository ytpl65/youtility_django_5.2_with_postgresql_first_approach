from rest_framework import serializers
from .models import Bt,Shift,TypeAssist,GeofenceMaster


class BtSerializers(serializers.ModelSerializer):
    class Meta:
        model = Bt
        fields = "__all__"


class ShiftSerializers(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = "__all__"


class TypeAssistSerializers(serializers.ModelSerializer):
    class Meta:
        model = TypeAssist
        fields = "__all__"


class GeofenceMasterSerializers(serializers.ModelSerializer):
    class Meta:
        model = GeofenceMaster
        fields = "__all__"

