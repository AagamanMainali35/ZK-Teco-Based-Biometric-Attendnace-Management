# Create your views here.
from auth.serializers import LoginSerializer
from auth.service import AuthService
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auth.schema_docs import LOGIN_SCHEMA


class LoginView(APIView):
    @extend_schema(**LOGIN_SCHEMA)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        tokens = AuthService.create_tokens(user)

        return Response(tokens, status=status.HTTP_200_OK)
