from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.auth.serializers import (
    ChangeEmployeePasswordSerializer,
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    SendResetCodeSerializer,
    UserSerializer,
)
from apps.auth.service import AuthService
from apps.base.permissions import IsEmployee, IsHR


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(
        request=LoginSerializer,
        summary="Login Endpoint",
        description="Authenticate a user",
        tags=["auth"],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = AuthService._attempt_login_(serializer.validated_data)
        tokens = AuthService.create_tokens(user)

        return Response(tokens, status=status.HTTP_200_OK)


@extend_schema(tags=["auth"], description="Returns the authenticated user's details", summary="Get Current User")
class CurrentUser(GenericAPIView):
    permission_classes = [IsAuthenticated, IsEmployee]
    serializer_class = UserSerializer

    def get(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["auth"],
    description="Allows an authenticated employee to change their own password.",
    summary="Change Password",
)
class ChangePasswordView(GenericAPIView):
    service_class = AuthService
    permission_classes = [IsAuthenticated, IsEmployee]
    serializer_class = ChangePasswordSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "change_pwd"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data["email"] = request.user.email
        result = self.service_class.change_password(**serializer.validated_data)
        if not result.get("success"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


@extend_schema(
    tags=["auth"],
    description="Allows HR/Admin to change any employee's password.",
    summary="Change Employee Password",
)
class ChangeEmployeePasswordView(GenericAPIView):
    service_class = AuthService
    permission_classes = [IsAuthenticated, IsHR]
    serializer_class = ChangeEmployeePasswordSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "change_pwd"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee_id = serializer.validated_data.get("employee_id")
        new_password = serializer.validated_data.get("new_password")
        result = self.service_class.change_employee_password(
            employee_identifier=employee_id,
            new_password=new_password,
        )
        return Response(result, status=status.HTTP_200_OK)


@extend_schema(
    tags=["auth"],
    description="Sends a 6-character password reset verification code to the employee's configured email.",
    summary="Send Reset Code",
)
class SendCodeView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = SendResetCodeSerializer
    service_class = AuthService
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "send_code"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        result = self.service_class.send_password_reset_code(email=email)
        return Response(result, status=status.HTTP_200_OK)


@extend_schema(
    tags=["auth"],
    description="Resets employee password by verifying the reset code and updating the password in 1 step.",
    summary="Forgot Password",
)
class ForgotPasswordView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer
    service_class = AuthService
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "forgot_password"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]
        new_password = serializer.validated_data["new_password"]
        result = self.service_class.reset_forgotten_password(
            email=email,
            code=code,
            new_password=new_password,
        )
        return Response(result, status=status.HTTP_200_OK)
