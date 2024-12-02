import base64
import logging

from struct import pack
from unittest import TestCase

from ..decode import decode_snmp_value


class DecodersUnitTest(TestCase):
    def setUp(t):
        logging.disable(logging.CRITICAL)

    def tearDown(t):
        logging.disable(logging.NOTSET)

    def test_decode_oid(t):
        value = (1, 2, 3, 4)
        t.assertEqual(decode_snmp_value(value), "1.2.3.4")

    def test_decode_utf8(t):
        value = "valid utf8 string \xc3\xa9".encode("utf8")
        t.assertEqual(
            decode_snmp_value(value), value.decode("utf8")
        )

    def test_decode_datetime(t):
        value = pack(">HBBBBBBsBB", 2017, 12, 20, 11, 50, 50, 8, "+", 6, 5)
        t.assertEqual(
            decode_snmp_value(value), "2017-12-20T11:50:50.800+06:05"
        )

    def test_decode_bad_timezone(t):
        value = pack(">HBBBBBBBBB", 2017, 12, 20, 11, 50, 50, 8, 0, 0, 0)
        dttm = decode_snmp_value(value)
        t.assertEqual(dttm[:23], "2017-12-20T11:50:50.800")
        t.assertRegexpMatches(dttm[23:], "^[+-][01][0-9]:[0-5][0-9]$")

    def test_decode_invalid_timezone(t):
        value = pack(">HBBBBBBsBB", 2017, 12, 20, 11, 50, 50, 8, "=", 6, 5)
        t.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_incomplete_datetime(t):
        value = pack(">HBBBBBB", 2017, 12, 20, 11, 50, 50, 8)
        t.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_bad_month_high(t):
        value = pack(">HBBBBBBsBB", 2017, 13, 20, 11, 50, 50, 8, "+", 6, 5)
        t.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_bad_month_low(t):
        value = pack(">HBBBBBBsBB", 2017, 0, 20, 11, 50, 50, 8, "+", 6, 5)
        t.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_bad_day_high(t):
        value = pack(">HBBBBBBsBB", 2017, 12, 32, 11, 50, 50, 8, "+", 6, 5)
        t.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_bad_day_low(t):
        value = pack(">HBBBBBBsBB", 2017, 12, 0, 11, 50, 50, 8, "+", 6, 5)
        t.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_bad_hour(t):
        value = pack(">HBBBBBBsBB", 2017, 12, 20, 24, 50, 50, 8, "+", 6, 5)
        t.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_bad_minute(t):
        value = pack(">HBBBBBBsBB", 2017, 12, 20, 11, 60, 50, 8, "+", 6, 5)
        t.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_bad_second(t):
        value = pack(">HBBBBBBsBB", 2017, 12, 20, 11, 50, 61, 8, "+", 6, 5)
        t.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_leap_second(t):
        value = pack(">HBBBBBBsBB", 2017, 12, 20, 11, 50, 60, 8, "+", 6, 5)
        t.assertEqual(
            decode_snmp_value(value), "2017-12-20T11:50:60.800+06:05"
        )

    def test_decode_bad_decisecond(t):
        value = pack(">HBBBBBBsBB", 2017, 12, 20, 11, 50, 50, 10, "+", 6, 5)
        t.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_value_ipv4(t):
        value = "\xcc\x0b\xc8\x01"
        t.assertEqual(decode_snmp_value(value), "204.11.200.1")

    def test_decode_value_ipv6(t):
        value = "Z\xef\x00+\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08"
        t.assertEqual(decode_snmp_value(value), "5aef:2b::8")

    def test_decode_int_values(t):
        value = int(555)
        t.assertEqual(decode_snmp_value(value), int(555))

    def test_encode_invalid_chars(t):
        value = "\xde\xad\xbe\xef\xfe\xed\xfa\xce"
        t.assertEqual(decode_snmp_value(value), "BASE64:3q2+7/7t+s4=")

    def test_decode_unexpected_object_type(t):
        value = object()
        t.assertEqual(decode_snmp_value(value), None)
