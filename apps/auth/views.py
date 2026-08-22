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
        try:
            serializer = LoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user = AuthService._attempt_login_(serializer.validated_data)

            tokens = AuthService.create_tokens(user)

            return Response(tokens, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(e, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
