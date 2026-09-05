from apps.auth.serializers import LoginSerializer

LOGIN_SCHEMA = {
    "request": LoginSerializer,
    "summary": "Login Endpoint",
    "description": "Authenticate a user",
    "tags": ["auth"],
}
