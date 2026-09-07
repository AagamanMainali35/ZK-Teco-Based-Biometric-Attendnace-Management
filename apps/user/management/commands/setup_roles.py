from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.user.models import Employee


class Command(BaseCommand):
    help = "Seed RBAC groups ('HR', 'Employee') and assign granular permissions matching permissions.py."

    def add_arguments(self, parser):
        parser.add_argument(
            "--assign-employees",
            action="store_true",
            help="Assign all existing active employees without a group to the 'Employee' group.",
        )
        parser.add_argument(
            "--hr-user",
            type=str,
            default=None,
            help="Assign a specific user (username, email, or employee_id) to the 'HR' group.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear and reassign permissions for the groups.",
        )

    def handle(self, *args, **options):
        assign_employees = options["assign_employees"]
        hr_identifier = options["hr_user"]
        clear_perms = options["clear"]

        self.stdout.write(self.style.NOTICE("--- Setting Up RBAC Groups & Permissions ---"))

        with transaction.atomic():
            # 1. Create or get 'HR' and 'Employee' groups
            hr_group, hr_created = Group.objects.get_or_create(name="HR")
            employee_group, emp_created = Group.objects.get_or_create(name="Employee")

            if hr_created:
                self.stdout.write(self.style.SUCCESS("  [+] Created group: 'HR'"))
            else:
                self.stdout.write(self.style.WARNING("  [*] Group 'HR' already exists"))

            if emp_created:
                self.stdout.write(self.style.SUCCESS("  [+] Created group: 'Employee'"))
            else:
                self.stdout.write(self.style.WARNING("  [*] Group 'Employee' already exists"))

            if clear_perms:
                hr_group.permissions.clear()
                employee_group.permissions.clear()
                self.stdout.write(self.style.WARNING("  [*] Cleared existing permissions from groups"))

            # 2. HR Permissions: full access to HRM modules (user, leave, attendance)
            hr_permissions = Permission.objects.filter(content_type__app_label__in=["user", "leave", "attendance"])
            hr_group.permissions.set(hr_permissions)
            self.stdout.write(self.style.SUCCESS(f"  [+] Assigned {hr_permissions.count()} permissions to 'HR' group"))

            # 3. Employee Permissions: view policies, view own logs, apply/view leave, view balance
            employee_permissions_map = [
                ("user", "view_employee"),
                ("attendance", "view_policy"),
                ("attendance", "view_dailyattendancelog"),
                ("attendance", "view_deviceattendancelog"),
                ("leave", "view_leavetype"),
                ("leave", "add_leaverequest"),
                ("leave", "view_leaverequest"),
                ("leave", "view_employeeleavebalance"),
            ]

            emp_permissions = Permission.objects.filter(
                content_type__app_label__in=[app for app, _ in employee_permissions_map],
                codename__in=[codename for _, codename in employee_permissions_map],
            )
            employee_group.permissions.set(emp_permissions)
            self.stdout.write(self.style.SUCCESS(f"  [+] Assigned {emp_permissions.count()} permissions to 'Employee' group"))

            # 4. Optional: Assign HR group to a specified user
            if hr_identifier:
                user = (
                    Employee.objects.filter(username=hr_identifier).first()
                    or Employee.objects.filter(email=hr_identifier).first()
                    or Employee.objects.filter(employee_id=hr_identifier).first()
                )
                if user:
                    user.groups.add(hr_group)
                    self.stdout.write(self.style.SUCCESS(f"  [+] Added user '{user.username}' ({user.employee_id}) to 'HR' group"))
                else:
                    self.stdout.write(self.style.ERROR(f"  [!] User with identifier '{hr_identifier}' not found."))

            # 5. Optional: Assign existing employees without groups to Employee group
            if assign_employees:
                employees_without_groups = Employee.objects.filter(is_active=True, groups__isnull=True)
                count = employees_without_groups.count()
                for emp in employees_without_groups:
                    emp.groups.add(employee_group)
                self.stdout.write(self.style.SUCCESS(f"  [+] Assigned {count} active employees without groups to 'Employee' group"))

        self.stdout.write(self.style.SUCCESS("\n RBAC roles and permissions seeded successfully!"))
