##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import math
import os
import platform
import socket
import string

from functools import total_ordering
from subprocess import Popen, PIPE

from zope.interface import implementer

from . import IHostData, IZenossEnvData

log = logging.getLogger("zen.callhome")

LOCAL_HOSTNAMES = [
    "localhost",
    "localhost.localdomain",
    socket.gethostname(),
    socket.getfqdn(),
]


@implementer(IHostData)
class PlatformData(object):
    def callHomeData(self):
        distro = " ".join(platform.linux_distribution())
        processor = platform.processor()
        system = platform.system()
        release = platform.release()
        yield (
            "OS",
            "{distro} {processor} "
            "({system} kernel {release})".format(**locals()),
        )


@implementer(IHostData)
class ProcFileData(object):
    """
    Used to gather proc file  statistics for call home
    """

    _proc_file = None
    _parser = None

    def callHomeData(self):
        """
        @return:: name, value pairs of host stats for call home
        @rtype: list or generator of tuples
        """
        return self._parseProcFile()

    def _parseProcFile(self):
        parser = self._createParser()
        try:
            with open(self._proc_file) as f:
                for line in f:
                    parser.parse(line)
            return parser.output
        except IOError:
            log.debug("Could not read %s", self._proc_file)
            return self._ioErrorOutputHandler()

    def _ioErrorOutputHandler(self):
        return tuple()

    @classmethod
    def _parse_key_value(self, line):
        if not line.strip():
            return None, None
        return [" ".join(word.split()) for word in line.split(":")]

    def _createParser(self):
        return self._parser()


class ProcFileParser(object):
    @classmethod
    def _parse_key_value(cls, line):
        if not line.strip():
            return None, None
        return [" ".join(word.split()) for word in line.split(":")]


class CpuinfoParser(ProcFileParser):
    def __init__(self):
        self._processors = []
        self._processor = None
        self._summaries = None

    def parse(self, line):
        key, value = self._parse_key_value(line)
        if key == "processor":
            self._processor = {}
            self._processors.append(self._processor)
        elif key is not None:
            self._processor[key] = value

    @property
    def output(self):
        if self._summaries is None:
            self._summarize()
        cores = 0
        for tuples, count in self._summaries.items():
            cores += count
            dct = dict(tuples)
            cache_size = convert_kb(dct["cache size"])
            yield (
                "CPU",
                "{dct[model name]} ({cache_size} cache)".format(**locals()),
            )
        yield "CPU Cores", cores

    def _summarize(self):
        """counts each type of CPU from cpuinfo
        processors comes from CpuinfoParser
        return value is a dictionary with tuples of cpuinfo to a count of the
        number of times that cpuinfo shows up in /proc/cpuinfo
        """
        self._summaries = {}
        for processor in self._processors:
            key = tuple(processor.items())
            if key in self._summaries:
                self._summaries[key] += 1
            else:
                self._summaries[key] = 1


class CpuProcFileData(ProcFileData):
    _proc_file = "/proc/cpuinfo"
    _parser = CpuinfoParser

    def _ioErrorOutputHandler(self):
        yield "CPU Cores", "Not available"


class MemoryStat(object):
    def __init__(self, label, total_key, free_key):
        self.label = label
        self._total = [total_key, None]
        self._free = [free_key, None]

    def set(self, key, value):
        for stat in self._total, self._free:
            if key == stat[0]:
                stat[1] = convert_kb(value, key.endswith("Total"))

    def __repr__(self):
        return ("{self._free[1]} of " "{self._total[1]} available").format(
            **locals()
        )


class MeminfoParser(ProcFileParser):
    def __init__(self):
        self._stats = [
            MemoryStat("Memory", "MemTotal", "MemFree"),
            MemoryStat("Swap", "SwapTotal", "SwapFree"),
        ]

    def parse(self, line):
        key, value = self._parse_key_value(line)
        for stat in self._stats:
            stat.set(key, value)

    @property
    def output(self):
        for stat in self._stats:
            yield stat.label, str(stat)


class MemProcFileData(ProcFileData):
    _proc_file = "/proc/meminfo"
    _parser = MeminfoParser

    def _ioErrorOutputHandler(self):
        for stat in self._parser()._stats:
            yield stat.label, "Not available"


class CommandData(object):
    """
    Base class for executing and return data based on executing a command
    """

    _args = []
    _parser = None

    def callHomeData(self):
        """
        @return:: name, value pairs of host stats for call home
        @rtype: list or generator of tuples
        """
        return self._parseCommand()

    def _parseCommand(self):
        try:
            log.debug("Executing command args %s", self._args)
            popen = Popen(self._args, stdout=PIPE, stderr=PIPE)
            stdoutdata, stderrdata = popen.communicate()
            parser = self._createParser()
            for line in stdoutdata.splitlines():
                parser.parse(line.strip())
            return parser.output
        except OSError:
            return self._osErrorOutputHandler()

    def _createParser(self):
        return self._parser()

    def _osErrorOutputHandler(self):
        return tuple()


@total_ordering
class FilesystemInfo(object):
    def __init__(self, mounted_on="", size=None, avail=None):
        self.mounted_on = mounted_on
        self.size = size
        self.avail = avail
        self.supporting = []

    def __eq__(self, other):
        return self.mounted_on == other.mounted_on

    def __ne__(self, other):
        return not (self == other)

    def __lt__(self, other):
        return self.mounted_on < other.mounted_on

    def __repr__(self):
        repr_ = (
            "'{self.mounted_on}', " "{self.avail} of {self.size} available"
        ).format(**locals())
        if self.supporting:
            supporting = ", ".join(self.supporting)
            repr_ = "{repr_} (supports {supporting})".format(**locals())
        return repr_


