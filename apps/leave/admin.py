from django.contrib import admin

from apps.leave.models import (
    EmployeeLeaveBalance,
    LeaveRequest,
    LeaveType,
)

admin.site.register(LeaveType)

admin.site.register(LeaveRequest)

admin.site.register(EmployeeLeaveBalance)
