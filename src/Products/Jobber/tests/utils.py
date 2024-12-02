##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import contextlib
import logging
import sys
import traceback

from urlparse import urlparse

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl


@contextlib.contextmanager
def subTest(**params):
    try:
        yield
    except Exception:
        _, _, tb = sys.exc_info()
        # formatted_tb = ''.join(
        #     traceback.format_list(traceback.extract_tb(tb)[1:]),
        # )
        _, _, fn, _ = traceback.extract_tb(tb, 2)[1]
        print(
            "\n{}\nFAIL: {} ({})\n{}".format(
                "=" * 80,
                fn,
                ", ".join("{}={}".format(k, v) for k, v in params.items()),
                "-" * 80,
            ),
            end="",
        )
        raise


class RedisLayer(object):
    """Test layer to support testing with Redis."""

    db = 13

    @classmethod
    def setUp(cls):
        pass

    @classmethod
    def tearDown(cls):
        pass

    @classmethod
    def testSetUp(cls):
        parsed = urlparse(getRedisUrl())
        url = "redis://{0}/{1}".format(parsed.netloc, cls.db)
        cls.redis = getRedisClient(url)

    @classmethod
    def testTearDown(cls):
        cls.redis.flushdb()
        del cls.redis


class LoggingLayer(object):
    """Test layer to support testing with Python's logging API."""

    @classmethod
    def setUp(cls):
        cls.original_manager = logging.Logger.manager
        cls.manager = logging.Manager(logging.root)
        logging.Logger.manager = cls.manager

    @classmethod
    def tearDown(cls):
        logging.Logger.manager = cls.original_manager
        del cls.manager
        del cls.original_manager
