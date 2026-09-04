from django.urls import path


from apps.user.views import SyncEmployeeView , EmployeeListView

urlpatterns = [
    path("sync-employee/", SyncEmployeeView.as_view(), name="sync-employee"),
    path("my-attendance/", EmployeeListView.as_view(), name="employee-attendance"),

]
