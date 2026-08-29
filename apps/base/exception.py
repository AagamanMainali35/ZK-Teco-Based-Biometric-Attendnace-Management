from rest_framework.exceptions import APIException


class HTTPException(APIException):
    def __init__(self, detail, status_code=400, code=None):
        self.status_code = status_code

        if isinstance(detail, str):
            self.detail = {"detail": detail}
        else:
            self.detail = detail

        super().__init__(detail=self.detail, code=code)
