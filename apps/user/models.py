from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from apps.base.models import BaseModel
from hrmweb import settings


class Employee(BaseModel, AbstractUser):
    employee_id = models.CharField(unique=True, max_length=10)
    email = models.EmailField(unique=True)

    def generate_organization_email(self):
        """Generates email using .env domain, e.g.. 'aagaman@lioris.ai'."""
        domain = getattr(settings, "ORGANIZATION_DOMAIN", "lioris.ai")
        return f"{self.username.lower()}@{domain.lower()}"

    def __str__(self):
        return f"{self.username} ({self.employee_id or 'No ID'})"


class EmployeeSequence(models.Mode):
    employee_id = models.IntegerField(blank=False, null=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, null=False, blank=False)

    def __str__(self):
        return self.employee.first_name


# class Organization(BaseModel):
# NOTE: aDD organization if making multi tenant rather than a  single used based application
#     organization_Name=models.CharField()
#     date_founded=models.DateField()
#     def __str__(self):
