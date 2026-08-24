from drf_spectacular.utils import OpenApiExample, OpenApiResponse

from apps.auth.serializers import (
    LoginResponseSerializer,
    LoginSerializer,
    RegisterSerializer,
)

LOGIN_SCHEMA = {"request": LoginSerializer, "summary": "Login Endpoint", "description": "Authenticate a user"}

REGISTER_SCHEMA = {
    "request": RegisterSerializer,
    "summary": "User registration",
}
