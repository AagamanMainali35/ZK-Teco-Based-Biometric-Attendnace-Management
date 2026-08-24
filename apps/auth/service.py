import datetime

import jwt
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auth.serializers import RegisterSerializer
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
    def create_user(payload: RegisterSerializer):
        password = payload.pop("password")

        sequence = EmployeeSequence.objects.filter(id=1).first()
        if not sequence:
            sequence = EmployeeSequence.objects.create(last_employee_id=1)
        else:
            sequence.last_employee_id += 1
            sequence.save(update_fields=["last_employee_id"])

        user = Employee(
            **payload,
            employee_id=sequence.last_employee_id,
        )
        user.set_password(password)
        user.save()

        return user

    @staticmethod
    def _initiate_reset_password(email, new_password, password):
        try:
            user = Employee.objects.get(email=email)

            user = authenticate(username=user.username, password=password)
            if user:
                user.set_password(new_password)
                return {"reset": True, "message": "Password reset has been successfully Completed"}
            raise HTTPException(detail="Invalid password provided please try again later", status_code=status.HTTP_400_BAD_REQUEST)
        except Employee.DoesNotExist:
            raise HTTPException(detail="User account with given email not found", status_code=status.HTTP_400_BAD_REQUEST)

        except Exception:
            raise HTTPException(detail="Something went wrong", status_code=status.HTTP_400_BAD_REQUEST)
