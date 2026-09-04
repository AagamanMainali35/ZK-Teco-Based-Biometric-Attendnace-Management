from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.attendance.views import (
    DailyAttendanceViewSet,
    DeviceSyncStateView,
    DeviceView,
    PullAttendanceView,
    RawAttendanceView,
    TestConnectionView,
    PolicyView
)

router = DefaultRouter()
router.register("device", DeviceView, basename="device")
router.register("attendance-log", DailyAttendanceViewSet, basename="attendance-log")
router.register("raw/attendance-log", RawAttendanceView, basename="raw-attendance-log")
router.register("policy", PolicyView,basename="PolicyView")


urlpatterns = [
    path("device/sync-state/", DeviceSyncStateView.as_view(), name="device-sync-state"),
    path("device/test-connection/<str:serial>/", TestConnectionView.as_view(), name="test-connection"),
    path("device/pull-attendance/", PullAttendanceView.as_view(), name="pull-attendance"),
    path("", include(router.urls)),
]
