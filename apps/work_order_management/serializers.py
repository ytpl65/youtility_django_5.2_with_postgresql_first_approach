from rest_framework import serializers
from .models import Wom,WomDetails

class WomSerializers(serializers.ModelSerializer):
    class Meta:
        model = Wom
        fields = "__all__"



class WomDetailsSerializers(serializers.ModelSerializer):
    class Meta:
        model = WomDetails
        fields = "__all__"


