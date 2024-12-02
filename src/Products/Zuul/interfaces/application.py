##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from ..form.schema import Text, TextLine, Bool
from ..utils import ZuulMessageFactory as _t
from . import IInfo, IFacade


class IApplicationInfo(IInfo):
    """
    Read-only set of attributes describing a Zenoss application.
    """

    id = TextLine(
        title=_t("ID"),
        description=_t("Identifier of the running service"),
        readonly=True
    )

    description = TextLine(
        title=_t("Description"),
        description=_t("Brief description of the application's function"),
        readonly=True
    )

    autostart = TextLine(
        title=_t("AutoStart"),
        description=_t("True if the application will run on startup"),
        readonly=True
    )

    state = TextLine(
        title=_t("State"),
        description=_t("Current running state of the application"),
        readonly=True
    )

    text = TextLine(
        title=_t("Text"),
        description=_t("Synonym for name."),
        readonly=True
    )

    isRestarting = Bool(
        title=_t("Restarting"),
        description=_t("True if the application is restarting."),
        readonly=True
    )

    uptime = TextLine(
        title=_t("Uptime"),
        description=_t("How long the application been running."),
        readonly=True
    )


class IApplicationConfigurationInfo(IInfo):

    filename = TextLine(
        title=_t("Filename"),
        description=_t("Pathname for log file."),
        readonly=True
    )

    content = Text(
        title=_t("Content"),
        description=_t("The content of the configuration file."),
    )


class IApplicationFacade(IFacade):
    """
    Interface for managing Zenoss applications.
    """

    def query(name=None):
        """
        Returns a sequence of IApplication objects.
        """

    def queryMasterDaemons():
        """
        Return a sequence of IApplication objects representing daemons
        which are not associated with monitors.
        """

    def queryMonitorDaemons(monitorId):
        """
        Return a sequence of IApplication objects that are associated
        with specified monitor.
        """

    def get(appId, default=None):
        """
        Retrieve the IApplication object of the identified application.
        The default argument is returned if the application doesn't exist.
        """

    def getLog(self, appId, lastCount=None):
        """
        Retrieve the log of the identified application.  Optionally,
        a count of the last N lines to retrieve may be given.
        """

    def start(appId):
        """
        Starts the identified application.
        """

    def stop(appId):
        """
        Stops the identified application.
        """

    def restart(appId):
        """
        Restarts the identified application.
        """


__all__ = (
    "IApplicationFacade", "IApplicationInfo",
    "IApplicationConfigurationInfo"
)
