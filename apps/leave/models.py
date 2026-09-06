from datetime import datetime

from django.db import models
from django.db.models import Sum

from apps.base.models import BaseModel
from apps.user.models import Employee


def get_current_year():
    return datetime.now().year


class LeaveStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"


class LeaveType(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    days_allowed = models.PositiveIntegerField(default=12, help_text="Annual quota of days for this leave type.")
    is_paid = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class LeaveRequest(BaseModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="leave_requests",
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="leave_requests",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    days_count = models.PositiveIntegerField(default=1)
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=LeaveStatus.choices,
        default=LeaveStatus.PENDING,
    )
    reviewed_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_leaves",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employee.username} - {self.leave_type.name} ({self.start_date} to {self.end_date}) [{self.status}]"


class EmployeeLeaveBalance(BaseModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="leave_balances",
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name="employee_balances",
    )
    year = models.PositiveIntegerField(default=get_current_year)
    allocated_days = models.PositiveIntegerField(
        default=0,
        help_text="Total days granted for this leave type for the year.",
    )

    class Meta:
        unique_together = ("employee", "leave_type", "year")
        ordering = ["-year", "employee", "leave_type"]

    def __str__(self):
        return f"{self.employee.username} - {self.leave_type.name} ({self.year}) [{self.allocated_days} days]"

    def get_used_days(self) -> int:
        total = (
            LeaveRequest.objects.filter(
                employee=self.employee,
                leave_type=self.leave_type,
                status=LeaveStatus.APPROVED,
                start_date__year=self.year,
            ).aggregate(total=Sum("days_count"))["total"]
            or 0
        )
        return total

    def get_pending_days(self) -> int:
        total = (
            LeaveRequest.objects.filter(
                employee=self.employee,
                leave_type=self.leave_type,
                status=LeaveStatus.PENDING,
                start_date__year=self.year,
            ).aggregate(total=Sum("days_count"))["total"]
            or 0
        )
        return total

    @property
    def used_days(self) -> int:
        return self.get_used_days()

    @property
    def pending_days(self) -> int:
        return self.get_pending_days()

    @property
    def remaining_days(self) -> int:
        return max(0, self.allocated_days - self.used_days)

    @property
    def available_days(self) -> int:
        return max(0, self.allocated_days - (self.used_days + self.pending_days))
