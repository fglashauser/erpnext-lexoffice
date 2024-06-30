from requests import Response


class LexofficeException(Exception):
    msg: str

    def __init__(self, response: Response, message: str):
        super().__init__(message)
        status_code = response.status_code
        body = response.json()
        self.msg = f"status={status_code}, msg={body['message']}"
        print(self.msg)

    def msg(self):
        return self.msg