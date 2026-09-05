from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.user.views import (
    EmployeeListView,
    GroupsView,
    PermissionView,
    SyncEmployeeView,
)

routers = DefaultRouter()
routers.register("permission", PermissionView, basename="permissions")
routers.register("groups", GroupsView, basename="groups")
urlpatterns = [
    path("sync-employee/", SyncEmployeeView.as_view(), name="sync-employee"),
    path("my-attendance/", EmployeeListView.as_view(), name="employee-attendance"),
    path("", include(routers.urls)),
]
