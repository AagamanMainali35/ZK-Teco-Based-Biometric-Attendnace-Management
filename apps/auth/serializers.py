from rest_framework import serializers

from apps.user.models import Employee


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


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


class ChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["password"] == attrs["new_password"]:
            raise serializers.ValidationError({"new_password": "New password must be different from the current password."})
        return attrs


class ChangeEmployeePasswordSerializer(serializers.Serializer):
    """Used by HR/Admin to change any employee's password."""

    employee_id = serializers.CharField(required=False, help_text="Employee ID or username (optional if specified in URL)")
    new_password = serializers.CharField(write_only=True)


class SendResetCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, help_text="Configured email address of the employee account")

    def validate_email(self, value):
        return value.lower().strip()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, help_text="Configured email address of the employee account")
    code = serializers.CharField(
        required=True,
        max_length=20,
        help_text="Verification code received in email",
    )
    new_password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=False, allow_blank=True, default="")

    def validate_email(self, value):
        return value.lower().strip()

    def validate_code(self, value):
        return value.strip()

    def validate(self, attrs):
        confirm = attrs.get("confirm_password")
        new_password = attrs.get("new_password")
        if confirm and new_password != confirm:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs
