##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

class ModelCatalogError(Exception):
    def __init__(self, message=""):
        if not message:
            message = "Model Catalog internal error"
        super(ModelCatalogError, self).__init__(message)


class ModelCatalogUnavailableError(ModelCatalogError):
    def __init__(self, message = ""):
        if not message:
            message = "Model Catalog not available"
        super(ModelCatalogUnavailableError, self).__init__(message)

class BadIndexingEvent(Exception):
    def __init__(self, message=""):
        if not message:
            message = "Could not index object. Bad indexing event."
        super(BadIndexingEvent, self).__init__(message)