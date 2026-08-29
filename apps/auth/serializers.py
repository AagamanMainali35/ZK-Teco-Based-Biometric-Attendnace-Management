from django.contrib.auth import authenticate
from rest_framework import serializers, status

from apps.base.exception import HTTPException
from apps.user.models import Employee


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def to_internal_value(self, data):
        data = data.copy()

        if "email" in data and data["email"]:
            data["email"] = data["email"].lower().strip()

        return super().to_internal_value(data)

    def validate_username(self, value):
        if Employee.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        if Employee.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            "id",
            "username",
            "email",
            "employee_id",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
        ]
        read_only_fields = ["id", "username", "email", "employee_id", "is_active", "date_joined"]

    def to_representation(self, instance):
        """Override to remove empty/None fields from output."""
        data = super().to_representation(instance)

        empty_fields = []
        for key, value in data.items():
            if value is None or value == "" or value == []:
                empty_fields.append(key)

        for field in empty_fields:
            data.pop(field)

        return data


class send_codeSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = Employee.objects.get(email=value)
            return user.email
        except Employee.DoesNotExist:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with provided detail not found")


class ChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField()
    new_password = serializers.CharField()

    def validate(self, attrs):
        if attrs["password"] == attrs["new_password"]:
            raise serializers.ValidationError({"new_password": "New password must be different from the current password."})

        return attrs
