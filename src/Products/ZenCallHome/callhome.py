##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

import logging
import json

from datetime import datetime

from zope.interface import implementer
from zope.component import getUtilitiesFor

from Products.ZenCallHome import (
    ICallHomeCollector,
    IHostData,
    IMasterCallHomeCollector,
    IVersionHistoryCallHomeCollector,
    IZenossData,
    IZenossEnvData,
)
from Products.ZenCallHome.CallHomeStatus import CallHomeStatus
from Products.ZenUtils.ZenScriptBase import ZenScriptBase

log = logging.getLogger("zen.callhome")

ERROR_KEY = "_ERROR_"
EXTERNAL_ERROR_KEY = "errors"
REPORT_DATE_KEY = "Report Date"
VERSION_HISTORIES_KEY = "Version History"


class CallHomeCollector(object):
    def __init__(self, utilityClass):
        self._utilityClass = utilityClass
        self._needsDmd = False

    def generateData(self, dmd=None):
        errors = []
        stats = {}
        args = []
        if self._needsDmd:
            args.append(dmd)
        for name, utilClass in getUtilitiesFor(self._utilityClass):
            try:
                log.debug(
                    "Getting data from %s %s, args: %s",
                    name,
                    utilClass,
                    str(args),
                )
                util = utilClass()
                for key, val in util.callHomeData(*args):
                    log.debug("Data: %s | %s", key, val)
                    if key in stats:
                        # if already a list append, else turn into a list
                        if isinstance(stats[key], list):
                            stats[key].append(val)
                        else:
                            stats[key] = [stats[key], val]
                    else:
                        stats[key] = val
            except Exception as e:
                errorObject = dict(
                    source=utilClass.__name__,
                    key=name,
                    callhome_collector=self.__class__.__name__,
                    exception=str(e),
                )
                log.warn(
                    "Continuing after catching exception while "
                    "generating callhome data for collector "
                    "%(callhome_collector)s (%(source)s:%(key)s : "
                    "%(exception)s",
                    errorObject,
                )
                errors.append(errorObject)
        returnValue = {self._key: stats}
        if errors:
            returnValue[ERROR_KEY] = errors
        return returnValue


@implementer(IMasterCallHomeCollector)
class ZenossDataCallHomeCollector(CallHomeCollector):
    """
    Gathers data from all IZenossData utilities registered
    """

    def __init__(self):
        super(ZenossDataCallHomeCollector, self).__init__(IZenossData)
        self._key = "Zenoss App Data"
        self._needsDmd = True


@implementer(ICallHomeCollector)
class HostDataCallHomeCollector(CallHomeCollector):
    """
    Gathers data from all IHostData utilities registered
    """

    def __init__(self):
        super(HostDataCallHomeCollector, self).__init__(IHostData)
        self._key = "Host Data"


@implementer(IMasterCallHomeCollector)
class ZenossEnvDataCallHomeCollector(CallHomeCollector):
    """
    Gathers data from all IZenossEnvData utilities registered
    """

    def __init__(self):
        super(ZenossEnvDataCallHomeCollector, self).__init__(IZenossEnvData)
        self._key = "Zenoss Env Data"


class CallHomeData(object):
    def __init__(self, dmd=None, master=True):
        self._dmd = dmd
        self._master = master

    def getExistingVersionHistories(self):
        versionHistories = {}
        if self._dmd:
            try:
                metricsString = self._dmd.callHome.metrics
                if metricsString and metricsString.strip():
                    metricsObj = json.loads(metricsString)
                    versionHistories = metricsObj.get(
                        VERSION_HISTORIES_KEY, {}
                    )
            except AttributeError:
                pass
        return {VERSION_HISTORIES_KEY: versionHistories}

    def getData(self):
        data = dict()
        errors = []
        data[REPORT_DATE_KEY] = datetime.utcnow().isoformat()
        data.update(self.getExistingVersionHistories())
        for name, utilClass in getUtilitiesFor(ICallHomeCollector):
            try:
                chData = utilClass().generateData()
                if chData:
                    if ERROR_KEY in chData:
                        errors.extend(chData[ERROR_KEY])
                        del chData[ERROR_KEY]
                    data.update(chData)
            except Exception as e:
                errorObject = dict(
                    callhome_collector=utilClass.__name__,
                    name=name,
                    exception=str(e),
                )
                log.warn(
                    "Caught exception while generating callhome data "
                    "%(callhome_collector)s:%(name)s : %(exception)s",
                    errorObject,
                )
                errors.append(errorObject)
        if self._master:
            for name, utilClass in getUtilitiesFor(IMasterCallHomeCollector):
                try:
                    chData = utilClass().generateData(self._dmd)
                    if chData:
                        if ERROR_KEY in chData:
                            errors.extend(chData[ERROR_KEY])
                            del chData[ERROR_KEY]
                        data.update(chData)
                except Exception as e:
                    errorObject = dict(
                        callhome_collector=utilClass.__name__,
                        name=name,
                        exception=str(e),
                    )
                    log.warn(
                        "Caught exception while generating callhome "
                        "data %(callhome_collector)s:%(name)s : "
                        "%(exception)s",
                        errorObject,
                    )
                    errors.append(errorObject)
        if self._dmd:
            for name, utilClass in getUtilitiesFor(
                IVersionHistoryCallHomeCollector
            ):
                try:
                    utilClass().addVersionHistory(self._dmd, data)
                except Exception as e:
                    errorObject = dict(
                        callhome_collector=utilClass.__name__,
                        name=name,
                        exception=str(e),
                    )
                    log.warn(
                        "Caught exception while adding version "
                        "history: %(callhome_collector)s:%(name)s : "
                        "%(exception)s",
                        errorObject,
                    )
                    errors.append(errorObject)
        if errors:
            data[EXTERNAL_ERROR_KEY] = errors
        return data


class Main(ZenScriptBase):
    def run(self):
        if self.options.status:
            chs = CallHomeStatus()
            print("Status:\t Description:\t Error:\t")
            for i in chs.status():
                print(
                    "{0}\t {1}\t {2}".format(
                        i.get("status"), i.get("description"), i.get("error")
                    )
                )
            return

        if self.options.master:
            log.debug("Connecting...")
            self.connect()
            log.debug("Connected")
        else:
            self.dmd = None

        chs = CallHomeStatus()
        chs.stage(chs.COLLECT_CALLHOME)
        chd = CallHomeData(self.dmd, self.options.master)
        data = chd.getData()
        if self.options.pretty:
            from pprint import pprint

            pprint(data)
        else:
            sort = False
            if self.options.jsonIndent:
                sort = True
            print(
                json.dumps(
                    data, indent=self.options.jsonIndent, sort_keys=sort
                )
            )
        chs.stage(chs.COLLECT_CALLHOME, "FINISHED")

    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZenScriptBase.buildOptions(self)
        self.parser.add_option(
            "-M",
            "--master",
            dest="master",
            default=False,
            action="store_true",
            help="Gather zenoss master data",
        )
        self.parser.add_option(
            "-p",
            dest="pretty",
            default=False,
            action="store_true",
            help="pretty print the output",
        )
        self.parser.add_option(
            "-i",
            "--json_indent",
            dest="jsonIndent",
            help="indent setting for json output",
            default=None,
            type="int",
        )
        self.parser.add_option(
            "-s",
            "--status",
            action="store_true",
            dest="status",
            help="show detail status information",
            default=False,
        )


if __name__ == "__main__":
    main = Main(connect=False)
    main.run()
