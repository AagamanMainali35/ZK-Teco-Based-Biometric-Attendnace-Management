from django.contrib.auth.models import Group, Permission
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.attendance.serializers import DailyAttendanceSerializer
from apps.attendance.service import AttendanceService
from apps.auth.schema_docs import REGISTER_SCHEMA
from apps.auth.serializers import RegisterSerializer
from apps.auth.service import AuthService
from apps.user.serializers import GroupSerializer, PermissionSerializer

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


class EmployeeListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["employee"], responses=DailyAttendanceSerializer(many=True))
    def get(self, request):
        user = request.user
        records = AttendanceService.get_attendance(user.employee_id)

        paginator = PageNumberPagination()
        paginator.page_size = 10
        page = paginator.paginate_queryset(
            queryset=records,
            request=request,
            view=self,
        )
        serializer = DailyAttendanceSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


@extend_schema(tags=["permission"])
class PermissionView(ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    http_method_names = ["get", "delete"]


@extend_schema(tags=["groups"])
class GroupsView(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    http_method_names = ["get", "post", "patch", "delete"]
