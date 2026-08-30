from rest_framework import serializers

from .models import Device


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = [
            "serial",
            "name",
            "ip_address",
            "port",
            "is_active",
        ]
        read_only_fields = ["id"]
