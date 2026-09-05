from django.contrib.auth.models import Group, Permission
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.auth.serializers import ChangeEmployeePasswordSerializer
from apps.user.models import Employee
from apps.user.serializers import (
    EmployeeSerializer,
    GroupSerializer,
    PermissionSerializer,
)


class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


@extend_schema(tags=["employee"])
class EmployeeViewSet(ModelViewSet):
    """Full CRUD ViewSet for managing Employee records.

    Handles employee creation with automatic ID assignment and ZKTeco device synchronization,
    as well as list, retrieve, update, partial update, and delete operations.
    """

    queryset = Employee.objects.all().prefetch_related("groups").order_by("-id")
    serializer_class = EmployeeSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active", "is_staff", "is_superuser", "groups"]
    search_fields = ["username", "email", "first_name", "last_name", "employee_id", "zk_device_user_id"]
    ordering_fields = ["id", "employee_id", "username", "first_name", "last_name", "date_joined", "created_at"]
    ordering = ["-id"]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = serializer.save()

        response_data = self.get_serializer(employee).data
        if hasattr(employee, "_device_sync_result"):
            response_data["device_sync"] = employee._device_sync_result

        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        """Toggle active/inactive status of an employee."""
        employee = self.get_object()
        employee.is_active = not employee.is_active
        employee.save(update_fields=["is_active"])
        return Response(
            {
                "success": True,
                "message": f"Employee {employee.username} is now {'active' if employee.is_active else 'inactive'}.",
                "is_active": employee.is_active,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="change-password",
        serializer_class=ChangeEmployeePasswordSerializer,
    )
    def change_password(self, request, pk=None):
        """Allows HR/Admin to change/reset an employee's password directly."""
        employee = self.get_object()
        serializer = ChangeEmployeePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_password = serializer.validated_data["new_password"]

        employee.set_password(new_password)
        employee.save()

        return Response(
            {
                "success": True,
                "message": f"Password for employee '{employee.username}' ({employee.employee_id}) has been updated successfully.",
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["permission"])
class PermissionView(ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    http_method_names = ["get", "delete"]


@extend_schema(tags=["groups"])
class GroupsView(ModelViewSet):
    queryset = Group.objects.prefetch_related("permissions").order_by("-id")
    serializer_class = GroupSerializer
    http_method_names = ["get", "post", "patch", "delete"]
