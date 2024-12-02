##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import binascii
import inspect
import os

from AccessControl import ClassSecurityInfo
from decorator import decorator
from ZPublisher import Forbidden


CSRF_TOKEN_NAME = 'CSRF_TOKEN'


class BadCSRFToken(Forbidden):

    """Raised when sent CSRF token doesn't match saved in session one."""


class CSRFTokenView(object):

    """View to provide CSRF tokens for templates.
    Example of usage:
        <input type="hidden" name="csrf_token"
        tal:attributes="value context/csrf_token/token">
    """

    security = ClassSecurityInfo()
    security.declareObjectPublic()

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        raise Forbidden()

    def token(self):
        return get_csrf_token(self.request)


def generate_csrf_token():
    """Returns string with generated CSRF token."""
    return binascii.hexlify(os.urandom(20))


def get_csrf_token(REQUEST):

    """Returns string with CSRF token stored in the session for current user.
    If there is no CSRF token session, generates one and save it to the
    session.
    """
    if not REQUEST.SESSION.has_key(CSRF_TOKEN_NAME):
        REQUEST.SESSION[CSRF_TOKEN_NAME] = generate_csrf_token()

    return REQUEST.SESSION[CSRF_TOKEN_NAME]


def check_csrf_token(REQUEST, csrf_token_field_name='csrf_token'):
    """Checks whether stored in the session CSRF token matches one sent
    in `REQUEST`. If tokens are not equal, raises `BadCSRFToken` exception.
    Otherwise do nothing.
    If `REQUEST` parameter is empty, check is not performed.
    """
    if not REQUEST:
        return

    csrf_token = REQUEST.get(csrf_token_field_name)
    if csrf_token != get_csrf_token(REQUEST):
        raise BadCSRFToken()


def validate_csrf_token(func):
    """Helper decorator for published methods.
    Checks whether stored in the session CSRF token matches one sent
    in `REQUEST` parameter of wrapped method. If tokens are not equal, raises
    `BadCSRFToken` exception. Otherwise invokes wrapped method.
    Wrapped method has to have `REQUEST` parameter.
    """
    args, varargs, kwargs, defaults = inspect.getargspec(func)
    if 'REQUEST' not in args:
        raise ValueError("Method doesn't have REQUEST parameter")
    request_index = args.index('REQUEST')

    @decorator
    def wrapper(func, *args, **kwargs):
        if len(args) > request_index:
            REQUEST = args[request_index]
            check_csrf_token(REQUEST)

        return func(*args, **kwargs)

    return wrapper(func)

