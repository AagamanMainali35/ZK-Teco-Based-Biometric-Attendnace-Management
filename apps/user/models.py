from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.base.models import BaseModel
from hrmweb import settings


class Employee(BaseModel, AbstractUser):
    employee_id = models.CharField(unique=True, max_length=10)
    email = models.EmailField(unique=True)
    zk_device_user_id = models.CharField(unique=True, max_length=10, db_index=True, null=True, blank=True)

    def generate_organization_email(self):
        """Generates email using .env domain, e.g.. 'aagaman@lioris.ai'."""
        domain = getattr(settings, "ORGANIZATION_DOMAIN", "lioris.ai")
        return f"{self.username.lower()}@{domain.lower()}"

    def __str__(self):
        return f"{self.username} ({self.employee_id or 'No ID'})"


class EmployeeSequence(BaseModel):
    last_employee_id = models.PositiveIntegerField(default=0)

    def __str__(self):
        return str(self.last_employee_id)


class Department(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    manager = models.ForeignKey(
        "Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_departments",
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.code})"
