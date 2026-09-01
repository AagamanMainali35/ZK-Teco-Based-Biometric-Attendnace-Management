from django.urls import path
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.views import TokenRefreshView

from apps.auth.views import (
    ChangePasswordView,
    CurrentUser,
    LoginView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", CurrentUser.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
]
