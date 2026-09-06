from datetime import datetime

from django.db.models import QuerySet, Sum
from django.utils import timezone

from apps.leave.models import (
    EmployeeLeaveBalance,
    LeaveRequest,
    LeaveStatus,
    LeaveType,
)
from apps.user.models import Employee


class LeaveService:
    @staticmethod
    def get_or_create_balance(
        employee: Employee,
        leave_type: LeaveType,
        year: int = None,
    ) -> EmployeeLeaveBalance:
        """Retrieves or provisions a balance record for the employee, leave type, and year."""
        if year is None:
            year = datetime.now().year

        balance, _ = EmployeeLeaveBalance.objects.get_or_create(
            employee=employee,
            leave_type=leave_type,
            year=year,
            defaults={
                "allocated_days": leave_type.days_allowed,
            },
        )
        return balance

    @staticmethod
    def get_employee_balances(
        employee: Employee,
        year: int = None,
    ) -> QuerySet[EmployeeLeaveBalance]:
        """Ensures balances exist for all active leave types for this employee and returns them."""
        if year is None:
            year = datetime.now().year

        active_types = LeaveType.objects.filter(is_active=True)
        for lt in active_types:
            LeaveService.get_or_create_balance(employee, lt, year)

        return (
            EmployeeLeaveBalance.objects.filter(employee=employee, year=year)
            .select_related("employee", "leave_type")
            .order_by("leave_type__name")
        )

    @staticmethod
    def get_available_days(
        employee: Employee,
        leave_type: LeaveType,
        year: int,
        exclude_request_id: int = None,
    ) -> tuple[int, EmployeeLeaveBalance]:
        """Calculates available days for an employee, leave type, and year (accounting for pending & approved leaves).

        Returns:
            (available_days, balance_instance)
        """
        balance = LeaveService.get_or_create_balance(employee, leave_type, year)

        approved_query = LeaveRequest.objects.filter(
            employee=employee,
            leave_type=leave_type,
            status=LeaveStatus.APPROVED,
            start_date__year=year,
        )
        pending_query = LeaveRequest.objects.filter(
            employee=employee,
            leave_type=leave_type,
            status=LeaveStatus.PENDING,
            start_date__year=year,
        )

        if exclude_request_id:
            approved_query = approved_query.exclude(id=exclude_request_id)
            pending_query = pending_query.exclude(id=exclude_request_id)

        used_days = approved_query.aggregate(total=Sum("days_count"))["total"] or 0
        pending_days = pending_query.aggregate(total=Sum("days_count"))["total"] or 0

        available_days = max(0, balance.allocated_days - (used_days + pending_days))
        return available_days, balance
