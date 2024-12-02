##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from zope.interface import implementer

from . import IVersionHistoryCallHomeCollector
from .callhome import REPORT_DATE_KEY, VERSION_HISTORIES_KEY

log = logging.getLogger("zen.callhome")

VERSION_START_KEY = "Version Start"


@implementer(IVersionHistoryCallHomeCollector)
class VersionHistoryCallHomeCollector(object):
    """
    Superclass for version history collectors that provides some basic
    functionality if you provide the code to get the current version.
    """

    def __init__(self, versionedEntity):
        self._entity = versionedEntity

    def addVersionHistory(self, dmd, callHomeData):
        versionHistories = callHomeData.setdefault(VERSION_HISTORIES_KEY, {})
        versionHistory = versionHistories.setdefault(self._entity, {})
        version = self.getCurrentVersion(dmd, callHomeData)
        if version not in versionHistory:
            historyRecord = self.createVersionHistoryRecord(dmd, callHomeData)
            versionHistory[version] = historyRecord

    def getCurrentVersion(self, dmd, callHomeData):
        """
        Implement this to determine the current version.
        Probably available in the callhome data.
        """
        raise NotImplementedError()

    def createVersionHistoryRecord(self, dmd, callHomeData):
        """
        Create a record object with the date.
        """
        reportDate = callHomeData[REPORT_DATE_KEY]
        record = {VERSION_START_KEY: reportDate}
        return record


class KeyedVersionHistoryCallHomeCollector(VersionHistoryCallHomeCollector):
    """
    If version info can be pulled from the callhome data by simple keys,
    then this class handles all the work.
    """

    def __init__(self, versionedEntity, historyRecordKeys=[]):
        super(KeyedVersionHistoryCallHomeCollector, self).__init__(
            versionedEntity
        )
        self._historyRecordKeys = historyRecordKeys

    def createVersionHistoryRecord(self, dmd, callHomeData):
        record = super(
            KeyedVersionHistoryCallHomeCollector, self
        ).createVersionHistoryRecord(dmd, callHomeData)
        if self._historyRecordKeys:
            for hrKey, targetKey in self._historyRecordKeys.iteritems():
                value = self.getKeyedValue(hrKey, callHomeData)
                if value is not None:
                    record[targetKey] = value
        return record

    def getKeyedValue(self, hrKey, callHomeData):
        key_list = hrKey.split(".")
        currObj = callHomeData
        for key in key_list:
            currObj = currObj.get(key, None)
            if currObj is None:
                break
        return currObj


class ZenossVersionHistoryCallHomeCollector(
    KeyedVersionHistoryCallHomeCollector
):
    """ """

    ZENOSS_VERSION_HISTORY_KEY = "Zenoss"
    ZENOSS_VERSION_HISTORY_RECORD_KEYS = {}

    def __init__(self):
        super(ZenossVersionHistoryCallHomeCollector, self).__init__(
            self.ZENOSS_VERSION_HISTORY_KEY,
            self.ZENOSS_VERSION_HISTORY_RECORD_KEYS,
        )

    def getCurrentVersion(self, dmd, callHomeData):
        return self.getKeyedValue("Zenoss App Data.Zenoss", callHomeData)
