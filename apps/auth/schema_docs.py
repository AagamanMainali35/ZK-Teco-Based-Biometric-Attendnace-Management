from drf_spectacular.utils import OpenApiExample, OpenApiResponse

from apps.auth.serializers import LoginResponseSerializer, LoginSerializer

LOGIN_SCHEMA = {
    "request": LoginSerializer,
    "summary": "Login",
    "description": "Authenticate a user",
}
