from datetime import datetime

from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from apps.leave.models import (
    EmployeeLeaveBalance,
    LeaveRequest,
    LeaveStatus,
    LeaveType,
)
from apps.leave.service import LeaveService


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


class EmployeeLeaveBalanceSerializer(serializers.ModelSerializer):
    used_days = serializers.IntegerField(read_only=True)
    pending_days = serializers.IntegerField(read_only=True)
    remaining_days = serializers.IntegerField(read_only=True)
    available_days = serializers.IntegerField(read_only=True)

    class Meta:
        model = EmployeeLeaveBalance
        fields = [
            "id",
            "employee",
            "leave_type",
            "year",
            "allocated_days",
            "used_days",
            "pending_days",
            "remaining_days",
            "available_days",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "used_days",
            "pending_days",
            "remaining_days",
            "available_days",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.employee:
            data["employee"] = {
                "id": instance.employee.id,
                "employee_id": instance.employee.employee_id,
                "username": instance.employee.username,
                "email": instance.employee.email,
                "first_name": instance.employee.first_name,
                "last_name": instance.employee.last_name,
            }
        if instance.leave_type:
            data["leave_type"] = {
                "id": instance.leave_type.id,
                "name": instance.leave_type.name,
                "code": instance.leave_type.code,
                "is_paid": instance.leave_type.is_paid,
                "days_allowed": instance.leave_type.days_allowed,
            }
        return data


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "employee",
            "leave_type",
            "start_date",
            "end_date",
            "days_count",
            "reason",
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.employee:
            data["employee"] = {
                "id": instance.employee.id,
                "employee_id": instance.employee.employee_id,
                "username": instance.employee.username,
                "email": instance.employee.email,
                "first_name": instance.employee.first_name,
                "last_name": instance.employee.last_name,
            }
        if instance.leave_type:
            data["leave_type"] = {
                "id": instance.leave_type.id,
                "name": instance.leave_type.name,
                "code": instance.leave_type.code,
                "is_paid": instance.leave_type.is_paid,
                "days_allowed": instance.leave_type.days_allowed,
            }
        if instance.reviewed_by:
            data["reviewed_by"] = {
                "id": instance.reviewed_by.id,
                "employee_id": instance.reviewed_by.employee_id,
                "username": instance.reviewed_by.username,
                "email": instance.reviewed_by.email,
                "first_name": instance.reviewed_by.first_name,
                "last_name": instance.reviewed_by.last_name,
            }
        return data


class LeaveRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "employee",
            "leave_type",
            "start_date",
            "end_date",
            "reason",
        ]
        extra_kwargs = {
            "employee": {"required": False},
        }

    def validate(self, attrs):
        request = self.context.get("request")
        employee = attrs.get("employee")
        if not employee and request and request.user and request.user.is_authenticated:
            employee = request.user
            attrs["employee"] = employee

        if not employee:
            raise serializers.ValidationError({"employee": "Employee is required."})

        leave_type = attrs.get("leave_type")
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")

        if start_date and end_date:
            if end_date < start_date:
                raise serializers.ValidationError({"end_date": "End date must be on or after start date."})

            # Check for overlapping active leaves
            overlapping = LeaveRequest.objects.filter(
                employee=employee,
                status__in=[LeaveStatus.PENDING, LeaveStatus.APPROVED],
                start_date__lte=end_date,
                end_date__gte=start_date,
            ).first()
            if overlapping:
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            f"You already have an active leave ({overlapping.leave_type.name} from "
                            f"{overlapping.start_date} to {overlapping.end_date}, status: {overlapping.status}) "
                            f"overlapping with requested dates ({start_date} to {end_date})."
                        ]
                    }
                )

            # Check leave balance quota
            days_count = (end_date - start_date).days + 1
            year = start_date.year
            available_days, balance = LeaveService.get_available_days(employee, leave_type, year)

            if days_count > available_days:
                raise serializers.ValidationError(
                    {
                        "leave_type": [
                            f"Insufficient leave balance. You have {available_days} day(s) available for "
                            f"{leave_type.name} in {year} (Allocated: {balance.allocated_days}, Used: {balance.used_days}, "
                            f"Pending: {balance.pending_days}), but requested {days_count} day(s)."
                        ]
                    }
                )

        return attrs

    def create(self, validated_data):
        start_date = validated_data["start_date"]
        end_date = validated_data["end_date"]
        validated_data["days_count"] = (end_date - start_date).days + 1
        validated_data["status"] = LeaveStatus.PENDING

        return super().create(validated_data)


class LeaveRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = [
            "leave_type",
            "start_date",
            "end_date",
            "reason",
            "status",
            "rejection_reason",
        ]
        extra_kwargs = {
            "leave_type": {"required": False},
            "start_date": {"required": False},
            "end_date": {"required": False},
            "reason": {"required": False},
            "status": {"required": False},
            "rejection_reason": {"required": False},
        }

    def validate(self, attrs):
        instance = self.instance
        employee = instance.employee
        leave_type = attrs.get("leave_type", instance.leave_type)
        start_date = attrs.get("start_date", instance.start_date)
        end_date = attrs.get("end_date", instance.end_date)
        new_status = attrs.get("status")

        # Validation when approving a request
        if new_status == LeaveStatus.APPROVED and instance.status != LeaveStatus.APPROVED:
            year = instance.start_date.year
            balance = LeaveService.get_or_create_balance(employee, instance.leave_type, year)
            used_excluding_current = (
                LeaveRequest.objects.filter(
                    employee=employee,
                    leave_type=instance.leave_type,
                    status=LeaveStatus.APPROVED,
                    start_date__year=year,
                )
                .exclude(id=instance.id)
                .aggregate(total=Sum("days_count"))["total"]
                or 0
            )
            remaining_days = max(0, balance.allocated_days - used_excluding_current)
            if instance.days_count > remaining_days:
                raise serializers.ValidationError(
                    {
                        "status": [
                            f"Cannot approve request. Employee has only {remaining_days} remaining day(s) for "
                            f"{instance.leave_type.name} in {year}, but this request requires {instance.days_count} day(s)."
                        ]
                    }
                )

        # Date and quota validation if dates/type are updated
        if "start_date" in attrs or "end_date" in attrs or "leave_type" in attrs:
            if end_date < start_date:
                raise serializers.ValidationError({"end_date": "End date must be on or after start date."})

            overlapping = (
                LeaveRequest.objects.filter(
                    employee=employee,
                    status__in=[LeaveStatus.PENDING, LeaveStatus.APPROVED],
                    start_date__lte=end_date,
                    end_date__gte=start_date,
                )
                .exclude(id=instance.id)
                .first()
            )
            if overlapping:
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            f"You already have an active leave ({overlapping.leave_type.name} from "
                            f"{overlapping.start_date} to {overlapping.end_date}, status: {overlapping.status}) "
                            f"overlapping with requested dates ({start_date} to {end_date})."
                        ]
                    }
                )

            days_count = (end_date - start_date).days + 1
            year = start_date.year
            available_days, balance = LeaveService.get_available_days(employee, leave_type, year, exclude_request_id=instance.id)
            if days_count > available_days:
                raise serializers.ValidationError(
                    {
                        "leave_type": [
                            f"Insufficient leave balance. You have {available_days} day(s) available for "
                            f"{leave_type.name} in {year} (Allocated: {balance.allocated_days}, Used: {balance.used_days}, "
                            f"Pending: {balance.pending_days}), but requested {days_count} day(s)."
                        ]
                    }
                )

        return attrs

    def update(self, instance, validated_data):
        request = self.context.get("request")
        new_status = validated_data.get("status")

        if new_status and new_status in [LeaveStatus.APPROVED, LeaveStatus.REJECTED]:
            if request and request.user and request.user.is_authenticated:
                instance.reviewed_by = request.user
            instance.reviewed_at = datetime.now()

        instance = super().update(instance, validated_data)

        if "start_date" in validated_data or "end_date" in validated_data:
            instance.days_count = (instance.end_date - instance.start_date).days + 1
            instance.save(update_fields=["days_count"])

        return instance
