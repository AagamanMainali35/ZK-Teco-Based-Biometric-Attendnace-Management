from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from apps.base.models import BaseModel
from hrmweb import settings

class User(BaseModel, AbstractUser):
    employee_id = models.IntegerField(unique=True,null=True,blank=True,)
    email = models.EmailField(unique=True,) 


    def generate_organization_email(self):
        """
        Generates email using .env domain, e.g.. 'aagaman@lioris.ai'
        """
        domain = getattr(settings,'ORGANIZATION_DOMAIN','lioris.ai')
        return f"{self.username.lower()}@{domain.lower()}"

    def __str__(self):
        return f"{self.username} ({self.employee_id or 'No ID'})"
    
    