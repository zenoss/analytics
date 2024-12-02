##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest
from itertools import imap
from zope.component import adapts, provideAdapter
from zope.interface import implements, Interface
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.Zuul.interfaces import IInfo
from Products import Zuul
from Products.Zuul import infos
class ITarget(Interface):
    pass


class Target(object):
    implements(ITarget)
    id = "Target"

    def __init__(self):
        self.foo = "foo"
        
    _properties = ( 
        {'id': 'foo', 'type':'int', 'mode':'w'},
        {'id': 'dummyProperty', 'type':'string', 'mode':'w', 'setter': 'setValue'}
       )
    def value(self):
        return 'value'
    
    def setValue(self, value):
        self._value = 'bar'

    def setDummyProperty(self, value):
        self._dummyProperty = value

    
        
class TargetInfo(infos.InfoBase):
    implements(IInfo)
    adapts(ITarget)
            
    @property
    def value(self):
        return self._obj.value()
    
    def dummyProperty(self):
        return 'foo'

    
class InfoTest(BaseTestCase):

    def afterSetUp(self):
        super(InfoTest, self).afterSetUp()
        provideAdapter(TargetInfo)
        target = Target()
        self.info = TargetInfo(target)


    def test_Zuuldotinfo(self):
        isinfo = lambda x:isinstance(x, TargetInfo)

        single = Zuul.info(Target())
        alist = Zuul.info([Target(), Target()])
        adict = Zuul.info({'a':Target(), 'b':Target()})
        nested = Zuul.info([{'a':[Target()], 'b':Target()}])

        self.assert_(isinfo(single))
        self.assert_(isinstance(alist, list))
        for ob in alist:
            self.assert_(isinfo(ob))
        self.assert_(isinstance(adict, dict))
        for k, v in adict.items():
            self.assert_(isinfo(v))
        self.assert_(isinstance(nested, list))
        
def test_suite():
    return unittest.TestSuite((unittest.makeSuite(InfoTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
