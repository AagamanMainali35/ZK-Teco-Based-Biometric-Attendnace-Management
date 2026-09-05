from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.leave.views import LeaveRequestViewSet, LeaveTypeViewSet

router = DefaultRouter()
router.register("types", LeaveTypeViewSet, basename="leave-types")
router.register("requests", LeaveRequestViewSet, basename="leave-requests")

urlpatterns = [
    path("", include(router.urls)),
]
