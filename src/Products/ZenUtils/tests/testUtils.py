##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, 2013 all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import re
import unittest
import warnings
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.Utils import prepId
from zope.testing.doctestunit import DocTestSuite

class TestUtils(BaseTestCase):

    def testPrepId(self):
        """
        Tests for Utils.prepId()
        Legal values for this test were determined by running existing prepId 
        code.  Note that there are still some corner cases where illegal ids 
        (as defined by /opt/zenoss/lib/python/OFS/ObjectManager.checkValidId())
        can be produced by prepId().
        """
        tests = []

        # Ensure that no legal chars are converted
        prog = re.compile(r'[a-zA-Z0-9-_,.$\(\) ]')
        legals = ''.join(chr(c) for c in xrange(256) if prog.match(chr(c)))
        legals = 'X' + legals   # prevents leading space from being trimmed
        tests.append((legals, legals))

        # Ensure that all illegal chars are converted
        illegals = ''.join(chr(c) for c in xrange(256) if not prog.match(chr(c)))
        tests.append((illegals, "-"))

        # Test various combinations of legals, illegals, and spaces
        tests.extend((
                    ("A", "A"),
                    ("A::A", "A__A"),
                    ("A: :A", "A_ _A"),
                    ("A : A", "A _ A"),
                    ("A A", "A A"),
                    (":A:", "A"),
                    ("::A::", "A"),
                    (" A ", "A"),
                    (": A :", "A"),
                    (u"A\u0100A", "A_A"), # test a unicode character
                    ))

        # The following tests produce illegal ids
        tests.extend((
                    (".", "."),
                    ("..", ".."),
                    ("A:: ", "A__"),
                    (("X__", '-'), "X__"),
                    ("aq_A", "aq_A"),
                    ("REQUEST", "REQUEST"),
                    ))

        for args, expected in tests:
            if not isinstance(args, tuple):
                actual = prepId(args)
            else:
                actual = prepId(*args)
            self.assertEqual(actual, expected, 
                            "prepId('%s') is '%s', should be '%s'" %
                            (args, actual, expected))


def test_suite():
    warnings.filterwarnings( 'ignore' )
    tests = []
    tests.append(unittest.makeSuite(TestUtils))
    tests.append(DocTestSuite('Products.ZenUtils.Utils'))
    tests.append(DocTestSuite('Products.ZenUtils.jsonutils'))
    tests.append(DocTestSuite('Products.ZenUtils.IpUtil'))
    tests.append(DocTestSuite('Products.ZenUtils.Skins'))
    return unittest.TestSuite(tests)

