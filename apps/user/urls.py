from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.user.views import (
    EmployeeViewSet,
    GroupsView,
    PermissionView,
)

router = DefaultRouter()
router.register("employees", EmployeeViewSet, basename="employees")
router.register("permissions", PermissionView, basename="permissions")
router.register("groups", GroupsView, basename="groups")

urlpatterns = [
    path("", include(router.urls)),
]
