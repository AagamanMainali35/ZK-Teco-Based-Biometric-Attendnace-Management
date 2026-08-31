from django.contrib import admin

from apps.attendance.models import (
    DailyAttendanceLog,
    Device,
    DeviceAttendanceLog,
    Policy,
    SyncState,
)

# Register your models here.
admin.site.register(Device)
admin.site.register(DailyAttendanceLog)
admin.site.register(DeviceAttendanceLog)
admin.site.register(SyncState)
admin.site.register(Policy)
