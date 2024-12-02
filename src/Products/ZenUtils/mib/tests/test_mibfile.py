##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import mock
import os
import shutil
import tempfile

from unittest import TestCase

from Products.ZenUtils.mib import MIBFile, Package, PackageManager
from Products.ZenUtils.mib.mibfile import (
    PRL, FileExtractor, DirectoryExtractor, TarExtractor, ZipExtractor
)


def _readfile(path):
    with open(path, 'r') as fd:
        return fd.read()


class TestMIBFile(TestCase):

    def test_one_module(self):
        basePath = os.path.dirname(__file__)
        filename = "SMIDUMP01-MIB.mib"
        contents_fname = os.path.join(basePath, filename)
        contents = _readfile(contents_fname)
        mibfile = MIBFile(filename, contents)

        self.assertEqual(mibfile.filename, filename)
        self.assertSequenceEqual(mibfile.module_names, ["SMIDUMP01-MIB"])

    def test_n_modules(self):
        basePath = os.path.dirname(__file__)
        filename = "multi.mib"
        contents_fname = os.path.join(basePath, filename)
        contents = _readfile(contents_fname)
        mibfile = MIBFile(filename, contents)

        self.assertEqual(mibfile.filename, filename)
        self.assertSequenceEqual(
            mibfile.module_names, ["SMIDUMP01-MIB", "SMIDUMP02-MIB"]
        )

    def test_no_modules(self):
        with self.assertRaises(ValueError):
            MIBFile("whatever", "")

    def test_equality(self):
        basePath = os.path.dirname(__file__)
        filename = "SMIDUMP01-MIB.mib"
        contents_fname = os.path.join(basePath, filename)
        contents = _readfile(contents_fname)
        mibfile1 = MIBFile(filename, contents)
        mibfile2 = MIBFile(filename, contents)

        self.assertEqual(mibfile1, mibfile2)
        self.assertEqual(hash(mibfile1), hash(mibfile2))

    def test_inequality(self):
        basePath = os.path.dirname(__file__)
        filename1 = "SMIDUMP01-MIB.mib"
        contents1_fname = os.path.join(basePath, filename1)
        contents1 = _readfile(contents1_fname)
        filename2 = "SMIDUMP02-MIB.mib"
        contents2_fname = os.path.join(basePath, filename2)
        contents2 = _readfile(contents2_fname)
        mibfile1 = MIBFile(filename1, contents1)
        mibfile2 = MIBFile(filename2, contents2)

        self.assertNotEqual(mibfile1, mibfile2)
        self.assertNotEqual(hash(mibfile1), hash(mibfile2))

    def test_repr(self):
        basePath = os.path.dirname(__file__)
        filename = "SMIDUMP01-MIB.mib"
        contents_fname = os.path.join(basePath, filename)
        contents = _readfile(contents_fname)
        mibfile = MIBFile(filename, contents)

        expected_repr = "<MIBFile %s, module SMIDUMP01-MIB>" % filename
        self.assertIsNotNone(repr(mibfile))
        self.assertEqual(repr(mibfile), expected_repr)

    def test_str(self):
        basePath = os.path.dirname(__file__)
        filename = "SMIDUMP01-MIB.mib"
        contents_fname = os.path.join(basePath, filename)
        contents = _readfile(contents_fname)
        mibfile = MIBFile(filename, contents)

        self.assertIsNotNone(str(mibfile))
        self.assertEqual(str(mibfile), filename)


