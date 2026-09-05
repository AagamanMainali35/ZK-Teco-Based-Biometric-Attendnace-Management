from django.utils import timezone
from rest_framework import serializers

from apps.leave.models import LeaveRequest, LeaveStatus, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = [
            "id",
            "name",
            "code",
            "days_allowed",
            "is_paid",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_code(self, value):
        return value.upper().strip()


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_username = serializers.CharField(source="employee.username", read_only=True)
    employee_id = serializers.CharField(source="employee.employee_id", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    reviewed_by_username = serializers.CharField(source="reviewed_by.username", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "employee",
            "employee_username",
            "employee_id",
            "leave_type",
            "leave_type_name",
            "start_date",
            "end_date",
            "days_count",
            "reason",
            "status",
            "reviewed_by",
            "reviewed_by_username",
            "reviewed_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "employee_username",
            "employee_id",
            "leave_type_name",
            "days_count",
            "reviewed_by",
            "reviewed_by_username",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "employee": {"required": False},
            "status": {"required": False},
        }

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date must be on or after start date."})

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if "employee" not in validated_data and request and request.user and request.user.is_authenticated:
            validated_data["employee"] = request.user

        start_date = validated_data["start_date"]
        end_date = validated_data["end_date"]
        validated_data["days_count"] = (end_date - start_date).days + 1

        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        new_status = validated_data.get("status")

        if new_status and new_status in [LeaveStatus.APPROVED, LeaveStatus.REJECTED]:
            if request and request.user and request.user.is_authenticated:
                instance.reviewed_by = request.user
            instance.reviewed_at = timezone.now()

        instance = super().update(instance, validated_data)

        if "start_date" in validated_data or "end_date" in validated_data:
            instance.days_count = (instance.end_date - instance.start_date).days + 1
            instance.save(update_fields=["days_count"])

        return instance
