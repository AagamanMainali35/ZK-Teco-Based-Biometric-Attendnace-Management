from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.attendance.models import Device
from apps.attendance.service import ZKDeviceService
from apps.base.exception import HTTPException
from apps.base.utils import generate_code, send_email
from apps.user.models import Employee, EmployeeSequence


class AuthService:
    @staticmethod
    def create_tokens(user):
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    @staticmethod
    def _attempt_login_(attrs):
        user = authenticate(
            username=attrs["username"],
            password=attrs["password"],
        )

        if user is None:
            raise HTTPException(detail="Invalid username or password.", status_code=status.HTTP_400_BAD_REQUEST)

        return user

    @staticmethod
    def create_user(payload: dict):
        password = payload.pop("password")
        device_serials = payload.pop("device_serials", None)
        devices = None
        if device_serials:
            devices = list(Device.objects.filter(serial__in=device_serials, is_active=True))

        sequence = EmployeeSequence.objects.filter(id=1).first()
        if not sequence:
            sequence = EmployeeSequence.objects.create(id=1, last_employee_id=1)
        else:
            sequence.last_employee_id += 1
            sequence.save(update_fields=["last_employee_id"])

        user = Employee(
            **payload,
            employee_id=f"emp_{sequence.last_employee_id:04d}",
        )
        user.set_password(password)
        sync_result = ZKDeviceService.sync_employee_to_device(user, devices=devices)
        success = sync_result.get("success", None)
        message = sync_result.get("message", None)
        if success:
            user.save()
            return {
                "success": True,
                "message": f"Employee {user.username} created and synced to device",
                "data": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "employee_id": user.employee_id,
                    "zk_device_user_id": user.zk_device_user_id,
                },
                "device_sync": sync_result,
            }
        else:
            raise HTTPException(
                detail=message if message else "Something went wrong during device sync",
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            )

    @staticmethod
    def change_password(email, new_password, password):
        try:
            user = Employee.objects.get(email=email)

            authenticated_user = authenticate(username=user.username, password=password)
            if authenticated_user:
                authenticated_user.set_password(new_password)
                authenticated_user.save()
                return {"success": True, "message": "Password changed successfully."}
            raise HTTPException(detail="Invalid password provided. Please try again.", status_code=status.HTTP_400_BAD_REQUEST)
        except Employee.DoesNotExist:
            raise HTTPException(detail="User account with given email not found", status_code=status.HTTP_400_BAD_REQUEST)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(detail="Something went wrong", status_code=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def change_employee_password(employee_identifier: str, new_password: str):
        """HR/Admin method to change any employee's password without needing old password."""
        employee = (
            Employee.objects.filter(employee_id=employee_identifier).first()
            or Employee.objects.filter(username=employee_identifier).first()
            or Employee.objects.filter(email=employee_identifier).first()
            or (Employee.objects.filter(id=int(employee_identifier)).first() if str(employee_identifier).isdigit() else None)
        )

        if not employee:
            raise HTTPException(detail=f"Employee '{employee_identifier}' not found.", status_code=status.HTTP_404_NOT_FOUND)

        employee.set_password(new_password)
        employee.save()

        return {
            "success": True,
            "message": f"Password for employee '{employee.username}' ({employee.employee_id}) has been updated successfully.",
        }

    @staticmethod
    def send_password_reset_code(email: str):
        """Generates a password reset code, stores it in cache with 10 min TTL, and sends it via email."""
        email = email.lower().strip()
        employee = Employee.objects.filter(email=email, is_active=True).first()

        if not employee:
            raise HTTPException(
                detail="No active employee account found with this email address.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        code = generate_code()
        cache_key = f"password_reset:{email}"
        cache.set(cache_key, code, timeout=600)

        subject = "HRM - Password Reset Verification Code"
        message = (
            f"Hello {employee.first_name or employee.username},\n\n"
            f"You have requested to reset your password.\n"
            f"Your verification code is: {code}\n\n"
            f"This code will expire in 10 minutes.\n\n"
            f"If you did not request this password reset, please ignore this email or contact your administrator."
        )

        email_sent = send_email(to=email, subject=subject, message=message)
        if not email_sent:
            raise HTTPException(
                detail="Failed to send verification email. Please try again later.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return {
            "success": True,
            "message": f"Verification code has been sent to {email}. It will expire in 10 minutes.",
        }

    @staticmethod
    def reset_forgotten_password(email: str, code: str, new_password: str):
        """Resets employee password directly after verifying the supplied reset code against cache."""
        email = email.lower().strip()
        code = code.strip()

        employee = Employee.objects.filter(email=email, is_active=True).first()
        if not employee:
            raise HTTPException(
                detail="No active employee account found with this email address.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = f"password_reset:{email}"
        cached_code = cache.get(cache_key)

        if not cached_code:
            raise HTTPException(
                detail="No reset code request found or code has expired. Please send a code first.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if str(cached_code).upper() != code.upper():
            raise HTTPException(
                detail="Invalid verification code provided. Please check the code and try again.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Validate password strength against configured validators
        try:
            validate_password(new_password, user=employee)
        except ValidationError as e:
            raise HTTPException(
                detail={"new_password": list(e.messages)},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        employee.set_password(new_password)
        employee.save()

        # Invalidate the cache key to prevent reuse
        cache.delete(cache_key)

        return {
            "success": True,
            "message": "Password has been reset successfully. You can now log in with your new password.",
        }
