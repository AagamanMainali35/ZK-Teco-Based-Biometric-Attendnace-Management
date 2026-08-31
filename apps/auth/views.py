# views.py
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auth.schema_docs import LOGIN_SCHEMA, REGISTER_SCHEMA
from apps.auth.serializers import (
    LoginSerializer,
    RegisterSerializer,
    ResetpasswordSerializer,
    UserSerializer,
    send_codeSerializer,
)
from apps.auth.service import AuthService


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(**LOGIN_SCHEMA)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = AuthService._attempt_login_(serializer.validated_data)
        tokens = AuthService.create_tokens(user)

        return Response(tokens, status=status.HTTP_200_OK)


class RegisterView(APIView):
    @extend_schema(**REGISTER_SCHEMA)
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        registration_result = AuthService.create_user(serializer.validated_data)
        return Response(registration_result, status=status.HTTP_200_OK if registration_result.get("success") else status.HTTP_400_BAD_REQUEST)


class CurrentUser(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def post(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SendCodeView(GenericAPIView):
    serializer_class = send_codeSerializer
    service_class = AuthService

    @extend_schema(
        request=send_codeSerializer,
        summary="send a token which acts as a verification code for forgetting-Password",
        description="Send password reset code to user's email",
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        result = self.service_class._initiate_forget_password(email)

        return Response(result, status=status.HTTP_200_OK)


class ResetPasswordView(GenericAPIView):
    service_class = AuthService
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ResetpasswordSerializer)
    def post(self, request):
        serializer = ResetpasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data["email"] = request.user.email
        print(f"{serializer.validated_data}")
        result = self.service_class._initiate_reset_password(**serializer.validated_data)
        if not result["reset"]:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)
