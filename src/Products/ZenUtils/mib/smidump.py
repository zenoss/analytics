import logging
import re

from collections import OrderedDict
from itertools import chain
from tempfile import NamedTemporaryFile
from subprocess import Popen, PIPE

MIB_METADATA = re.compile(
    r"(?:\A|})[^}]+?FILENAME\s+=\s+\"(.+?)\".*?MIB\s+=\s+",
    re.DOTALL | re.MULTILINE
)
MIB_DEF = re.compile(r"MIB\s+=\s+")
FILENAME_DEF = re.compile(r"FILENAME\s+=\s+\".*?\"")
DICT_STRING_VALUE = re.compile(r"(:\s*)\"")

log = logging.getLogger("zen.mib")

__all__ = ("SMIConfigFile", "SMIDumpTool", "SMIDump")


class SMIConfigFile(object):
    """
    """

    def __init__(self, path=[]):
        """Initialize an instance of SMIConfigFile.

        @param path {sequence} The paths to put into the config file.
        """
        paths = list(OrderedDict.fromkeys(path))
        if log.getEffectiveLevel() <= logging.DEBUG:
            log.debug(
                "MIB file dependency search path(s): %s", ', '.join(paths)
            )
        self._path = ':'.join(paths)
        self._file = NamedTemporaryFile()
        self._makeConfig()

    def __enter__(self):
        """
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        """
        self.close()

    @property
    def filename(self):
        return self._file.name

    def close(self):
        self._file.close()

    def _makeConfig(self):
        self._file.write("path :%s\n" % self._path)
        self._file.flush()


class SMIDump(object):
    """Returned by SMIDumpTool, objects of this class wrap the output of the
    smidump utility, and exposes methods for manipulating that output.
    """

    def __init__(self, dump):
        """Initialize an instance of SMIDump.

        @param dump {str} The output from SMIDumpTool.
        """
        self._dump = dump

    @property
    def definitions(self):
        """Evaluates the MIB definitions contained in the dump as Python dict
        objects.  This function returns a generator that produces one dict
        object per MIB definition found in the dump.

        @returns {generator -> dict} MIB defs as dict objects
        """
        # Get the offsets from the match of every "FILENAME = ... MIB = "
        # entry in the dump into a flattened list of values, e.g.
        # (s1, e1, s2, e2, s3, e3, ...)
        # where 's' is the start of the match and 'e' is the end of the match.
        offsets = list(chain.from_iterable(
            m.span() for m in MIB_METADATA.finditer(self._dump)
        ))

        # The MIB def is found between e(N) and s(N+1), so regroup the offsets
        # to create pairs that mark the begin and end of MIB definitions, e.g.
        # (s1, e1, s2, e2, ..., sN, eN) -> ((e1, s2), (e2, s3), ..., (eN, L))
        # where 'L' is the offset to the end of the dump string.
        # (note that the first offset is ignored)
        offsets = offsets[1:] + [len(self._dump)-1] if offsets else []
        mib_offsets = map(
            # The 'y' offset will be a '}' character in dumps containing
            # multiple MIB definitions.  To ensure correct offsets, move the
            # offset by one to the position just after the '}' character.
            lambda x, y: (x, y + 1 if self._dump[y] == "}" else y),
            *[iter(offsets)]*2
        )

        # Use the new offset groupings to extract the MIB defintions into
        # their own strings. The offsets specify how to convert one string of:
        #
        #    FILENAME = "..."
        #    MIB = {
        #       ...
        #    }
        #    FILENAME = "..."
        #    MIB = {
        #       ...
        #    }
        #    ...
        #
        # into separate strings of:
        #
        #    {
        #       ...
        #    }
        #
        return (
            # Some MIBs produce values containing character sequences that
            # Python will misinterpret, so prefix dict values with 'r' to make
            # them into 'raw' strings, e.g. "key": "val" -> "key": r"val"
            DICT_STRING_VALUE.sub("\g<1>r\"", buffer(self._dump, bgn, end-bgn))
            for bgn, end in mib_offsets
        )

    @property
    def files(self):
        """Each MIB definition found in the smidump output is associated
        with the filename the MIB definition was originally read from.
        This function returns a generator that produces a series of tuples
        containing the filename as its first element and the contents of the
        file (as a string) as its second element.

        The dump is a string which should have a format like:

            FILENAME = "name"

            MIB = {
                ...
            }

            FILENAME = "name"

            MIB = {
                ...
            }
            ...

        FILENAME identifies the file the MIB declaration that follows came
        from.  This method will group all MIB declarations having the same
        FILENAME to the same string.

        @returns {generator -> (str, str), ...} MIB defs grouped by file
        """
        results = list(MIB_METADATA.finditer(self._dump))

        if not results:
            return ()

        # Store the filenames found in the content
        filenames = [m.groups()[0] for m in results]

        # Retrieve the start offset of every MIB def in the content.
        offsets = list(
            # The start the match will point to a '}' character after the first
            # MIB definition in dumps having more than one definition, so move
            # the start ahead by two characters.  The new start will be the
            # offset just after the '}\n' character sequence.
            m.start() + 2 if m.group().startswith("}") else m.start()
            for m in results
        )

        # Create a grouping where a copy of following value is grouped with
        # the preceding value, e.g.
        #   [0, 1, 2, 3] -> [(0, 1), (1, 2), (2, 3), (3, 4)]
        # The last "following value" is calculated.
        mib_offsets = map(
            lambda x, y: (x, y),
            *[iter(offsets), iter(offsets[1:] + [len(self._dump)])]
        )

        # Associate the offsets with their corresponding filenames.
        metadata = {}
        for name, offsets in zip(filenames, mib_offsets):
            metadata.setdefault(name, []).append(offsets)

        return (
            (name, ''.join(self._dump[bgn:end] for bgn, end in offsets))
            for name, offsets in metadata.iteritems()
        )


def _makeCmdArgs(mibfiles):
    args = []
    mibdefNames = []
    for mibfile in mibfiles:
        args.append(mibfile.filename)
        mibdefNames.extend(mibfile.module_names[:-1])
    args.extend(mibdefNames)
    return args


class SMIDumpTool(object):
    """
    """

    def __init__(self, config=None):
        """
        """
        self._cmd = ['smidump', '--keep-going', '--format', 'python']
        if config:
            self._cmd.extend(["--config", config.filename])

    def run(self, *mibfiles):
        """Takes the given MIBFile objects and returns a string containing
        the output of the 'smidump -f python' command.  If multiple MIBFiles
        are given, the returned string will contain the MIB definitions from
        all of them.
        """
        cmd = list(self._cmd)
        cmd.extend(_makeCmdArgs(mibfiles))
        if log.getEffectiveLevel() <= logging.DEBUG:
            log.debug("Executing command: %s", ' '.join(cmd))

        process = Popen(cmd, stdout=PIPE, stderr=PIPE, close_fds=True)
        output, error = process.communicate()  # blocks until done
        rc = process.poll()

        if rc != 0:
            raise RuntimeError("smidump failed:\n" + error.strip())

        if log.getEffectiveLevel() <= logging.DEBUG:
            for line in (ln.strip() for ln in error.split("\n")):
                if line:
                    log.warn("[smidump] %s", line)

        return SMIDump(output)
