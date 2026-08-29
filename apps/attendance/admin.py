from django.contrib import admin

from apps.attendance.models import DailyAttendanceLog, DeviceAttendanceLog

# Register your models here.
admin.site.register(DailyAttendanceLog)
admin.site.register(DeviceAttendanceLog)
