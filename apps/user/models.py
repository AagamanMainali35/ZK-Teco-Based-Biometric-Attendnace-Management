from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.base.models import BaseModel
from hrmweb import settings


class Employee(BaseModel, AbstractUser):
    employee_id = models.CharField(unique=True, max_length=10)
    email = models.EmailField(unique=True)
    zk_device_user_id = models.CharField(unique=True, max_length=10, db_index=True, null=True, blank=True)

    def generate_organization_email(self):
        """Generates email using .env domain, e.g. 'aagaman@lioris.ai'."""
        domain = getattr(settings, "ORGANIZATION_DOMAIN", "lioris.ai")
        return f"{self.username.lower()}@{domain.lower()}"

    def __str__(self):
        return f"{self.username} ({self.employee_id or 'No ID'})"


class EmployeeSequence(BaseModel):
    last_employee_id = models.PositiveIntegerField(default=0)

    def __str__(self):
        return str(self.last_employee_id)
