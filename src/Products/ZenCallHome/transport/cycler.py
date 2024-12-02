##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import os
import time

import transaction

from twisted.internet import reactor
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.task import LoopingCall

from Products.Zuul.utils import safe_hasattr

from ..CallHomeStatus import CallHomeStatus
from . import CallHome
from .methods.directpost import direct_post

# number of seconds between metrics updates
GATHER_METRICS_INTERVAL = 60 * 60 * 24 * 30

logger = logging.getLogger("zen.callhome")


class CallHomeCycler(object):
    def __init__(self, dmd):
        self.dmd = dmd
        if not safe_hasattr(dmd, "callHome") or dmd.callHome is None:
            dmd._p_jar.sync()
            _ = CallHome(dmd).callHome  # modifies dmd.  should refactor.
            transaction.commit()
        self.callhome = dmd.callHome
        self.gatherProtocol = None

    def start(self):
        LoopingCall(self.run).start(300, now=False)

    def run(self):
        chs = CallHomeStatus()
        chs.stage(chs.START_CALLHOME)
        try:
            now = int(time.time())
            self.dmd._p_jar.sync()
            # Start metrics gather if needed
            if (
                now - self.callhome.lastMetricsGather > GATHER_METRICS_INTERVAL
                or self.callhome.requestMetricsGather
            ) and not self.gatherProtocol:
                self.gatherProtocol = GatherMetricsProtocol()
                self.callhome.requestMetricsGather = True

            # Update metrics if run complete
            if self.gatherProtocol and (
                self.gatherProtocol.data or self.gatherProtocol.failed
            ):
                chs.stage(chs.GPROTOCOL)
                if not self.gatherProtocol.failed:
                    self.callhome.metrics = self.gatherProtocol.data
                try:
                    chs.stage(chs.GPROTOCOL, "FINISHED")
                    chs.stage(chs.UPDATE_REPORT, "FINISHED")
                    chs.updateStat(
                        "lastTook", int(time.time()) - chs.getStat("startedAt")
                    )
                except Exception as e:
                    logger.warning(
                        "Callhome cycle status update failed: '%r'", e
                    )
                self.callhome.lastMetricsGather = now
                self.callhome.requestMetricsGather = False
                self.gatherProtocol = None

            # Callhome directly if needed
            direct_post(self.dmd)
            chs.stage(chs.START_CALLHOME, "FINISHED")
            transaction.commit()
        except Exception as e:
            chs.stage(chs.START_CALLHOME, "FAILED", str(e))
            logger.warning("Callhome cycle failed: '%r'", e)


class GatherMetricsProtocol(ProcessProtocol):
    def __init__(self):
        import Products.ZenCallHome as _zch

        self.data = None
        self.failed = False
        self.output = []
        self.error = []
        chPath = os.path.join(os.path.dirname(_zch.__file__), "callhome.py")
        reactor.spawnProcess(
            self, "python", args=["python", chPath, "-M"], env=os.environ
        )

    def outReceived(self, data):
        self.output.append(data)

    def errReceived(self, data):
        self.error.append(data)

    def processEnded(self, reason):
        out = "".join(self.output)
        err = "".join(self.error)
        if reason.value.exitCode != 0:
            self.failed = True
            logger.warning(
                (
                    "Callhome metrics gathering failed: "
                    + "stdout: %s, stderr: %s"
                ),
                out,
                err,
            )
        else:
            self.data = out
