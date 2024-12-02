##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from ..form.schema import Text, TextLine, Int
from ..utils import ZuulMessageFactory as _t
from . import IFacade, IInfo


class IHostInfo(IInfo):
    """
    Read-only set of attributes describing a Control Center host.
    """

    id = TextLine(
        title=_t("ID"),
        description=_t("Globally unique host identifier"),
        readonly=True
    )

    name = TextLine(
        title=_t("Name"),
        description=_t("Name of the host"),
        readonly=True
    )

    poolId = TextLine(
        title=_t("PoolID"),
        description=_t("Name of the pool on which the host is running"),
        readonly=True
    )

    ipAddr = TextLine(
        title=_t("IPAddr"),
        description=_t("IP Address of the host"),
        readonly=True
    )

    cores = Int(
        title=_t("Cores"),
        description=_t("Number of processor cores"),
        readonly=True
    )

    memory = Int(
        title=_t("Memory"),
        description=_t("Memory (bytes) available on the host"),
        readonly=True
    )

    privateNetwork = TextLine(
        title=_t("Private Network"),
        description=_t("Private network of the host"),
        readonly=True
    )

    createdAt = TextLine(
        title=_t("Created At"),
        description=_t("Time host was added"),
        readonly=True
    )

    updatedAt = TextLine(
        title=_t("Updated At"),
        description=_t("Time the host was updated"),
        readonly=True
    )

    kernelVersion = TextLine(
        title=_t("Kernel Version"),
        description=_t("Kernel version of the host OS"),
        readonly=True
    )

    kernelRelease = TextLine(
        title=_t("Kernel Release"),
        description=_t("Kernel release number of the host OS"),
        readonly=True
    )


class IHostFacade(IFacade):
    """
    Interface for managing Zenoss applications.
    """

    def query(self):
        """
        Returns a sequence of IApplication objects.
        """


__all__ = ("IHostFacade", "IHostInfo")
