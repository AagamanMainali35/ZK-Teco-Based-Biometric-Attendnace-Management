import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.attendance.models import (
    DailyAttendanceLog,
    DeviceAttendanceLog,
    Policy,
)
from apps.attendance.query import (
    get_all_device,
    get_device_by_serial,
    get_devices_with_sync_state,
    getAllPolicy,
)
from apps.attendance.serializers import (
    DailyAttendanceSerializer,
    DeviceSerializer,
    DeviceSyncStateSerializer,
    PolicySerializer,
    RawAttendanceSerializer,
)
from apps.attendance.service import DeviceService, ZKDeviceService
from apps.base.exception import HTTPException
from apps.base.permissions import HasPerm, IsHR


class DevicePagination(PageNumberPagination):
    page_size = 10
    page_query_param = "page"
    max_page_size = None
    page_size_query_param = None


@extend_schema(tags=["device"])
class DeviceView(ModelViewSet):
    queryset = get_all_device()
    serializer_class = DeviceSerializer
    service_class = DeviceService
    pagination_class = DevicePagination
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        "is_active",
        "port",
    ]

    search_fields = [
        "name",
        "serial",
        "ip_address",
    ]

    ordering_fields = [
        "name",
        "serial",
        "port",
    ]

    lookup_field = "serial"

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), HasPerm("attendance.add_device")]
        if self.action in ["update", "partial_update"]:
            return [IsAuthenticated(), HasPerm("attendance.change_device")]
        if self.action == "destroy":
            return [IsAuthenticated(), HasPerm("attendance.delete_device")]
        return [IsAuthenticated(), HasPerm("attendance.view_device")]

    def create(self, request: DeviceSerializer, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = self.service_class.register_device(serializer.validated_data)
        serializer = self.get_serializer(instance=device)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        action = request.query_params.get("action", None)
        if action not in ["deactivate", "delete"]:
            return Response(
                {"detail": "Invalid action. Please specify 'deactivate' or 'delete'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if action == "deactivate":
            result = self.service_class.deactivate_device(instance)
        else:
            result = self.service_class.delete_device(instance)
        return Response(result, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        device = self.service_class.update_device(instance, serializer.validated_data)
        serializer = self.get_serializer(instance=device)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["device"])
class TestConnectionView(APIView):
    permission_classes = [IsAuthenticated, IsHR]

    def post(self, request, *args, **kwargs):
        serial = self.kwargs.get("serial", None)
        if not serial or serial.strip() == "":
            return Response(
                {"detail": "Please provide valid device serial number."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        device = get_device_by_serial(serial)
        if not device:
            return Response(
                {"detail": "Device not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        result = ZKDeviceService._connect(device)
        return Response(result, status=status.HTTP_200_OK)


@extend_schema(
    tags=["device"],
    parameters=[
        OpenApiParameter(
            name="serial",
            description="Device serial number. If provided, pulls attendance records for this specific device; otherwise pulls for all active devices.",
            required=False,
            type=str,
        )
    ],
)
class PullAttendanceView(APIView):
    permission_classes = [IsAuthenticated, HasPerm("attendance.add_deviceattendancelog")]

    def post(self, request, *args, **kwargs):
        serial = request.query_params.get("serial")
        if serial and serial.strip():
            device = get_device_by_serial(serial.strip())
            if not device:
                return Response(
                    {"detail": f"Device with serial '{serial}' not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            result = ZKDeviceService.pull_attendance_from_device(device)
            return Response(result, status=status.HTTP_200_OK)

        result = ZKDeviceService.pull_attendance_from_all_active_devices()
        return Response(result, status=status.HTTP_200_OK)


@extend_schema(
    tags=["device"],
    parameters=[
        OpenApiParameter(
            name="serial",
            description="Device serial number. If provided, returns sync state for this single device; otherwise returns sync states for all devices.",
            required=False,
            type=str,
        )
    ],
    responses=DeviceSyncStateSerializer(many=True),
)
class DeviceSyncStateView(APIView):
    permission_classes = [IsAuthenticated, IsHR]

    def get(self, request, *args, **kwargs):
        serial = request.query_params.get("serial")
        if serial and serial.strip():
            serial = serial.strip()
            device_data = get_devices_with_sync_state(serial=serial)
            if not device_data:
                return Response(
                    {"detail": f"Device with serial '{serial}' not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            serializer = DeviceSyncStateSerializer(device_data[0])
            return Response(serializer.data, status=status.HTTP_200_OK)

        data = get_devices_with_sync_state()
        serializer = DeviceSyncStateSerializer(data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AttendanceFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(
        field_name="date",
        lookup_expr="gte",
    )

    end_date = django_filters.DateFilter(
        field_name="date",
        lookup_expr="lte",
    )

    employee_id = django_filters.CharFilter(
        field_name="employee__employee_id",
        lookup_expr="exact",
    )

    class Meta:
        model = DailyAttendanceLog
        fields = [
            "start_date",
            "end_date",
            "employee_id",
            "status",
            "is_early_leave",
        ]


@extend_schema(tags=["attendance"])
class DailyAttendanceViewSet(ModelViewSet):
    serializer_class = DailyAttendanceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = AttendanceFilter
    search_fields = [
        "employee__username",
        "employee__employee_id",
    ]
    ordering_fields = [
        "date",
        "employee__username",
        "total_hours",
    ]
    http_method_names = ["get", "delete"]

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAuthenticated(), HasPerm("attendance.delete_dailyattendancelog")]
        return [IsAuthenticated(), HasPerm("attendance.view_dailyattendancelog")]

    def get_queryset(self):
        user = self.request.user
        if not (user and user.is_authenticated):
            return DailyAttendanceLog.objects.none()

        if user.is_superuser or user.is_staff or user.has_perm("attendance.delete_dailyattendancelog"):
            return DailyAttendanceLog.objects.all().select_related("employee")

        return DailyAttendanceLog.objects.filter(employee=user).select_related("employee")


@extend_schema(tags=["attendance"])
class RawAttendanceView(ModelViewSet):
    queryset = DeviceAttendanceLog.objects.all()
    serializer_class = RawAttendanceSerializer
    permission_classes = [IsAuthenticated, IsHR]
    http_method_names = ["get", "delete"]


@extend_schema(tags=["policy"])
class PolicyView(ModelViewSet):
    queryset = getAllPolicy()
    serializer_class = PolicySerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch"]

    def get_permissions(self):
        if self.action in ["create", "partial_update", "update"]:
            return [IsAuthenticated(), HasPerm("attendance.change_policy")]
        return [IsAuthenticated(), HasPerm("attendance.view_policy")]

    def create(self, request, *args, **kwargs):
        if Policy.objects.exists():
            raise HTTPException(
                detail="Cannot add a new policy when one instance already exists. Please update the existing policy.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return super().create(request, *args, **kwargs)
