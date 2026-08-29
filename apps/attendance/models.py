from decimal import Decimal

from django.db import models

from apps.user.models import Employee


class StatusChoices(models.TextChoices):
    PRESENT = "present", "Present"
    HALF_DAY = "half_day", "Half Day"


class Device(models.Model):
    serial = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField()
    port = models.IntegerField(default=4370)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.serial})"


class DeviceAttendanceLog(models.Model):
    device_serial = models.CharField(max_length=50)
    device_user_id = models.CharField(max_length=50)
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
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="daily_attendance_logs")
    date = models.DateField(db_index=True)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, null=True, blank=True)
    is_late = models.BooleanField(default=False)
    is_early_leave = models.BooleanField(default=False)
    early_leave_minutes = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [models.UniqueConstraint(fields=["employee", "date"], name="unique_employee_date")]


class SyncState(models.Model):
    device_serial = models.CharField(max_length=50, unique=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.device_serial} → last synced {self.last_synced_at}"


class Policy(models.Model):
    single_column = models.BooleanField(default=True, unique=True, editable=False)
    name = models.CharField(max_length=100, unique=True)
    check_in_time = models.TimeField(default="09:00")
    check_out_time = models.TimeField(default="17:00")
    late_threshold_minutes = models.PositiveIntegerField(default=15)
    half_day_threshold_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=4,
    )

    full_day_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=8,
    )

    tax_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    overtime_enabled = models.BooleanField(default=True)
    overtime_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("1.50"),
    )

    late_deduction_enabled = models.BooleanField(default=False)
    late_deduction_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    minimum_working_days = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(single_column=True),
                name="system_policy_singleton_true",
            )
        ]
