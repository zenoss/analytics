import os
import re
import shutil
import tarfile
import urllib
import zipfile

from contextlib import closing
from urlparse import urlsplit, SplitResult

moduleNameMatcher = re.compile(
    r"([A-Z][a-zA-Z0-9-_]+)\s+DEFINITIONS\s+.*?\s*::=\s*BEGIN.+?END", re.DOTALL
)

__all__ = ("MIBFile", "PackageManager", "Package")


class MIBFile(object):
    """A MIB file may contain one or more MIB module definitions.

    This class wraps an open file object and reads its contents.  It will
    not close the file nor write to the file.
    """

    def __init__(self, filename, contents):
        """Initialize an instance of MIBFile.

        @param filename {string} Name of the file containing MIB definitions.
        @param contents {string} Contents of the named file.
        """
        self._filename = filename
        names = tuple(moduleNameMatcher.findall(contents))
        if not names:
            raise ValueError("No MIB definitions found in content")
        self._names = names
        self._reprstr = "<%s %s, module%s %s>" % (
            self.__class__.__name__, self._filename,
            "" if len(self._names) == 1 else "s", ", ".join(self._names)
        )
        self.__hash = hash(self._filename)

    @property
    def filename(self):
        return self._filename

    @property
    def module_names(self):
        """A tuple containing the name of each module definition found
        in the file.
        """
        return self._names

    def __eq__(self, other):
        if type(self) != type(other):
            return NotImplemented
        return self._filename == other._filename

    def __ne__(self, other):
        if type(self) != type(other):
            return NotImplemented
        return self._filename != other._filename

    def __hash__(self):
        return self.__hash

    def __repr__(self):
        return self._reprstr

    def __str__(self):
        return self._filename


def _pathwalker(root):
    """A generator that returns each file in the path given by root.
    """
    for path, _, filenames in os.walk(root):
        for name in filenames:
            yield os.path.join(path, name)


class PRL(object):
    """A PRL is a Package Resource Locator.

    Basically a URL specialized to work with PackageManager.
    """

    def __init__(self, url):
        """
        """
        # urlsplit will parse what it can from the provided string.
        raw = urlsplit(url)

        if not raw.path:
            raise ValueError("Invalid argument for MIB source: %s" % url)

        scheme = raw.scheme
        if not scheme:
            scheme = "file" if not raw.netloc else "http"

        path = raw.path
        if scheme == "file" and not path.startswith("/"):
            path = os.path.abspath("./" + path)

        cooked = SplitResult(scheme, raw.netloc, path, raw.query, raw.fragment)
        self._url = cooked.geturl()
        self._scheme = scheme
        self._path = cooked.path
        self._filename = os.path.split(cooked.path)[-1]

    @property
    def url(self):
        """The URL of the package."""
        return self._url

    @property
    def scheme(self):
        """The scheme of the package's URL."""
        return self._scheme

    @property
    def path(self):
        """The package's full path."""
        return self._path

    @property
    def filename(self):
        """The package's filename."""
        return self._filename


class ZipExtractor(object):

    def challenge(self, source):
        return os.path.isfile(source) and zipfile.is_zipfile(source)

    def extract(self, source, path):
        """Unzip the source file into the given directory path.
        """
        with closing(zipfile.ZipFile(source, 'r')) as zf:
            if zf.testzip() is not None:
                raise ValueError("Zip file %s is corrupted" % source)
            zf.extractall(path)
        return list(_pathwalker(path))


class TarExtractor(object):

    def challenge(self, source):
        return os.path.isfile(source) and tarfile.is_tarfile(source)

    def extract(self, source, path):
        """Extract the source tar file into the target directory.
        """
        with tarfile.open(source, 'r') as tf:
            for info in (mi for mi in tf if mi.isfile()):
                self._write(tf, info, path)
        return list(_pathwalker(path))

    def _write(self, tf, info, path):
        dirname, filename = os.path.split(info.name)
        targetdir = os.path.join(path, dirname)
        if not os.path.exists(targetdir):
            os.mkdir(targetdir)
        elif not os.path.isdir(targetdir):
            raise ValueError(
                "Unable to extract %s; target path, %s, "
                "is not a directory" % (info.name, targetdir)
            )
        targetfile = os.path.join(targetdir, filename)
        with closing(tf.extractfile(info)) as src, \
                open(targetfile, 'w') as sink:
            sink.write(src.read())


class DirectoryExtractor(object):

    def challenge(self, source):
        return os.path.isdir(source)

    def extract(self, source, path):
        """
        """
        return list(_pathwalker(source))


class FileExtractor(object):

    def extract(self, source, path):
        """
        """
        return [source]


_extractors = [ZipExtractor(), TarExtractor(), DirectoryExtractor()]
_fileExtractor = FileExtractor()


class Package(object):

    @classmethod
    def make(cls, source, target):
        """
        """
        for extractor in _extractors:
            if extractor.challenge(source):
                return cls(extractor, source, target)
        else:
            return cls(_fileExtractor, source, target)

    def __init__(self, extractor, source, target):
        """
        """
        self._extractor = extractor
        self._source = source
        self._target = target

    def extract(self):
        """Extracts the package, returns a list of MIBFiles representing
        the files found in the package.
        """
        files = self._extractor.extract(self._source, self._target)
        mibfiles = []
        for pkgfile in files:
            with open(pkgfile, 'r') as f:
                contents = f.read()
                mibfiles.append(MIBFile(pkgfile, contents))
        return mibfiles


class PackageManager(object):
    """
    Given an URL, filename or archive (eg zip, tar), extract the files from
    the package and return a list of filenames.
    """

    def __init__(self, downloaddir, extractdir):
        """
        Initialize the packagae manager.

        @parameter log: logging object
        @type log: logging class object
        @parameter downloaddir: directory name to store downloads
        @type downloaddir: string
        @parameter extractdir: directory name to store downloads
        @type extractdir: string
        """
        self._downloaddir = downloaddir
        self._extractdir = extractdir

    def get(self, source):
        """Return the given source as a Package object.
        """
        prl = PRL(source)
        if prl.scheme != "file":
            if not os.path.exists(self._downloaddir):
                os.makedirs(self._downloaddir)
            # A remote file will not have a 'file' scheme; so retrieve it.
            filepath, _ = urllib.urlretrieve(
                prl.url, os.path.join(self._downloaddir, prl.filename)
            )
            prl = PRL(filepath)

        return Package.make(prl.path, self._extractdir)

    def cleanup(self):
        """
        Remove any clutter left over from the installation.
        """
        if self._downloaddir != "/":
            shutil.rmtree(self._downloaddir)
        if self._extractdir != "/":
            shutil.rmtree(self._extractdir)
