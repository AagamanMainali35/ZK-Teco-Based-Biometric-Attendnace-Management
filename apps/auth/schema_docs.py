from drf_spectacular.utils import OpenApiExample

from apps.auth.serializers import LoginResponseSerializer, LoginSerializer

LOGIN_SCHEMA = {
    "request": LoginSerializer,
    "responses": {
        200: LoginResponseSerializer,
    },
    "summary": "Login",
    "description": "Authenticate a user with their username and password ",
    "tags": ["Authentication"],
}
