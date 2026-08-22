from rest_framework_simplejwt.tokens import RefreshToken


class AuthService:
    @staticmethod
    def create_tokens(user):
        refresh = RefreshToken.for_user(user)

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    def _attempt_login_(email_or_username, password):
        pass

    def register(payload):
        pass

    # def reset_password(user_id,new_password,old_password):
    #     pass

    # def forget_password(user):
    #     pass
