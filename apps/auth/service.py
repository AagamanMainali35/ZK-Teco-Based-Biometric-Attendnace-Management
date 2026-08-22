from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.base.exception import HTTPException


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

        attrs["user"] = user
        return attrs
