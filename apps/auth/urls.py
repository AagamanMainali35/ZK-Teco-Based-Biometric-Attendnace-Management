from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.auth.views import (
    ChangeEmployeePasswordView,
    ChangePasswordView,
    CurrentUser,
    LoginView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", CurrentUser.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("change-employee-password/", ChangeEmployeePasswordView.as_view(), name="change-employee-password"),
]
