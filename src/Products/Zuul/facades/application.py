##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
from zope.component import getUtility
from zope.interface import implementer

from Products.ZenUtils.application import IApplicationManager
from Products.Zuul.interfaces import IApplicationFacade

LOG = logging.getLogger("Zuul.facades")


@implementer(IApplicationFacade)
class ApplicationFacade(object):
    """
    """
    
    def __init__(self, dataroot):
        """
        """
        self._dmd = dataroot
        self._svc = getUtility(IApplicationManager)

    def getResourcePoolIds(self):
        return ['default']
    
    def query(self, name=None):
        """
        Returns a sequence of application objects.
        """
        result = self._svc.query(name=name, tags=["daemon"])
        if not result:
            return ()
        return tuple(result)

    def queryMasterDaemons(self):
        """
        Return an iterable producing application objects not associated
        with any monitor.
        """
        result = self._svc.query(tags=["daemon", "-collector"])
        if not result:
            return ()
        return tuple(result)

    def queryMonitorDaemons(self, monitorId):
        """
        Return an iterable producing application objects that are
        associated with specified monitor.
        """
        # Get daemons associated with monitor.
        result = self._svc.query(
            monitorName=monitorId, tags=["daemon", "collector"]
        )
        if not result:
            return ()
        return tuple(result)

    def get(self, applicationId, default=None):
        """
        Returns the requested application object.
        """
        app = self._svc.get(applicationId, default)
        if not app:
            return default
        return app

    def getLog(self, appId, lastCount=None):
        """
        Retrieve the log of the identified application.  Optionally,
        a count of the last N lines to retrieve may be given.
        """
        app = self._svc.get(appId)
        if not app:
            raise RuntimeError("No such application '%s'" % (appId,))
        if app.log:
            count = lastCount if lastCount else 200
            return '\n'.join(app.log.last(count))
        else:
            return ''  # not running, so no log.

    def start(self, appId):
        """
        Starts the application.
        """
        app = self._svc.get(appId)
        if app:
            app.start()

    def stop(self, appId):
        """
        Stops the application.
        """
        app = self._svc.get(appId)
        if app:
            app.stop()

    def restart(self, appId):
        """
        Restarts the application.
        """
        app = self._svc.get(appId)
        if app:
            app.restart()

    def updateService(self, appId):
        """
        """
        app = self._svc.get(appId)
        if app:
            app.update()


__all__ = ("ApplicationFacade",)
