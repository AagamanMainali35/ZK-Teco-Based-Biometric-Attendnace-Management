from django.contrib import admin

from apps.leave.models import LeaveRequest, LeaveType


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "days_allowed", "is_paid", "is_active", "created_at")
    search_fields = ("name", "code")
    list_filter = ("is_paid", "is_active")


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "leave_type",
        "start_date",
        "end_date",
        "days_count",
        "status",
        "reviewed_by",
        "created_at",
    )
    list_filter = ("status", "leave_type", "start_date")
    search_fields = ("employee__username", "employee__employee_id", "reason")
