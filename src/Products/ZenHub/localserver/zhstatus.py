from twisted.web._responses import INTERNAL_SERVER_ERROR

from .errors import ErrorResponse
from .resource import ZenResource


class ZenHubStatus(ZenResource):
    def __init__(self, statusgetter):
        ZenResource.__init__(self)
        self._getstatus = statusgetter

    def render_GET(self, request):
        try:
            request.responseHeaders.addRawHeader(
                b"content-type", b"text/plain; charset=utf-8"
            )
            return self._getstatus()
        except Exception:
            self.log.exception("failed to get ZenHub connection status")
            return ErrorResponse(
                INTERNAL_SERVER_ERROR, "zenhub status unavailable"
            )
