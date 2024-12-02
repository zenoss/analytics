import logging

from unittest import TestCase

from mock import Mock

from ..oidmap import OidMap


class TestOidMap(TestCase):
    def setUp(t):
        logging.disable(logging.CRITICAL)
        t.app = Mock()
        t.oidmap = OidMap(t.app)

    def tearDown(t):
        logging.disable(logging.NOTSET)

    def test_NoExactMatch(t):
        t.assertEqual(t.oidmap.to_name(".1.2.3.4"), "1.2.3.4")
        t.assertEqual(t.oidmap.to_name(".1.2.3.4", strip=True), "1.2.3.4")

    def test_HasExactMatch(t):
        t.oidmap._oidmap = {"1.2.3.4": "Zenoss.Test.exactMatch"}
        result = t.oidmap.to_name(".1.2.3.4")
        t.assertEqual(result, "Zenoss.Test.exactMatch")
        result = t.oidmap.to_name(".1.2.3.4", strip=True)
        t.assertEqual(result, "Zenoss.Test.exactMatch")

    def test_NoInexactMatch(t):
        t.oidmap._oidmap = {"1.2.3.4": "Zenoss.Test.exactMatch"}
        result = t.oidmap.to_name(".1.5.3.4", exactMatch=False)
        t.assertEqual(result, "1.5.3.4")

    def test_HasInexactMatchNotStripped(t):
        t.oidmap._oidmap = {
            "1.2": "Zenoss",
            "1.2.3": "Zenoss.Test",
            "1.2.3.2": "Zenoss.Test.inexactMatch"
        }
        result = t.oidmap.to_name(".1.2.3.2.5", exactMatch=False)
        t.assertEqual(result, "Zenoss.Test.inexactMatch.5")
        result = t.oidmap.to_name(".1.2.3.2.5.6", exactMatch=False)
        t.assertEqual(result, "Zenoss.Test.inexactMatch.5.6")

    def test_HasInexactMatchStripped(t):
        t.oidmap._oidmap = {
            "1.2": "Zenoss",
            "1.2.3": "Zenoss.Test",
            "1.2.3.2": "Zenoss.Test.inexactMatch"
        }
        result = t.oidmap.to_name(".1.2.3.2.5", exactMatch=False, strip=True)
        t.assertEqual(result, "Zenoss.Test.inexactMatch")
        result = t.oidmap.to_name(".1.2.3.2.5.6", exactMatch=False, strip=True)
        t.assertEqual(result, "Zenoss.Test.inexactMatch")

    def test_AcceptsTuple(t):
        t.assertEqual(t.oidmap.to_name((1, 2, 3, 4)), "1.2.3.4")
