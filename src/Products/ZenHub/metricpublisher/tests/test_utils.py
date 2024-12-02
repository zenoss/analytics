import logging

from unittest import TestCase
from mock import Mock, create_autospec, patch

from Products.ZenHub.metricpublisher.utils import (
    base64,
    basic_auth_string,
    basic_auth_string_content,
    DelayedMeter,
    exponential_backoff,
    sanitized_float,
)


class UtilsTest(TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)

    def test_exponential_backoff(self):
        sleep_func = Mock()
        func = Mock(__name__="someFunc")
        decorator = exponential_backoff(
            exception=Exception, delay=0.1, maxdelay=5, sleepfunc=sleep_func
        )
        decorated_func = decorator(func)
        result = decorated_func()
        self.assertEqual(result, func.return_value)
        # raise exception when function is called
        # we will loop forever on exception
        # exception_instance = Exception("Boom")
        # func.side_effect = exception_instance
        # decorated_func_error = decorator(func)
        # decorated_func_error()

    @patch(
        "Products.ZenHub.metricpublisher.utils.basic_auth_string_content",
        autospec=True,
        spec_set=True,
    )
    def test_basic_auth_string(self, basic_auth_string_content):
        username = "user"
        password = "pass"
        auth_str = "Authorization: useruser"
        basic_auth_string_content.return_value = username + username
        result = basic_auth_string(username=username, password=password)
        self.assertEqual(result, auth_str)

    def test_basic_auth_string_content(self):
        username = "user"
        password = "pass"
        combine = username + ":" + password
        encoded = base64.b64encode(combine)
        auth_str = "basic {0}".format(encoded)
        result = basic_auth_string_content(
            username=username, password=password
        )
        self.assertEqual(result, auth_str)

    def test_sanitized_float(self):
        # The result of float() and sanitized_float() should match for these.
        float_inputs = [
            100,
            "100",
            "100",
            -100,
            "-100",
            "-100",
            100.1,
            "100.1",
            "100.1",
            -100.1,
            "-100.1",
            "-100.1",
            1e9,
            "1e9",
            "1e9",
            -1e9,
            "-1e9",
            "-1e9",
            1.1e9,
            "1.1e9",
            "1.1e9",
            -1.1e9,
            "-1.1e9",
            "-1.1e9",
        ]

        for value in float_inputs:
            self.assertEqual(sanitized_float(value), float(value))
        # First item in tuple should be normalized to second item.
        normalized_inputs = [
            ("100%", 100.0),
            ("-100%", -100.0),
            ("100.1%", 100.1),
            ("-100.1%", -100.1),
            ("123 V", 123.0),
            ("F123", 123.0),
        ]
        for value, expected_output in normalized_inputs:
            self.assertEqual(sanitized_float(value), expected_output)

        # Bad inputs should result in None.
        bad_inputs = [
            "not-applicable",
        ]
        for value in bad_inputs:
            self.assertEqual(sanitized_float(value), None)
        # make sure we can read exponential values if they have a capital E
        self.assertEqual(
            sanitized_float("3.33333333333333E-5"),
            float("3.33333333333333E-5"),
        )


class DelayedMeterTest(TestCase):
    def setUp(self):
        self.meter = Mock()
        self.delayCount = 100
        self.delayedMeter = DelayedMeter(
            meter=self.meter, delayCount=self.delayCount
        )

    def test___init__(self):
        self.assertEqual(self.delayedMeter._meter, self.meter)
        self.assertEqual(self.delayedMeter._delayCount, self.delayCount)
        self.assertEqual(self.delayedMeter._count, 0)
        self.assertIsNone(self.delayedMeter._pushThread)

    @patch(
        "Products.ZenHub.metricpublisher.utils.eventlet",
        autospec=True,
        spec_set=True,
    )
    def test_mark(self, eventlet):
        value = 2
        # to check all if statements set _delayCount to 1
        self.delayedMeter._delayCount = 1
        self.delayedMeter._pushMark = create_autospec(
            self.delayedMeter._pushMark, spec_set=True
        )
        self.delayedMeter.mark(value=value)
        self.assertEqual(self.delayedMeter._count, value)
        eventlet.spawn_after.assert_called_with(
            10, self.delayedMeter._pushMark
        )
        self.assertEqual(
            self.delayedMeter._pushThread, eventlet.spawn_after.return_value
        )
        self.delayedMeter._pushMark.assert_called_with()

    def test__pushMark(self):
        self.delayedMeter._pushThread = Mock()
        self.delayedMeter._pushMark()
        self.assertEqual(self.delayedMeter._count, 0)
        self.delayedMeter._meter.mark.assert_called_with(
            self.delayedMeter._count
        )
        # can't check if cancel was called on the Thread
        self.assertIsNone(self.delayedMeter._pushThread)
