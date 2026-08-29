# urls.py
from django.urls import path

from apps.auth.views import (
    CurrentUser,
    LoginView,
    RegisterView,
    ResetPasswordView,
    SendCodeView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", CurrentUser.as_view(), name="register"),
    path("send-code/", SendCodeView.as_view(), name="register"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
]
