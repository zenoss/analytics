##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009-2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from celery import Celery
from kombu import serialization

from .serialization import without_unicode

# Register custom serializer
serialization.register(
    "without-unicode",
    without_unicode.dump,
    without_unicode.load,
    content_type="application/x-without-unicode",
    content_encoding="utf-8",
)


def _buildapp():
    app = Celery(
        "zenjobs",
        task_cls="Products.Jobber.task:ZenTask",
        config_source="Products.Jobber.config:ZenCeleryConfig",
    )
    return app


app = _buildapp()
