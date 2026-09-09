from datetime import datetime

import django_filters
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.base.permissions import HasPerm, IsEmployee
from apps.leave.models import (
    EmployeeLeaveBalance,
    LeaveRequest,
    LeaveStatus,
    LeaveType,
)
from apps.leave.serializers import (
    EmployeeLeaveBalanceSerializer,
    LeaveRequestCreateSerializer,
    LeaveRequestSerializer,
    LeaveRequestUpdateSerializer,
    LeaveTypeSerializer,
)
from apps.leave.service import LeaveService


class LeavePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class LeaveRequestFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(field_name="start_date", lookup_expr="gte")
    end_date = django_filters.DateFilter(field_name="end_date", lookup_expr="lte")
    employee_id = django_filters.CharFilter(field_name="employee__employee_id", lookup_expr="exact")
    status = django_filters.ChoiceFilter(choices=LeaveStatus.choices)
    leave_type = django_filters.NumberFilter(field_name="leave_type__id")

    class Meta:
        model = LeaveRequest
        fields = ["status", "leave_type", "employee_id", "start_date", "end_date"]


class EmployeeLeaveBalanceFilter(django_filters.FilterSet):
    employee_id = django_filters.CharFilter(field_name="employee__employee_id", lookup_expr="exact")
    leave_type = django_filters.NumberFilter(field_name="leave_type__id")
    year = django_filters.NumberFilter(field_name="year")

    class Meta:
        model = EmployeeLeaveBalance
        fields = ["employee_id", "leave_type", "year"]


@extend_schema(tags=["leave"])
class LeaveTypeViewSet(ModelViewSet):
    """CRUD ViewSet for managing Leave Types (e.g. Sick Leave, Annual Leave)."""

    queryset = LeaveType.objects.all().order_by("-id")
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_paid", "is_active"]
    search_fields = ["name", "code"]
    ordering_fields = ["id", "name", "code", "days_allowed", "created_at"]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), HasPerm("leave.add_leavetype")]
        if self.action in ["update", "partial_update"]:
            return [IsAuthenticated(), HasPerm("leave.change_leavetype")]
        if self.action == "destroy":
            return [IsAuthenticated(), HasPerm("leave.delete_leavetype")]
        return [IsAuthenticated(), HasPerm("leave.view_leavetype")]


@extend_schema(tags=["leave"])
class LeaveRequestViewSet(ModelViewSet):
    """Compact ViewSet for Leave Applications."""

    serializer_class = LeaveRequestSerializer
    pagination_class = LeavePagination
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = LeaveRequestFilter
    search_fields = ["employee__username", "employee__employee_id", "reason"]
    ordering_fields = ["created_at", "start_date", "end_date", "status"]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        if self.action in ["update", "partial_update"]:
            return [IsAuthenticated(), HasPerm("leave.change_leaverequest")]
        if self.action == "destroy":
            return [IsAuthenticated(), HasPerm("leave.delete_leaverequest")]
        if self.action == "create":
            return [IsAuthenticated(), HasPerm("leave.add_leaverequest")]
        return [IsAuthenticated(), HasPerm("leave.view_leaverequest")]

    def get_queryset(self):
        user = self.request.user
        if not (user and user.is_authenticated):
            return LeaveRequest.objects.none()

        if user.is_superuser or user.is_staff or user.has_perm("leave.change_leaverequest"):
            return LeaveRequest.objects.all().select_related("employee", "leave_type", "reviewed_by").order_by("-created_at")

        return LeaveRequest.objects.filter(employee=user).select_related("employee", "leave_type", "reviewed_by").order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return LeaveRequestCreateSerializer
        if self.action in ["update", "partial_update"]:
            return LeaveRequestUpdateSerializer
        return LeaveRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        output_serializer = LeaveRequestSerializer(instance, context=self.get_serializer_context())
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        output_serializer = LeaveRequestSerializer(instance, context=self.get_serializer_context())
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        output_serializer = LeaveRequestSerializer(instance, context=self.get_serializer_context())
        return Response(output_serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["leave"])
class EmployeeLeaveBalanceViewSet(ModelViewSet):
    """ViewSet for managing and inspecting Employee Leave Balances."""

    serializer_class = EmployeeLeaveBalanceSerializer
    pagination_class = LeavePagination
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = EmployeeLeaveBalanceFilter
    ordering_fields = ["year", "allocated_days", "created_at"]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        if self.action == "my_balances":
            return [IsAuthenticated(), IsEmployee()]
        if self.action == "create":
            return [IsAuthenticated(), HasPerm("leave.add_employeeleavebalance")]
        if self.action in ["update", "partial_update"]:
            return [IsAuthenticated(), HasPerm("leave.change_employeeleavebalance")]
        if self.action == "destroy":
            return [IsAuthenticated(), HasPerm("leave.delete_employeeleavebalance")]
        return [IsAuthenticated(), HasPerm("leave.view_employeeleavebalance")]

    def get_queryset(self):
        user = self.request.user
        if not (user and user.is_authenticated):
            return EmployeeLeaveBalance.objects.none()

        if user.is_superuser or user.is_staff or user.has_perm("leave.change_employeeleavebalance"):
            return (
                EmployeeLeaveBalance.objects.all()
                .select_related("employee", "leave_type")
                .order_by("-year", "employee__username", "leave_type__name")
            )

        return (
            EmployeeLeaveBalance.objects.filter(employee=user)
            .select_related("employee", "leave_type")
            .order_by("-year", "employee__username", "leave_type__name")
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="year",
                description="Calendar year to retrieve balances for (defaults to current year).",
                required=False,
                type=int,
            )
        ],
        responses=EmployeeLeaveBalanceSerializer(many=True),
    )
    @action(detail=False, methods=["get"], url_path="my-balances")
    def my_balances(self, request):
        """Returns the leave balances for the currently authenticated employee."""
        year = request.query_params.get("year")
        if year:
            try:
                year = int(year)
            except ValueError:
                return Response(
                    {"detail": "Invalid year provided. Must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            year = datetime.now().year

        balances = LeaveService.get_employee_balances(request.user, year=year)
        serializer = self.get_serializer(balances, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
