from rest_framework.permissions import BasePermission


class IsEmployee(BasePermission):
    """Allows access to any active, authenticated employee."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class IsHR(BasePermission):
    """Allows access to users in the 'HR' group, or users with superuser/staff status."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False

        return request.user.is_superuser or request.user.is_staff or request.user.groups.filter(name="HR").exists()


class HasPerm(BasePermission):
    """Reusable permission class that checks specific Django permission(s).

    Evaluates permissions assigned directly to user OR via any of their groups.

    Usage:
        permission_classes = [HasPerm("attendance.add_device")]
        permission_classes = [HasPerm("leave.add_leaverequest", "leave.view_leaverequest")]
    """

    def __init__(self, *perms: str):
        self.perms = perms

    def __call__(self):
        return self

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False

        if request.user.is_superuser:
            return True

        # In Django, user.has_perm() automatically checks user's groups
        return all(request.user.has_perm(perm) for perm in self.perms)
