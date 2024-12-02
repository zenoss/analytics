##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest

from zope.interface import implements
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.Zuul.interfaces import IInfo
from Products.Zuul.decorators import decorator, marshalto, marshal
from base import FakeInfo

class Child(FakeInfo):
    implements(IInfo)
    x = '67890'
    notx = 'I should not be included'

class Something(FakeInfo):
    implements(IInfo)
    x = '12345'
    hithere = "I am a banana!"
    def abcde(self):
        return {'a':Child(), 'b':[1, Child()]}
    
@decorator
def reverse(f, *args, **kwargs):
    result = f(*args, **kwargs)
    return result[::-1]

class DecoratorTest(BaseTestCase):
    
    def test_decoratordecorator(self):
        @reverse
        def test():
            "A docstring"
            return "ABCDE"
        self.assertEqual(test.__name__, 'test')
        self.assertEqual(test.__doc__, 'A docstring')
        self.assertEqual(test(), 'EDCBA')
    
    def test_marshalto(self):
        @marshalto(['x', 'abcde'])
        def test():
            return Something()
        result = test()
        self.assert_(isinstance(result, dict))
        self.assertEqual(sorted(result.keys()), ['abcde', 'x'])
        self.assertEqual(result['abcde']['a'].keys(), ['x'])
    
    def test_marshal(self):
        @marshal
        def test():
            return Something()
        result = test()
        self.assert_(isinstance(result, dict))
        self.assertEqual(sorted(result.keys()), ['hithere', 'x'])

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(DecoratorTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
