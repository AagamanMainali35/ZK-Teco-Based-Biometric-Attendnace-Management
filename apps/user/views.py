from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.attendance.serializers import DailyAttendanceSerializer
from apps.attendance.service import AttendanceService
from apps.auth.schema_docs import REGISTER_SCHEMA
from apps.auth.serializers import RegisterSerializer
from apps.auth.service import AuthService


# Create your views here.


@extend_schema(tags=["employee"])
class SyncEmployeeView(APIView):
    @extend_schema(**REGISTER_SCHEMA)
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        registration_result = AuthService.create_user(serializer.validated_data)
        if not registration_result.get("success"):
            return Response(registration_result, status=status.HTTP_400_BAD_REQUEST)
        return Response(registration_result, status=status.HTTP_201_CREATED)