class TestPRL(TestCase):

    def test_noscheme(self):
        path = "/path/to/file.txt"
        prl = PRL(path)
        self.assertEqual(prl.url, "file://" + path)
        self.assertEqual(prl.scheme, "file")
        self.assertEqual(prl.path, "/path/to/file.txt")
        self.assertEqual(prl.filename, "file.txt")

    def test_noscheme_nonroot(self):
        path = "path/to/file.txt"
        curdir = os.getcwd()
        prl = PRL(path)
        expected_path = curdir + "/" + path
        self.assertEqual(prl.url, "file://" + expected_path)
        self.assertEqual(prl.scheme, "file")
        self.assertEqual(prl.path, expected_path)
        self.assertEqual(prl.filename, "file.txt")

    def test_file(self):
        url = "file:///path/to/file.txt"
        prl = PRL(url)
        self.assertEqual(prl.url, url)
        self.assertEqual(prl.scheme, "file")
        self.assertEqual(prl.path, "/path/to/file.txt")
        self.assertEqual(prl.filename, "file.txt")

    def test_http(self):
        url = "http://server.com/path/to/file.txt"
        prl = PRL(url)
        self.assertEqual(prl.url, url)
        self.assertEqual(prl.scheme, "http")
        self.assertEqual(prl.path, "/path/to/file.txt")
        self.assertEqual(prl.filename, "file.txt")

    def test_url_no_scheme(self):
        url = "//server.com/path/to/file.txt"
        prl = PRL(url)
        self.assertEqual(prl.url, "http:" + url)
        self.assertEqual(prl.scheme, "http")
        self.assertEqual(prl.path, "/path/to/file.txt")
        self.assertEqual(prl.filename, "file.txt")

    def test_no_path(self):
        url = "http://server.com"
        with self.assertRaises(ValueError):
            PRL(url)


class TestFileExtractor(TestCase):

    def test_nominal(self):
        extractor = FileExtractor()
        filename = "file.txt"
        expected = [filename]
        result = extractor.extract(filename, "/some/path")
        self.assertSequenceEqual(result, expected)


class TestDirectoryExtractor(TestCase):

    def test_is_dir(self):
        extractor = DirectoryExtractor()
        directory = os.path.dirname(__file__)
        self.assertTrue(extractor.challenge(directory))

    def test_is_not_dir(self):
        extractor = DirectoryExtractor()
        self.assertFalse(extractor.challenge(__file__))

    def test_not_empty(self):
        extractor = DirectoryExtractor()
        directory = os.path.dirname(__file__)
        self.assertNotEqual(len(extractor.extract(directory, "/path")), 0)

    def test_empty(self):
        extractor = DirectoryExtractor()
        directory = tempfile.mkdtemp()
        try:
            self.assertEqual(len(extractor.extract(directory, "/path")), 0)
        finally:
            shutil.rmtree(directory)


class TestZipExtractor(TestCase):

    def test_non_zipfile_challenge(self):
        extractor = ZipExtractor()
        self.assertFalse(extractor.challenge(__file__))

    def test_zipfile_challenge(self):
        extractor = ZipExtractor()
        filepath = os.path.join(os.path.dirname(__file__), "mibfile.zip")
        self.assertTrue(extractor.challenge(filepath))

    def test_extraction(self):
        extractor = ZipExtractor()
        filepath = os.path.join(os.path.dirname(__file__), "mibfile.zip")
        directory = tempfile.mkdtemp()
        try:
            expected_contents = [os.path.join(directory, "SMIDUMP01-MIB.mib")]
            result = extractor.extract(filepath, directory)
            self.assertSequenceEqual(result, expected_contents)
        finally:
            shutil.rmtree(directory)

    @mock.patch("Products.ZenUtils.mib.mibfile.zipfile.ZipFile")
    def test_bad_zipfile(self, mockZipFile):
        mockZip = mock.Mock()
        mockZipFile.return_value = mockZip
        mockZip.testzip = mock.Mock(return_value=["badzip"])

        extractor = ZipExtractor()
        with self.assertRaises(ValueError):
            extractor.extract("somefile.zip", "/somepath")


