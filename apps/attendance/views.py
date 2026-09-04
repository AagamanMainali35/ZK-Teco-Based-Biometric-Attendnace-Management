from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.attendance.models import DailyAttendanceLog, DeviceAttendanceLog
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
    def post(self, request, *args, **kwargs):
        serial = self.kwargs.get("serial_number", None)
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


@extend_schema(tags=["attendance"])
class DailyAttendanceViewSet(ModelViewSet):
    queryset = DailyAttendanceLog.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        "date",
        "status",
        "is_early_leave",
    ]
    search_fields = [
        "employee__username",
    ]
    ordering_fields = [
        "date", 
        "employee__username",
        "total_hours"
    ]
    serializer_class = DailyAttendanceSerializer
    http_method_names = ["get", "delete"]

    def get_object(self):
        if self.request.method == "GET":
            self.lookup_field = "employee_id"

        return super().get_object()


@extend_schema(tags=["attendance"])
class RawAttendanceView(ModelViewSet):
    queryset = DeviceAttendanceLog.objects.all()
    serializer_class = RawAttendanceSerializer
    http_method_names = ["get", "delete"]


@extend_schema(tags=["policy"])
class PolicyView(ModelViewSet):
    queryset=getAllPolicy()
    serializer_class=PolicySerializer
    http_method_names = ["get", "post", "patch"]