class DfParser(object):
    def __init__(self):
        self._zenoss_mounts = {
            zenhome.environ_key: "",
            zendshome.environ_key: "",
            rabbitmq_mnesia_base.environ_key: "",
        }
        self._filesystems = []

    def parse(self, line):
        if not line.startswith("/"):
            return
        filesystem, size, used, avail, use_pct, mounted_on = line.split()
        fs_info = FilesystemInfo(
            mounted_on, convert_kb(size), convert_kb(avail, False)
        )

        for environ_var in zenhome, zendshome, rabbitmq_mnesia_base:
            if environ_var.value is not None and environ_var.value.startswith(
                mounted_on
            ):
                key = environ_var.environ_key
                if len(mounted_on) > len(self._zenoss_mounts[key]):
                    fs_info.supporting.append(key)
                    self._zenoss_mounts[key] = fs_info.mounted_on

        self._filesystems.append(fs_info)

    @property
    def output(self):
        for filesystem in self._filesystems:
            yield "Filesystem", str(filesystem)


@implementer(IHostData)
class DfData(CommandData):

    _args = ["df", "-Pk"]
    _parser = DfParser

    def _osErrorOutputHandler(self):
        yield "Filesystem", "Not Available"


@implementer(IHostData)
class HostId(CommandData):
    _args = ["hostid"]

    def __init__(self):
        self._parser = HostId
        self._hostId = None

    def parse(self, line):
        self._hostId = line

    @property
    def output(self):
        yield "Host Id", self._hostId

    def _osErrorOutputHandler(self):
        yield "Host Id", "Not Available"


class RpmParser(object):
    def __init__(self, key):
        self._output = None
        self._key = key

    def parse(self, line):
        self._output = line

    @property
    def output(self):
        label = "RPM"
        if self._key:
            label = "%s - %s" % (label, self._key)
        yield label, self._output


class RPMData(CommandData):
    def __init__(self, rpm_arg):
        super(RPMData, self).__init__()
        self._rpm_arg = rpm_arg
        if os.path.exists("/etc/redhat-release") or os.path.exists(
            "/etc/SuSe-release"
        ):
            self._rpm_support = True
            self._args = ["rpm", "-q", rpm_arg]
        else:
            self._rpm_support = False
            self._args = ["exit", "1"]

    def _createParser(self):
        return RpmParser(self._rpm_arg)

    def _osErrorOutputHandler(self):
        label = "RPM"
        if self._rpm_arg:
            label = "%s - %s" % (label, self._rpm_arg)
        if self._rpm_support:
            value = "Not Available"
        else:
            value = "Not Supported"
        yield label, value


@implementer(IZenossEnvData)
class ZenossRPMData(RPMData):
    def __init__(self):
        super(ZenossRPMData, self).__init__("zenoss")


@implementer(IZenossEnvData)
class ZenDSRPMData(RPMData):
    def __init__(self):
        super(ZenDSRPMData, self).__init__("zends")


@implementer(IZenossEnvData)
class CoreZenpackRPMData(RPMData):
    def __init__(self):
        super(CoreZenpackRPMData, self).__init__("zenoss-core-zenpacks")


@implementer(IZenossEnvData)
class EnterpriseZenpackRPMData(RPMData):
    def __init__(self):
        super(EnterpriseZenpackRPMData, self).__init__(
            "zenoss-enterprise-zenpacks"
        )


class Zenhome(object):

    environ_key = "ZENHOME"

    def __init__(self):
        self.value = os.environ[self.environ_key]

    def generate(self):
        yield self.environ_key, self.value


zenhome = Zenhome()


class Zendshome(object):

    environ_key = "ZENDSHOME"

    @classmethod
    def _get_value(cls):
        if cls.environ_key in os.environ:
            return os.environ[cls.environ_key]

    def __init__(self):
        self.value = self._get_value()

    def generate(self):
        if self.value is not None:
            yield self.environ_key, self.value


zendshome = Zendshome()


class RabbitmqMnesiaBase(object):

    environ_key = "RABBITMQ_MNESIA_BASE"

    @classmethod
    def _get_value(cls):
        zenhome_ = zenhome.value
        with open("{zenhome_}/etc/global.conf".format(**locals())) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                words = [w.strip() for w in line.split()]
                if len(words) == 2 and words[0] == "amqphost":
                    amqphost = words[1]
                    break
            else:
                amqphost = None
        if amqphost in LOCAL_HOSTNAMES:
            return os.environ.get(cls.environ_key, "/var/lib/rabbitmq/mnesia")

    def __init__(self):
        self.value = self._get_value()

    def generate(self):
        if self.value is not None:
            yield self.environ_key, self.value


rabbitmq_mnesia_base = RabbitmqMnesiaBase()


@implementer(IZenossEnvData)
class ZenHomeData(object):
    def callHomeData(self):
        return zenhome.generate()


@implementer(IZenossEnvData)
class ZenDSHomeData(object):
    def callHomeData(self):
        return zendshome.generate()


@implementer(IZenossEnvData)
class RabbitData(object):
    def callHomeData(self):
        return rabbitmq_mnesia_base.generate()


def convert_kb(kb_str, round_up=True):
    units = ["YB", "ZB", "EB", "PB", "TB", "GB", "MB", "KB"]
    quantity = int(kb_str.translate(None, string.ascii_letters))
    # 5 percent fudge factor for rounding up
    while quantity > (1024 - (1024 * 0.05)):
        quantity = quantity / 1024.0
        units.pop()
    unit = units.pop()
    if round_up:
        quantity = int(math.ceil(quantity))
        return "{quantity} {unit}".format(**locals())
    else:
        return "{quantity:.1f} {unit}".format(**locals())
