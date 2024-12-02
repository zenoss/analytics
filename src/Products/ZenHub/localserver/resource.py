import logging

from twisted.web.resource import Resource
from twisted.web._responses import INTERNAL_SERVER_ERROR

from .errors import ErrorResponse, NotFound


class ZenResource(Resource):
    def __init__(self):
        Resource.__init__(self)
        name = self.__class__.__name__.lower()
        self.log = logging.getLogger("zen.localserver.%s" % (name,))

    def getChild(self, path, request):
        return NotFound()

    def render(self, request):
        try:
            response = Resource.render(self, request)
            if isinstance(response, Resource):
                return response.render(request)
            return response
        except Exception:
            return ErrorResponse(
                INTERNAL_SERVER_ERROR, "unexpected problem"
            ).render(request)
