##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import math
import tempfile

from cStringIO import StringIO
from twisted.internet import utils, defer

from Products.ZenStatus.nmap.PingResult import parseNmapXmlToDict
from Products.ZenStatus import nmap

log = logging.getLogger("zen.nmap")

MAX_PARALLELISM = 150
DEFAULT_PARALLELISM = 10
MAX_NMAP_OVERHEAD = 0.5  # in seconds
MIN_PING_TIMEOUT = 0.1  # in seconds

_NMAP_BINARY = "/opt/zenoss/bin/nmap"


@defer.inlineCallbacks
def executeNmapForIps(
    ips,
    traceroute=False,
    outputType="xml",
    dataLength=0,
    pingTries=2,
    pingTimeOut=1.5,
    pingCycleInterval=60,
):
    """
    Execute nmap and return its output.
    """
    with tempfile.NamedTemporaryFile(prefix="nmap_ips_") as tfile:
        for ip in ips:
            tfile.write("%s\n" % ip)
        tfile.flush()
        results = yield executeNmapCmd(
            tfile.name,
            traceroute,
            outputType,
            len(ips),
            dataLength,
            pingTries,
            pingTimeOut,
            pingCycleInterval,
        )
        defer.returnValue(results)


@defer.inlineCallbacks
def executeNmapCmd(
    inputFileFilename,
    traceroute=False,
    outputType="xml",
    num_devices=0,
    dataLength=0,
    pingTries=2,
    pingTimeOut=1.5,
    pingCycleInterval=60,
):
    """
    Execute nmap and return its output.
    """
    args = ["-iL", inputFileFilename]  # input file

    args.extend(
        [
            "-sn",  # don't port scan the hosts
            "-PE",  # use ICMP echo
            "-n",  # don't resolve hosts internally
            "--privileged",  # assume we can open raw socket
            "--send-ip",  # don't allow ARP responses
            "-T5",  # "insane" speed
        ]
    )

    if dataLength > 0:
        args.extend(["--data-length", str(dataLength)])

    cycle_interval = pingCycleInterval
    ping_tries = pingTries
    ping_timeout = pingTimeOut

    # Make sure the timeout fits within one cycle.
    if (ping_timeout + MAX_NMAP_OVERHEAD) > cycle_interval:
        ping_timeout = cycle_interval - MAX_NMAP_OVERHEAD

    # Give each host at least that much time to respond.
    args.extend(["--min-rtt-timeout", "%.1fs" % ping_timeout])

    # But not more, so we can be exact with our calculations.
    args.extend(["--max-rtt-timeout", "%.1fs" % ping_timeout])

    # Make sure we can safely complete the number of tries within one cycle.
    if (ping_tries * ping_timeout + MAX_NMAP_OVERHEAD) > cycle_interval:
        ping_tries = int(
            math.floor((cycle_interval - MAX_NMAP_OVERHEAD) / ping_timeout)
        )
    args.extend(["--max-retries", "%d" % (ping_tries - 1)])

    # Try to force nmap to go fast enough to finish within one cycle.
    min_rate = int(
        math.ceil(num_devices / (1.0 * cycle_interval / ping_tries))
    )
    args.extend(["--min-rate", "%d" % min_rate])

    if num_devices > 0:
        min_parallelism = int(
            math.ceil(2 * num_devices * ping_timeout / cycle_interval)
        )
        if min_parallelism > MAX_PARALLELISM:
            min_parallelism = MAX_PARALLELISM
        if min_parallelism > DEFAULT_PARALLELISM:
            args.extend(["--min-parallelism", "%d" % min_parallelism])

    if traceroute:
        args.append("--traceroute")
        # FYI, all bets are off as far as finishing within the cycle interval.

    if outputType != "xml":
        raise ValueError("Unsupported nmap output type: %s" % outputType)
    args.extend(["-oX", "-"])  # outputXML to stdout

    # execute nmap
    if log.isEnabledFor(logging.DEBUG):
        log.debug("executing nmap %s", " ".join(args))
    args = ["-n", _NMAP_BINARY] + args
    log.debug("Executing /bin/sudo %s", " ".join(args))
    out, err, exitCode = yield utils.getProcessOutputAndValue(
        "/bin/sudo", args
    )

    if exitCode != 0:
        input = open(inputFileFilename).read()
        log.debug("input file: %s", input)
        log.debug("stdout: %s", out)
        log.debug("stderr: %s", err)
        raise nmap.NmapExecutionError(
            exitCode=exitCode, stdout=out, stderr=err, args=args
        )

    try:
        nmapResults = parseNmapXmlToDict(StringIO(out))
        log.debug("nmapResults -> %s", nmapResults)
        defer.returnValue(nmapResults)
    except Exception as e:
        input = open(inputFileFilename).read()
        log.debug("input file: %s", input)
        log.debug("stdout: %s", out)
        log.debug("stderr: %s", err)
        log.exception(e)
        raise nmap.NmapExecutionError(
            exitCode=exitCode, stdout=out, stderr=err, args=args
        )
