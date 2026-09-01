from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.user.models import Department, Employee, EmployeeSequence


@admin.register(Employee)
class EmployeeAdmin(UserAdmin):
    list_display = (
        "employee_id",
        "username",
        "email",
        "first_name",
        "last_name",
        "zk_device_user_id",
        "is_active",
        "is_staff",
    )
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("employee_id", "username", "email", "first_name", "last_name", "zk_device_user_id")
    ordering = ("employee_id",)

    fieldsets = UserAdmin.fieldsets + (("HRM & Biometric Info", {"fields": ("employee_id", "zk_device_user_id")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("HRM & Biometric Info", {"fields": ("employee_id", "zk_device_user_id")}),)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "manager", "is_active", "created_at")
    search_fields = ("name", "code")
    list_filter = ("is_active",)


@admin.register(EmployeeSequence)
class EmployeeSequenceAdmin(admin.ModelAdmin):
    list_display = ("last_employee_id", "updated_at")