class TestTarExtractor(TestCase):

    def test_non_tarfile_challenge(self):
        extractor = TarExtractor()
        self.assertFalse(extractor.challenge(__file__))

    def test_tarfile_challenge(self):
        extractor = TarExtractor()
        filepath = os.path.join(os.path.dirname(__file__), "mibfile.tar")
        self.assertTrue(extractor.challenge(filepath))

    def test_extraction(self):
        extractor = TarExtractor()
        filepath = os.path.join(os.path.dirname(__file__), "mibfile.tar")
        directory = tempfile.mkdtemp()
        try:
            expected_contents = [
                os.path.join(directory, "SMIDUMP01-MIB.mib"),
                os.path.join(directory, "mibs", "SMIDUMP02-MIB.mib")
            ]
            result = extractor.extract(filepath, directory)
            self.assertSequenceEqual(result, expected_contents)
        finally:
            shutil.rmtree(directory)


class TestPackage(TestCase):

    def test_extract(self):
        extract = mock.Mock(return_value=[])
        extractor = FileExtractor()
        extractor.extract = extract

        target = "/ignored/path"

        basePath = os.path.dirname(__file__)
        filename = "SMIDUMP01-MIB.mib"
        source = os.path.join(basePath, filename)

        pkg = Package(extractor, source, target)
        pkg.extract()
        extract.assert_called_once_with(source, target)

    def test_make_from_file(self):
        basePath = os.path.dirname(__file__)
        filename = "SMIDUMP01-MIB.mib"
        source = os.path.join(basePath, filename)
        pkg = Package.make(source, "/ignored/path")
        self.assertIsInstance(pkg._extractor, FileExtractor)

    def test_make_from_directory(self):
        source = tempfile.mkdtemp()
        try:
            pkg = Package.make(source, "/ignored/path")
            self.assertIsInstance(pkg._extractor, DirectoryExtractor)
        finally:
            shutil.rmtree(source)

    def test_make_from_zipfile(self):
        basePath = os.path.dirname(__file__)
        filename = "mibfile.zip"
        source = os.path.join(basePath, filename)
        pkg = Package.make(source, "/ignored/path")
        self.assertIsInstance(pkg._extractor, ZipExtractor)

    def test_make_from_tarfile(self):
        basePath = os.path.dirname(__file__)
        filename = "mibfile.tar"
        source = os.path.join(basePath, filename)
        pkg = Package.make(source, "/ignored/path")
        self.assertIsInstance(pkg._extractor, TarExtractor)


class TestPackageManager(TestCase):

    @mock.patch("Products.ZenUtils.mib.mibfile.urllib.urlretrieve")
    def test_get_local(self, mock_urlretrieve):
        with tempfile.NamedTemporaryFile() as dl, \
                tempfile.NamedTemporaryFile() as ex:
            mgr = PackageManager(dl.name, ex.name)
            pkg = mgr.get("blah")
            mock_urlretrieve.assert_not_called()
            self.assertEqual(pkg._target, ex.name)

    @mock.patch("Products.ZenUtils.mib.mibfile.urllib.urlretrieve")
    def test_get_remote(self, mock_urlretrieve):
        url = "http://server.eng/thefile.tar"
        tmpdir = "/tmp/mib_downloads/"
        expdir = "/tmp/mib_ex/"
        mock_urlretrieve.return_value = (tmpdir + "/thefile.tar", None)
        mgr = PackageManager(tmpdir, expdir)
        pkg = mgr.get(url)
        mock_urlretrieve.assert_called_with(url, tmpdir+"thefile.tar")
        self.assertEqual(pkg._target, expdir)

    def test_cleanup(self):
        dl = tempfile.mkdtemp()
        ex = tempfile.mkdtemp()
        try:
            mgr = PackageManager(dl, ex)
            mgr.cleanup()
            self.assertFalse(os.path.exists(dl))
            self.assertFalse(os.path.exists(ex))
        finally:
            if os.path.exists(dl):
                shutil.rmtree(dl)
            if os.path.exists(ex):
                shutil.rmtree(ex)
