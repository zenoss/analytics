##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os.path

from mock import MagicMock, Mock, create_autospec, patch

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenReports.ReportLoader import ReportLoader, Report


class ReportLoaderTest(BaseTestCase):
    def setUp(self):
        self.rp_load = ReportLoader()

    def test_loadDatabase(self):
        self.rp_load.loadAllReports = create_autospec(
            self.rp_load.loadAllReports
        )
        self.rp_load.loadDatabase()
        self.rp_load.loadAllReports.assert_called_once_with()

    @patch(
        "Products.ZenReports.ReportLoader.transaction.commit",
        autospec=True,
        spec_set=True,
    )
    def test_loadAllReports(self, commit):
        import Products.ZenReports as _zr

        repdir = os.path.join(
            os.path.dirname(_zr.__file__), self.rp_load.options.dir
        )
        self.rp_load.loadDirectory = create_autospec(
            self.rp_load.loadDirectory
        )
        self.rp_load.loadAllReports()
        self.rp_load.loadDirectory.assert_called_once_with(repdir)
        commit.assert_called_once_with()

    def test_loadAllReports_zp(self):
        self.rp_load.options.zenpack = True
        self.rp_load.getZenPackDirs = create_autospec(
            self.rp_load.getZenPackDirs
        )
        self.rp_load.loadAllReports()
        self.rp_load.getZenPackDirs.assert_called_once_with(
            self.rp_load.options.zenpack
        )

    def test_getZenPackDirs(self):
        zp_name = "test_zp"
        zp_path = "/path/to/test_zp"
        zp_obj = Mock(id="test_zp")
        zp_obj.path = Mock(return_value=zp_path)
        self.rp_load.dmd.ZenPackManager.packs = create_autospec(
            self.rp_load.dmd.ZenPackManager.packs, return_value=[zp_obj]
        )
        self.rp_load.options.dir = "reports"
        zp_dir_result = ["/path/to/test_zp/reports"]
        result = self.rp_load.getZenPackDirs(name=zp_name)
        self.assertEqual(result, zp_dir_result)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

    def test_getZenPackDirs_error(self):
        zp_name = "noname_zp"
        zp_path = "/path/to/test_zp"
        zp_obj = Mock(id="test_zp")
        zp_obj.path = Mock(return_value=zp_path)
        self.rp_load.dmd.ZenPackManager.packs = create_autospec(
            self.rp_load.dmd.ZenPackManager.packs, return_value=[zp_obj]
        )
        self.rp_load.options.dir = "reports"
        # set loglevel to 50(CRITICAL) this will remove error log
        self.rp_load.log.setLevel("CRITICAL")
        with self.assertRaises(SystemExit) as exc:
            self.rp_load.getZenPackDirs(name=zp_name)
        self.assertEqual(exc.exception.code, 1)

    @patch(
        "Products.ZenReports.ReportLoader.os.walk",
        autospec=True,
        spec_set=True,
    )
    def test_reports(self, walk):
        rp_dir = "/path/to/test_zp/reports/SomeReports"
        os_walk_data = [(rp_dir, [], ["reportName.rpt"])]
        walk.return_value = os_walk_data
        ret_data = [
            (
                "/SomeReports",
                "reportName",
                "/path/to/test_zp/reports/SomeReports/reportName.rpt",
            )
        ]
        result = self.rp_load.reports(rp_dir)
        self.assertEqual(result, ret_data)

    def test_unloadDirectory(self):
        rp_dir = "/path/to/test_zp/reports/SomeReports"
        orgpath = "/SomeReports"
        rp_id = "reportName"
        report_data = [
            (
                orgpath,
                rp_id,
                "/path/to/test_zp/Reports/SomeReports/reportName.rpt",
            )
        ]
        rorg = Mock(id=rp_id)
        rorg_parent = Mock(id="Reports")
        setattr(rorg, rp_id, True)
        rorg._delObject = Mock()
        rorg.objectValues = Mock(return_value=False)
        rorg.getPrimaryParent = Mock(return_value=rorg_parent)
        self.rp_load.dmd.Reports.createOrganizer = Mock(return_value=rorg)
        self.rp_load.reports = Mock(return_value=report_data)

        self.rp_load.unloadDirectory(repdir=rp_dir)

        self.rp_load.dmd.Reports.createOrganizer.assert_called_once_with(
            orgpath
        )
        rorg._delObject.assert_called_with(rp_id)
        rorg.objectValues.assert_called_once_with()
        rorg.getPrimaryParent.assert_called_once_with()

    def test_unloadDirectory_false(self):
        """test that _delObject method was not called"""
        rp_dir = "/path/to/test_zp/reports/SomeReports"
        orgpath = "/SomeReports"
        rp_id = "reportName"
        report_data = [
            (
                orgpath,
                rp_id,
                "/path/to/test_zp/Reports/SomeReports/reportName.rpt",
            )
        ]
        rorg = Mock(id="Reports")
        rorg_parent = Mock(id="Reports")
        rorg._delObject = Mock()
        rorg.objectValues = Mock(return_value=False)
        rorg.getPrimaryParent = Mock(return_value=rorg_parent)
        setattr(rorg, rp_id, False)
        self.rp_load.dmd.Reports.createOrganizer = Mock(return_value=rorg)
        self.rp_load.reports = Mock(return_value=report_data)

        self.rp_load.unloadDirectory(repdir=rp_dir)

        rorg._delObject.assert_not_called()

    def test_loadDirectory_force(self):
        full_path = "/path/to/test_zp/Reports/SomeReports/reportName.rpt"
        rp_dir = "/path/to/test_zp/reports/SomeReports"
        orgpath = "/SomeReports"
        rp_id = "reportName"
        report_data = [(orgpath, rp_id, full_path)]
        self.rp_load.options.force = True
        rorg = Mock()
        report = Mock()
        # set that this report is not from zenpack
        report.pack = Mock(return_value=False)
        setattr(rorg, rp_id, report)
        rorg._delObject = Mock()
        rorg.objectValues = Mock(return_value=False)
        self.rp_load.dmd.Reports.createOrganizer = Mock(return_value=rorg)
        self.rp_load.reports = Mock(return_value=report_data)
        self.rp_load.loadFile = create_autospec(self.rp_load.loadFile)

        self.rp_load.loadDirectory(rp_dir)

        self.rp_load.dmd.Reports.createOrganizer.assert_called_once_with(
            orgpath
        )
        rorg._delObject.assert_called_once_with(rp_id)
        self.rp_load.loadFile.assert_called_with(rorg, rp_id, full_path)

    def test_loadDirectory(self):
        """
        Test that _delObject method was not called reports wasn't overwritten.
        """
        full_path = "/path/to/test_zp/Reports/SomeReports/reportName.rpt"
        rp_dir = "/path/to/test_zp/reports/SomeReports"
        orgpath = "/SomeReports"
        rp_id = "reportName"
        report_data = [(orgpath, rp_id, full_path)]
        # force option is False by default, this is for better clarity
        self.rp_load.options.force = False
        rorg = Mock()
        setattr(rorg, rp_id, True)
        rorg._delObject = Mock()
        rorg.objectValues = Mock(return_value=False)
        self.rp_load.dmd.Reports.createOrganizer = Mock(return_value=rorg)
        self.rp_load.reports = Mock(return_value=report_data)
        self.rp_load.loadFile = Mock()

        self.rp_load.loadDirectory(rp_dir)

        rorg._delObject.assert_not_called()
        self.rp_load.loadFile.assert_not_called()

    @patch("__builtin__.open")
    def test_loadFile(self, _open):
        rp_name = "reportName"
        full_rp_path = "/path/to/test_zp/Reports/SomeReports/reportName.rpt"
        report_txt = "some report data"
        file_obj = Mock()
        file_obj.read.return_value = report_txt
        ctx_mgr = MagicMock()
        ctx_mgr.__enter__.return_value = file_obj
        ctx_mgr.__exit__ = Mock(return_value=False)
        _open.return_value = ctx_mgr
        root = Mock()
        root._setObject = Mock()

        rp = self.rp_load.loadFile(root, rp_name, full_rp_path)
        self.assertIsInstance(rp, Report)
        self.assertEqual(rp.id, rp_name)
        root._setObject.assert_called_once_with(rp_name, rp)
