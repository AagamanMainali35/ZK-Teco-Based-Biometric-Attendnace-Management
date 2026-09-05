from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auth.schema_docs import LOGIN_SCHEMA
from apps.auth.serializers import (
    ChangeEmployeePasswordSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    UserSerializer,
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


@extend_schema(tags=["auth"])
class CurrentUser(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["auth"])
class ChangePasswordView(GenericAPIView):
    """Allows an authenticated employee to change their own password."""

    service_class = AuthService
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data["email"] = request.user.email
        result = self.service_class.change_password(**serializer.validated_data)
        if not result.get("success"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


@extend_schema(tags=["auth"])
class ChangeEmployeePasswordView(GenericAPIView):
    """Allows HR/Admin to change any employee's password."""

    service_class = AuthService
    permission_classes = [IsAuthenticated]
    serializer_class = ChangeEmployeePasswordSerializer

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
