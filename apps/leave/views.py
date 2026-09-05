from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
import django_filters

from apps.leave.models import LeaveRequest, LeaveStatus, LeaveType
from apps.leave.serializers import (
    LeaveRequestSerializer,
    LeaveTypeSerializer,
)


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


@extend_schema(tags=["leave"])
class LeaveRequestViewSet(ModelViewSet):
    """Compact ViewSet for Leave Applications.

    - GET /api/leave/requests/: List all leaves (filterable by status, employee_id, date range).
    - POST /api/leave/requests/: Apply for a leave.
    - GET /api/leave/requests/{id}/: View leave details.
    - PATCH /api/leave/requests/{id}/: Update leave or status (approve/reject/cancel).
    - DELETE /api/leave/requests/{id}/: Delete a leave request.
    """

    queryset = (
        LeaveRequest.objects.all()
        .select_related("employee", "leave_type", "reviewed_by")
        .order_by("-created_at")
    )
    serializer_class = LeaveRequestSerializer
    pagination_class = LeavePagination
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = LeaveRequestFilter
    search_fields = ["employee__username", "employee__employee_id", "reason"]
    ordering_fields = ["created_at", "start_date", "end_date", "status"]
    http_method_names = ["get", "post", "patch", "delete"]
