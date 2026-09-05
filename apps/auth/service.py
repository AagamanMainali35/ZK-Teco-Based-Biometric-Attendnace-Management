from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.attendance.models import Device
from apps.attendance.service import ZKDeviceService
from apps.base.exception import HTTPException
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
