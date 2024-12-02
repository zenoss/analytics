##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import mock
import os
from collections import namedtuple

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenModel.zenmib import (
    ZenMib, DumpFileProcessor, MIBFileProcessor, SMIDump, SMIDumpTool
)
from Products.ZenUtils.mib import MIBFile


_dir = os.path.dirname(__file__)
_testmibdir = os.path.abspath(os.path.join(
    _dir, "..", "..", "ZenUtils", "mib", "tests"
))


def _readfile(path):
    with open(path, 'r') as fd:
        return fd.read()


class TestMIBFileProcessor(BaseTestCase):

    def _checkResults(self):
        module = self.dmd.unrestrictedTraverse(
            "/zport/dmd/Mibs/mibs/SMIDUMP01-MIB", None
        )
        self.assertTrue(module is not None)
        self.assertEqual(module.nodeCount(), 4)
        self.assertEqual(module.notificationCount(), 1)
        node_names = set([
            "dumpCount", "smidump01",
            "smidump01Notifications", "smidump01Objects"
        ])
        for node in module.nodes():
            if node.id in node_names:
                node_names.remove(node.id)
        self.assertEqual(len(node_names), 0)
        self.assertEqual(
            module.notifications()[0].id, "smidump01Notification01"
        )

    @mock.patch("Products.ZenModel.zenmib.SMIDumpTool", spec_set=SMIDumpTool)
    def test_MIBFileProcessor(self, mockSMIDumpTool):
        dump_filename = os.path.join(_testmibdir, "SMIDUMP01-MIB.mib.py")
        dump_data = _readfile(dump_filename)
        dump = SMIDump(dump_data)

        mockTool = mock.Mock(spec=SMIDumpTool)
        mockTool.run = mock.Mock(return_value=dump)
        mockSMIDumpTool.return_value = mockTool

        source = os.path.join(_testmibdir, "SMIDUMP01-MIB.mib")
        source_data = _readfile(source)
        expectedMIBFile = MIBFile(source, source_data)

        options = namedtuple(
            "options",
            "mibsdir mibdepsdir path keeppythoncode "
            "pythoncodedir downloaddir extractdir evalSavedPython"
        )
        options.mibsdir = "/opt/zenoss/share/mibs/site"
        options.mibdepsdir = "/opt/zenoss/share/mibs"
        options.path = ""
        options.keeppythoncode = False

        log = logging.getLogger("zen.testzenmib")
        # log.setLevel(logging.DEBUG)
        # log.manager.disable = 0  # re-enable log output

        processor = MIBFileProcessor(log, self.dmd, options, [source])
        processor.run()

        mockTool.run.assert_called_with(expectedMIBFile)
        self._checkResults()

    def test_DumpFileProcessor(self):
        dump_filename = os.path.join(_testmibdir, "SMIDUMP01-MIB.mib.py")

        options = namedtuple(
            "options",
            "mibsdir mibdepsdir path keeppythoncode "
            "pythoncodedir downloaddir extractdir evalSavedPython"
        )
        options.mibsdir = "/opt/zenoss/share/mibs/site"
        options.mibdepsdir = "/opt/zenoss/share/mibs"
        options.path = ""
        options.evalSavedPython = [dump_filename]
        options.keeppythoncode = False

        log = logging.getLogger("zen.testzenmib")
        # log.setLevel(logging.DEBUG)
        # log.manager.disable = 0  # re-enable log output

        processor = DumpFileProcessor(log, self.dmd, options, [dump_filename])
        processor.run()

        self._checkResults()


class TestCommitFeature(BaseTestCase):

    def setUp(self):
        # Patching MIBFileProcessor so that nothing actually happens.
        self.mfp_patcher = mock.patch(
            "Products.ZenModel.zenmib.MIBFileProcessor"
        )
        self.commit_patcher = mock.patch("transaction.commit")
        self.mfp_mock = self.mfp_patcher.start()
        self.commit_mock = self.commit_patcher.start()
        self.mfp_instance = mock.Mock()
        self.mfp_mock.return_value = self.mfp_instance

    def tearDown(self):
        self.mfp_patcher.stop()
        self.commit_patcher.stop()

    def test_commit(self):
        check = mock.Mock()
        check.run, check.commit = self.mfp_instance.run, self.commit_mock

        zenmib = ZenMib()
        zenmib.inputArgs = ["/some/mibfile"]
        zenmib.parseOptions()
        zenmib.run()
        self.assertTrue(self.mfp_instance.run.called)
        self.assertTrue(self.commit_mock.called)

        # asserts that processor.run is called before commit
        check.has_calls([mock.call.run(), mock.call.commit()])

    def test_nocommit(self):
        zenmib = ZenMib()
        zenmib.inputArgs = ["--nocommit", "/some/mibfile"]
        zenmib.parseOptions()
        zenmib.log = mock.Mock()  # disable logging
        zenmib.run()
        self.assertTrue(self.mfp_instance.run.called)
        self.commit_mock.assert_not_called()
