# serializers.py
from django.contrib.auth.models import Group, Permission
from rest_framework import serializers


class PermissionSerializer(serializers.ModelSerializer):
    """Simple permission serializer."""

    class Meta:
        model = Permission
        fields = ["id", "name", "codename"]


class GroupSerializer(serializers.ModelSerializer):
    """Group serializer with permissions."""

    permissions = serializers.PrimaryKeyRelatedField(queryset=Permission.objects.all(), many=True, required=False)
    permission_details = PermissionSerializer(source="permissions", many=True, read_only=True)
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ["id", "name", "permissions", "permission_details", "user_count"]

    def get_user_count(self, obj):
        """Count users in this group."""
        return obj.user_set.count()

    def create(self, validated_data):
        """Create group with permissions."""
        permissions = validated_data.pop("permissions", [])
        group = Group.objects.create(**validated_data)
        group.permissions.set(permissions)
        return group

    def update(self, instance, validated_data):
        """Update group with permissions."""
        permissions = validated_data.pop("permissions", None)

        # Update name
        instance.name = validated_data.get("name", instance.name)
        instance.save()

        # Update permissions if provided
        if permissions is not None:
            instance.permissions.set(permissions)

        return instance


class GroupListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list view."""

    user_count = serializers.IntegerField()
    permission_count = serializers.IntegerField()

    class Meta:
        model = Group
        fields = ["id", "name", "user_count", "permission_count"]
