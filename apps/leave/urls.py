from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.leave.views import (
    EmployeeLeaveBalanceViewSet,
    LeaveRequestViewSet,
    LeaveTypeViewSet,
)

router = DefaultRouter()
router.register("types", LeaveTypeViewSet, basename="leave-types")
router.register("requests", LeaveRequestViewSet, basename="leave-requests")
router.register("balances", EmployeeLeaveBalanceViewSet, basename="leave-balances")

urlpatterns = [
    path("", include(router.urls)),
]
