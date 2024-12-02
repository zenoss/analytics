##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest


from zope.interface import implements, Interface
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.Zuul.form.builder import FormBuilder
import Products.Zuul.form.schema as zs

class ITestObject(Interface):
    foo = zs.Text(title=u"Foo", readonly=True, group="B", order=1)
    baz = zs.TextLine(title=u"Baz", group="A", order=2)

class ITestObjectII(ITestObject):
    bar = zs.Int(title=u"Bar", group="A", xtype="notint", order=1)
    blah = zs.Int(title=u"Blah", group="B", xtype="notint", order=2)
    thing = zs.Entity(title=u"Thing", group="C")
    yoyo = zs.Int(title=u"YoYo", group="C")

class LinkedTo(object):
    uid = '/path/to/ob'

class TestObject(object):
    implements(ITestObjectII)
    foo = 'quux'
    bar = 'spam'
    baz = 'eggs'
    blah = 'pony'
    thing = LinkedTo()

class FormBuilderTest(BaseTestCase):
    def afterSetUp(self):
        super(FormBuilderTest, self).afterSetUp()
        self.fb = FormBuilder(TestObject())

    def test_inherited_schema(self):
        fields = self.fb.fields()
        self.assert_('foo' in fields)
        self.assert_('bar' in fields)
        self.assert_('baz' in fields)

    def test_props(self):
        fields = self.fb.fields()

        self.assert_(fields['foo']['title'] == 'Foo')
        self.assert_(fields['foo']['readonly'] == True)
        self.assert_(fields['foo']['xtype'] == 'textarea')
        self.assert_(fields['baz']['xtype'] == 'textfield')
        self.assert_(fields['bar']['xtype'] == 'notint')

    def test_groups(self):
        groups = self.fb.groups()
        self.assertEqual(sorted(groups.keys()), ['A', 'B', 'C'])
        Anames = [d['name'] for d in groups['A']]
        Bnames = [d['name'] for d in groups['B']]
        self.assert_('bar' in Anames and 'baz' in Anames)
        self.assert_('foo' in Bnames and 'blah' in Bnames)

    def test_order(self):
        groups = self.fb.groups()
        self.assertEqual([d['name'] for d in groups['A']], ['bar', 'baz'])
        self.assertEqual([d['name'] for d in groups['B']], ['foo', 'blah'])

    def test_form(self):
        form = self.fb.render()
        # 3 fieldsets
        items = form['items']
        self.assert_(isinstance(items, list))
        self.assertEqual(len(items), 3)
        for item in items:
            self.assertEqual(item['xtype'], 'fieldset')
            # Each fieldset should have 2 items
            self.assertEqual(len(item['items']), 2)

    def test_value(self):
        fields = self.fb.fields()
        self.assert_(isinstance(self.fb._item(fields['thing'])['value'], LinkedTo))
        self.assertEqual(self.fb._item(fields['yoyo'])['value'], None)

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(FormBuilderTest),))

if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
