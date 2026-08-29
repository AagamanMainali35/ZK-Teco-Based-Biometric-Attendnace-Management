from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.auth.views import (
    ChangePasswordView,
    CurrentUser,
    LoginView,
    RegisterView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", CurrentUser.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
]
