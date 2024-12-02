import json

from twisted.web.resource import Resource
from twisted.web._responses import NOT_FOUND


class ErrorResponse(Resource):
    def __init__(self, code, detail):
        Resource.__init__(self)
        self.code = code
        self.detail = detail

    def render(self, request):
        request.setResponseCode(self.code)
        request.setHeader(b"content-type", b"application/json; charset=utf-8")
        return json.dumps({"error": self.code, "message": self.detail})


class NotFound(ErrorResponse):
    def __init__(self):
        ErrorResponse.__init__(self, NOT_FOUND, "resource not found")
