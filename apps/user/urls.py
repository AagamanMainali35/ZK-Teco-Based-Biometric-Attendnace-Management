from django.urls import path

from apps.user.views import SyncEmployeeView

urlpatterns = [
    path("sync-employee/", SyncEmployeeView.as_view(), name="sync-employee"),
]
