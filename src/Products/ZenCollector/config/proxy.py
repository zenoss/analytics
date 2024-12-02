##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
The config module provides the implementation of the IConfigurationProxy
interface used within Zenoss Core. This implementation provides basic
configuration retrieval services directly from a remote ZenHub service.
"""

import logging

from cryptography.fernet import Fernet
from twisted.internet import defer
from zope.component import queryUtility
from zope.interface import implementer

from ..interfaces import ICollector, IConfigurationProxy

log = logging.getLogger("zen.collector.configurationproxy")


@implementer(IConfigurationProxy)
class ConfigurationProxy(object):
    """
    This implementation of IConfigurationProxy provides basic configuration
    retrieval from the remote ZenHub instance using the remote configuration
    service proxy as specified by the collector's configuration.
    """

    _cipher_suite = None

    def __init__(self, prefs):
        super(ConfigurationProxy, self).__init__()
        self._prefs = prefs
        self._collector = queryUtility(ICollector)

    @defer.inlineCallbacks
    def getPropertyItems(self):
        ref = yield self._collector.getRemoteConfigServiceProxy()
        result = yield ref.callRemote("getConfigProperties")
        log.info("fetched daemon configuration properties")
        props = dict(result)
        defer.returnValue(props)

    @defer.inlineCallbacks
    def getThresholdClasses(self):
        ref = yield self._collector.getRemoteConfigServiceProxy()
        classes = yield ref.callRemote("getThresholdClasses")
        log.info("fetched threshold classes")
        defer.returnValue(classes)

    @defer.inlineCallbacks
    def getThresholds(self):
        ref = yield self._collector.getRemoteConfigServiceProxy()
        try:
            thresholds = yield ref.callRemote("getCollectorThresholds")
            log.info("fetched collector thresholds")
            defer.returnValue(thresholds)
        except Exception:
            log.exception("getThresholds failed")

    @defer.inlineCallbacks
    def getConfigProxies(self, token, deviceIds):
        ref = yield self._collector.getRemoteConfigCacheProxy()

        log.debug("fetching configurations")
        # get options from prefs.options and send to remote
        proxies = yield ref.callRemote(
            "getDeviceConfigs",
            self._prefs.configurationService,
            token,
            deviceIds,
            options=self._prefs.options.__dict__,
        )
        defer.returnValue(proxies)

    @defer.inlineCallbacks
    def getConfigNames(self):
        ref = yield self._collector.getRemoteConfigCacheProxy()

        # log.info("fetching device names")
        names = yield ref.callRemote(
            "getDeviceNames",
            self._prefs.configurationService,
            options=self._prefs.options.__dict__,
        )
        log.info(
            "workerid %s fetched names %s %s",
            self._prefs.options.workerid,
            len(names),
            names,
        )
        defer.returnValue(names)

    @defer.inlineCallbacks
    def _get_cipher_suite(self):
        """
        Fetch the encryption key for this collector from zenhub.
        """
        if self._cipher_suite is None:
            ref = yield self._collector.getRemoteConfigServiceProxy()
            try:
                key = yield ref.callRemote("getEncryptionKey")
                self._cipher_suite = Fernet(key)
            except Exception as e:
                log.warn("remote exception: %s", e)
                self._cipher_suite = None
        defer.returnValue(self._cipher_suite)

    @defer.inlineCallbacks
    def encrypt(self, data):
        """
        Encrypt data using a key from zenhub.
        """
        cipher_suite = yield self._get_cipher_suite()
        encrypted_data = None
        if cipher_suite:
            try:
                encrypted_data = yield cipher_suite.encrypt(data)
            except Exception as e:
                log.warn("exception encrypting data %s", e)
        defer.returnValue(encrypted_data)

    @defer.inlineCallbacks
    def decrypt(self, data):
        """
        Decrypt data using a key from zenhub.
        """
        cipher_suite = yield self._get_cipher_suite()
        decrypted_data = None
        if cipher_suite:
            try:
                decrypted_data = yield cipher_suite.decrypt(data)
            except Exception as e:
                log.warn("exception decrypting data %s", e)
        defer.returnValue(decrypted_data)
