from django.db import models

from apps.user.models import Employee


class DeviceAttendanceLog(models.Model):
    class PunchType(models.TextChoices):
        CHECK_IN = "0", "Check In"
        CHECK_OUT = "1", "Check Out"
        BREAK_OUT = "2", "Break Out"
        BREAK_IN = "3", "Break In"
        OT_IN = "4", "OT In"
        OT_OUT = "5", "OT Out"

    class VerifyMode(models.TextChoices):
        FINGERPRINT = "1", "Fingerprint"
        CARD = "4", "Card"
        FACE = "15", "Face"

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="attendance_logs",
    )
    device_serial = models.CharField(max_length=50)
    punch_time = models.DateTimeField(db_index=True)
    punch_type = models.CharField(max_length=10, choices=PunchType.choices)
    verify_mode = models.CharField(max_length=20, choices=VerifyMode.choices, null=True, blank=True)
    raw_payload = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-punch_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "punch_time", "device_serial"],
                name="unique_employee_punch_per_device",
            )
        ]
        indexes = [
            models.Index(fields=["employee", "punch_time"]),
        ]

    def __str__(self):
        return f"{self.employee} - {self.get_punch_type_display()} @ {self.punch_time}"


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
