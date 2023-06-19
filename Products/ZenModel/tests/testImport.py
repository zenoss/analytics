##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenTestCase.BaseTestCase import BaseTestCase

class TestImportEverything(BaseTestCase):

    def testImportEverything(self):
        import os
        from Products.ZenUtils.path import zenPath
        modules = ['ZenModel', 'ZenRelations', 'ZenRRD', 'ZenUtils',
                   'ZenEvents', 'ZenHub']
        for module in modules:
            for fs, ds, d in os.walk(zenPath('Products', module)):
                for f in fs:
                    if f.endswith('.py'):
                        f = f[-2]
                        __import__('Products.%s.%s' % (module, f))

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestImportEverything))
    return suite
