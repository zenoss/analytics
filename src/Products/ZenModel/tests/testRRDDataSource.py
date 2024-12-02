##############################################################################
#
# Copyright (C) Zenoss, Inc. 2021, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenModel.RRDDataSource import RRDDataSource, isPythonDataSource

from .ZenModelBaseTest import ZenModelBaseTest


class _PythonDataSource(RRDDataSource):

    sourcetypes = ("Python",)
    sourcetype = "Python"


class _MyDataSource(_PythonDataSource):

    sourcetypes = ("MyDS",)
    sourcetype = "MyDS"


class TestIsPythonDataSource(ZenModelBaseTest):

    def test_isPythonDataSource_Python(t):
        ds = _PythonDataSource("test")
        t.assertTrue(isPythonDataSource(ds))

    def test_isPythonDataSource_Python_derived(t):
        ds = _MyDataSource("test")
        t.assertTrue(isPythonDataSource(ds))

    def test_isPythonDataSource_not_Python(t):
        ds = RRDDataSource("test")
        ds.sourcetypes = ("COMMAND",)
        ds.sourcetype = ds.sourcetypes[0]
        t.assertFalse(isPythonDataSource(ds))
