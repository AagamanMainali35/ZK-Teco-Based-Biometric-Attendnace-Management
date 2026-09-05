from django.contrib.auth.models import Group, Permission
from rest_framework import serializers

from apps.auth.service import AuthService
from apps.user.models import Employee


class PermissionSerializer(serializers.ModelSerializer):
    """Simple permission serializer."""

    class Meta:
        model = Permission
        fields = ["id", "name", "codename"]


class GroupSerializer(serializers.ModelSerializer):
    """Group serializer with permissions."""

    permissions = serializers.PrimaryKeyRelatedField(queryset=Permission.objects.all(), many=True, required=False)

    class Meta:
        model = Group
        fields = ["id", "name", "permissions"]

    def create(self, validated_data):
        """Create group with permissions."""
        permissions = validated_data.pop("permissions", [])
        group = Group.objects.create(**validated_data)
        group.permissions.set(permissions)
        return group

    def update(self, instance, validated_data):
        """Update group with permissions."""
        permissions = validated_data.pop("permissions", None)

        instance.name = validated_data.get("name", instance.name)
        instance.save()

        if permissions is not None:
            instance.permissions.set(permissions)

        return instance


class EmployeeSerializer(serializers.ModelSerializer):
    """Unified serializer for Employee CRUD operations.

    Handles listing, retrieval, creation (with automated ID assignment and ZKTeco device sync),
    and updates.
    """

    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={"input_type": "password"},
        help_text="Required when creating a new employee. Leave blank on updates to keep current password.",
    )
    device_serials = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        write_only=True,
        default=None,
        help_text="Optional list of device serials to sync to on creation.",
    )
    groups = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = Employee
        fields = [
            "id",
            "employee_id",
            "username",
            "email",
            "zk_device_user_id",
            "password",
            "first_name",
            "last_name",
            "is_active",
            "groups",
            "device_serials",
            "date_joined",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "employee_id",
            "zk_device_user_id",
            "date_joined",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["groups"] = [group.name for group in instance.groups.all()]
        return data

    def validate_username(self, value):
        value = value.strip()
        instance = getattr(self, "instance", None)
        qs = Employee.objects.filter(username=value)
        if instance:
            qs = qs.exclude(id=instance.id)
        if qs.exists():
            raise serializers.ValidationError("An employee with this username already exists.")
        return value

    def validate_email(self, value):
        value = value.lower().strip()
        instance = getattr(self, "instance", None)
        qs = Employee.objects.filter(email=value)
        if instance:
            qs = qs.exclude(id=instance.id)
        if qs.exists():
            raise serializers.ValidationError("An employee with this email already exists.")
        return value

    def validate(self, attrs):
        if not self.instance and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Password is required when creating an employee."})
        return attrs

    def create(self, validated_data):
        groups = validated_data.pop("groups", None)
        result = AuthService.create_user(validated_data)
        employee = Employee.objects.get(id=result["data"]["id"])
        if groups is not None:
            employee.groups.set(groups)
        employee._device_sync_result = result.get("device_sync")
        return employee

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        groups = validated_data.pop("groups", None)
        validated_data.pop("device_serials", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password and password.strip():
            instance.set_password(password)

        instance.save()

        if groups is not None:
            instance.groups.set(groups)

        return instance
