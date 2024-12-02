##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


# Functions to simplify form submission return values.

import transaction

from Products.ZenUtils.jsonutils import json, unjson
from Products.ZenUtils.extdirect.zope.router import ZopeDirectRouter as DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse

class FormResponse(object):
    """
    Builds a response for an Ext form.
    """
    _errors = None
    _redirect = None

    def has_errors(self):
        return bool(self._errors)

    def redirect(self, url):
        self._redirect = url

    def error(self, field_name, error_text):
        if self._errors is None:
            self._errors = {}
        self._errors[field_name] = error_text

    @json
    def get_response(self):
        return {
            'success':  not self.has_errors(),
            'redirect': self._redirect,
            'errors':   self._errors or {}
        }


def form_action(f):
    """
    Decorator for methods that are the targets of Ext form submission.

    Provides transaction rollback, so methods can be used as their own
    validation without harm.
    """
    def inner(*args, **kwargs):
        savepoint = transaction.savepoint()
        result = f(*args, **kwargs)
        if isinstance(result, FormResponse):
            if result.has_errors():
                savepoint.rollback()
            return result.get_response()
        return result
    return inner
