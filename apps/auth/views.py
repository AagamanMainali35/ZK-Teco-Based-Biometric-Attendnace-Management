# views.py
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auth.schema_docs import LOGIN_SCHEMA
from apps.auth.serializers import (
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


class ChangePasswordView(GenericAPIView):
    service_class = AuthService
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ChangePasswordSerializer, tags=["auth"])
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data["email"] = request.user.email
        result = self.service_class.change_password(**serializer.validated_data)
        if not result.get("success"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)
