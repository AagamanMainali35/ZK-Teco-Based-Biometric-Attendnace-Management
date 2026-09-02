from rest_framework import serializers

from apps.attendance.models import (
    DailyAttendanceLog,
    Device,
    DeviceAttendanceLog,
    SyncState,
)


class SyncStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncState
        fields = [
            "device_serial",
            "last_synced_at",
            "last_run_at",
        ]


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


class DeviceSyncStateSerializer(serializers.Serializer):
    serial = serializers.CharField()
    name = serializers.CharField()
    ip_address = serializers.CharField()
    port = serializers.IntegerField()
    is_active = serializers.BooleanField()
    last_synced_at = serializers.DateTimeField(allow_null=True)
    last_run_at = serializers.DateTimeField(allow_null=True)


class DailyAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyAttendanceLog
        fields = [
            "employee",
            "date",
            "check_in_time",
            "check_out_time",
            "total_hours",
            "status",
            "is_late",
            "is_early_leave",
            "early_leave_minutes",
        ]


class RawAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceAttendanceLog
        fields = "__all__"
