##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.Utils import getDisplayType

class MetaTypeTestObject(object):
    def __init__(self):
        self.meta_type = self.__class__.__name__

class SaneMetaType(object):
    meta_type = 'SaneMetaType'

class NoneMetaType(object):
    meta_type = None

class EmptyMetaType(object):
    meta_type = ''

class UnrelatedMetaType(object):
    meta_type = 'EntirelyUnrelatedMetaType'

class IntegerMetaType(object):
    meta_type = 42

class UnicodeMetaType(object):
    meta_type = unicode('\xc3\xa4\xc3\xb6\xc3\xbc', 'utf-8')

class SelfMetaType(object):
    def __init__(self):
        self.meta_type = self

class TestDisplayType(BaseTestCase):

    def setUp(self):
        pass

    def test_getDisplayType(self):
        testObj = None
        self.assertEqual(getDisplayType(testObj), 'None')

        testObj = 'string!'
        self.assertEqual(getDisplayType(testObj), 'Str')

        testObj = u'string!'
        self.assertEqual(getDisplayType(testObj), 'Unicode')

        testObj = 1
        self.assertEqual(getDisplayType(testObj), 'Int')

        testObj = MetaTypeTestObject()
        self.assertEqual(getDisplayType(testObj), 'MetaTypeTestObject')

        testObj = SaneMetaType()
        self.assertEqual(getDisplayType(testObj), 'SaneMetaType')

        testObj = NoneMetaType()
        self.assertEqual(getDisplayType(testObj), 'NoneMetaType')

        testObj = EmptyMetaType()
        self.assertEqual(getDisplayType(testObj), 'EmptyMetaType')

        testObj = UnrelatedMetaType()
        self.assertEqual(getDisplayType(testObj), 'EntirelyUnrelatedMetaType')

        testObj = IntegerMetaType()
        self.assertEqual(getDisplayType(testObj), '42')

        testObj = UnicodeMetaType()
        self.assertEqual(getDisplayType(testObj), '\xc3\xa4\xc3\xb6\xc3\xbc')

        testObj = SelfMetaType()
        self.assertEqual(getDisplayType(testObj), str(testObj))


def test_suite():
    return unittest.makeSuite(TestDisplayType)
