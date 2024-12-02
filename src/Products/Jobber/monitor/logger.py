##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import copy
import logging
import logging.config


def getLogger(obj):
    return logging.getLogger(
        "zen.zenjobs.monitor.{}".format(
            type(obj).__module__.split(".")[-1].lower()
        )
    )


def configure_logging(level=None, filename=None, maxcount=None, maxsize=None):
    config = copy.deepcopy(_logging_config)
    common_handler = config["handlers"]["default"]
    common_handler.update(
        {
            "filename": filename,
            "maxBytes": maxsize,
            "backupCount": maxcount,
        }
    )
    config["loggers"]["zen.zenjobs.monitor"]["level"] = level.upper()
    logging.config.dictConfig(config)


_logging_config = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "default": {
            "format": (
                "%(asctime)s.%(msecs).0f %(levelname)s %(name)s: %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "cloghandler.ConcurrentRotatingFileHandler",
            "filename": None,
            "maxBytes": None,
            "backupCount": None,
            "mode": "a",
            "filters": [],
        },
    },
    "loggers": {
        "zen": {
            "level": "INFO",
            "handlers": ["default"],
        },
        "zen.zenjobs.monitor": {
            "level": "INFO",
        },
    },
    "root": {
        "handlers": [],
    },
}
