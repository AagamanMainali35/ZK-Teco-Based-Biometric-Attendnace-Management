from django.db import models

from apps.user.models import Employee


class DeviceAttendanceLog(models.Model):
    device_serial = models.CharField(max_length=50)
    device_user_id = models.CharField(max_length=50)
    uid = models.IntegerField()
    punch_time = models.DateTimeField(db_index=True)
    status = models.IntegerField()
    punch = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-punch_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["device_serial", "device_user_id", "punch_time"],
                name="unique_device_attendance",
            )
        ]


class DailyAttendanceLog(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        LATE = "late", "Late"
        ABSENT = "absent", "Absent"
        HALF_DAY = "half_day", "Half Day"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="daily_attendance_logs")
    date = models.DateField(db_index=True)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ABSENT)
    is_late = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [models.UniqueConstraint(fields=["employee", "date"], name="unique_employee_date")]
