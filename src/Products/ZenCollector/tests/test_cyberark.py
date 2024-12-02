##############################################################################
#
# Copyright (C) Zenoss, Inc. 2022, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import httplib

from unittest import TestCase
from mock import call, Mock, patch
from twisted.internet.interfaces import IOpenSSLClientConnectionCreator
from zope.interface.verify import verifyObject

from Products.ZenCollector.cyberark import (
    _CFG_QUERY,
    _CFG_URL,
    _CFG_PORT,
    _CFG_CERT_PATH,
    _default_config,
    _cyberark_flag,
    get_cyberark,
    load_certificates,
    CyberArk,
    CyberArkManager,
    CyberArkClient,
    CyberArkProperty,
)

PATH = {"src": "Products.ZenCollector.cyberark"}


class TestFunctions(TestCase):
    def setUp(t):
        t.log_patcher = patch("{src}.log".format(**PATH), autospec=True)
        t.log = t.log_patcher.start()
        t.addCleanup(t.log_patcher.stop)

        t.getGlobalConfiguration_patcher = patch(
            "{src}.getGlobalConfiguration".format(**PATH),
            name="getGlobalConfiguration",
            autospec=True,
        )
        t.getGlobalConfiguration = t.getGlobalConfiguration_patcher.start()
        t.addCleanup(t.getGlobalConfiguration_patcher.stop)

    def test_get_cyberark_no_config(t):
        config_mock = {}
        t.getGlobalConfiguration.return_value = config_mock

        result = get_cyberark()
        t.assertIsNone(result)
        t.log.info.assert_called_once_with(
            "CyberArk unavailable. No configuration found.",
        )

    @patch("{src}.CyberArk".format(**PATH), autospec=True)
    def test_get_cyberark_failed(t, _cyberark):
        t.getGlobalConfiguration.return_value = {
            "cyberark-url": "https://vault",
        }
        _cyberark.from_dict.side_effect = Exception("boom")

        result = get_cyberark()
        t.assertIsNone(result)
        t.log.exception.assert_called_once_with(
            "CyberArk failed to initialize",
        )

    @patch("{src}.load_certificates".format(**PATH))
    def test_get_cyberark_bad_certs(t, _load_certs):
        t.getGlobalConfiguration.return_value = {
            "cyberark-url": "https://vault",
        }
        _load_certs.side_effect = Exception("boom")

        result = get_cyberark()
        t.assertIsNone(result)
        t.log.exception.assert_called_once_with(
            "CyberArk failed to initialize",
        )

    @patch("{src}.CyberArkManager".format(**PATH), autospec=True)
    def test_get_cyberark_success(t, _manager):
        t.getGlobalConfiguration.return_value = {
            "cyberark-url": "https://vault",
            "cyberark-query": "/foo",
        }
        _manager.from_dict.return_value = _manager

        result = get_cyberark()
        t.assertIsInstance(result, CyberArk)
        t.assertIs(result._manager, _manager)
        t.assertEqual(result._base_query, "/foo")


class TestCyberArk(TestCase):
    class Conf(object):
        def __init__(self, query):
            self.configId = "dev1"
            self.zProp1 = "value1"
            self.zProp2 = "%s?h=g" % query

    def setUp(t):
        t.log_patcher = patch("{src}.log".format(**PATH), autospec=True)
        t.log = t.log_patcher.start()
        t.addCleanup(t.log_patcher.stop)

        t.queryUtility_patcher = patch(
            "{src}.queryUtility".format(**PATH),
            autospec=True,
        )
        t.queryUtility = t.queryUtility_patcher.start()
        t.addCleanup(t.queryUtility_patcher.stop)

        t.client = Mock(spec=CyberArkClient)
        t.manager = CyberArkManager(100, t.client)

    @patch("{src}.CyberArkManager".format(**PATH), autospec=True)
    def test_from_dict(t, _manager):
        query = "/foo/bar"
        conf = {_CFG_QUERY: query}
        mgr = _manager.from_dict.return_value

        vault = CyberArk.from_dict(conf)
        t.assertEqual(vault._base_query, query)
        t.assertEqual(vault._manager, mgr)
        _manager.from_dict.assert_called_once_with(conf)

    def test_update_config_no_value(t):
        query = "/foo/bar"
        vault = CyberArk(query, t.manager)
        conf = t.Conf(query)

        vault.update_config(conf.configId, conf)

        t.assertTrue(getattr(conf, _cyberark_flag, None))
        t.assertEqual(conf.zProp2, "")
        t.assertEqual(conf.zProp1, "value1")

        props = t.manager.getPropertiesFor(conf.configId)
        t.assertEqual(len(props), 1)
        prop = props[0]
        t.assertEqual(prop.deviceId, conf.configId)
        t.assertEqual(prop.name, "zProp2")
        t.assertEqual(prop.value, None)
        t.assertEqual(prop.query, "%s?h=g" % query)

    def test_update_config_has_value(t):
        query = "/foo/bar"
        vault = CyberArk(query, t.manager)
        conf = t.Conf(query)

        status = httplib.OK
        result = """{"Content": "stuff"}"""
        t.client.request.return_value = (status, result)

        vault.update_config(conf.configId, conf)

        t.assertTrue(getattr(conf, _cyberark_flag, None))
        t.assertEqual(conf.zProp2, "stuff")
        t.assertEqual(conf.zProp1, "value1")

        props = t.manager.getPropertiesFor(conf.configId)
        t.assertEqual(len(props), 1)
        prop = props[0]
        t.assertEqual(prop.deviceId, conf.configId)
        t.assertEqual(prop.name, "zProp2")
        t.assertEqual(prop.value, "stuff")
        t.assertEqual(prop.query, "%s?h=g" % query)

    def test_update_config_no_props(t):
        query = "/foo/bar"
        vault = CyberArk(query, t.manager)
        conf = t.Conf(query)
        conf.zProp2 = "value2"

        vault.update_config(conf.configId, conf)

        t.assertFalse(None)
        t.assertFalse(getattr(conf, _cyberark_flag, None))
        t.assertEqual(conf.zProp2, "value2")
        t.assertEqual(conf.zProp1, "value1")

        props = t.manager.getPropertiesFor(conf.configId)
        t.assertEqual(len(props), 0)


class TestCyberArkManager(TestCase):
    def setUp(t):
        t.log_patcher = patch("{src}.log".format(**PATH), autospec=True)
        t.log = t.log_patcher.start()
        t.addCleanup(t.log_patcher.stop)

        t.queryUtility_patcher = patch(
            "{src}.queryUtility".format(**PATH),
            autospec=True,
        )
        t.queryUtility = t.queryUtility_patcher.start()
        t.addCleanup(t.queryUtility_patcher.stop)

    def test_add(t):
        client = Mock(spec=CyberArkClient)
        ttl = 100
        devId = "thedevice"
        zprop = "password"
        query = _default_config[_CFG_QUERY] + "foo&safe=Test&object=bar"
        mgr = CyberArkManager(ttl, client)

        mgr.add(devId, zprop, query)

        props = mgr.getPropertiesFor(devId)
        t.assertEqual(len(props), 1)

        prop = props[0]
        t.assertEqual(prop.deviceId, devId)
        t.assertEqual(prop.name, zprop)
        t.assertEqual(prop.query, query)
        t.assertIsNone(prop.value)

    def test_update_nominal(t):
        client = Mock(spec=CyberArkClient)
        status = httplib.OK
        result = """{"Content": "stuff"}"""
        client.request.return_value = (status, result)

        ttl = 100
        devId = "thedevice"
        zprop = "password"
        query = _default_config[_CFG_QUERY] + "foo&safe=Test&object=bar"
        mgr = CyberArkManager(ttl, client)
        mgr.add(devId, zprop, query)

        mgr.update(devId)
        client.request.assert_called_once_with(query)
        t.assertEqual("stuff", mgr.getPropertiesFor(devId)[0].value)

    def test_update_from_cache(t):
        client = Mock(spec=CyberArkClient)
        status = httplib.OK
        result = """{"Content": "stuff"}"""
        client.request.return_value = (status, result)

        ttl = 100
        dev1 = "device1"
        dev2 = "device2"
        zprop = "password"
        query = _default_config[_CFG_QUERY] + "foo&safe=Test&object=bar"
        mgr = CyberArkManager(ttl, client)

        mgr.add(dev1, zprop, query)
        mgr.add(dev2, zprop, query)

        mgr.update(dev1)
        mgr.update(dev2)

        client.request.assert_called_once_with(query)
        t.assertEqual("stuff", mgr.getPropertiesFor(dev1)[0].value)
        t.assertEqual("stuff", mgr.getPropertiesFor(dev2)[0].value)

    def test_update_error(t):
        client = Mock(spec=CyberArkClient)
        status = httplib.NOT_FOUND
        result = """{"ErrorCode":"4E", "ErrorMsg":"object not found"}"""
        client.request.return_value = (status, result)

        ttl = 100
        devId = "thedevice"
        zprop = "password"
        query = _default_config[_CFG_QUERY] + "foo&safe=Test&object=bar"
        mgr = CyberArkManager(ttl, client)

        expected = call(
            "Bad CyberArk query  "
            "status=%s %s device=%s zproperty=%s query=%s "
            "ErrorCode=%s ErrorMsg=%s",
            status,
            httplib.responses.get(status),
            devId,
            zprop,
            query,
            "4E",
            "object not found",
        )

        mgr.add(devId, zprop, query)

        mgr.update(devId)
        client.request.assert_called_once_with(query)
        t.assertIsNone(mgr.getPropertiesFor(devId)[0].value)
        actual = t.log.error.mock_calls[0]
        t.assertEqual(expected, actual)

    def test_update_unexpected_error(t):
        client = Mock(spec=CyberArkClient)
        status = httplib.NOT_FOUND
        result = """Unexpected format"""
        client.request.return_value = (status, result)

        ttl = 100
        devId = "thedevice"
        zprop = "password"
        query = _default_config[_CFG_QUERY] + "foo&safe=Test&object=bar"
        mgr = CyberArkManager(ttl, client)

        expected = call(
            "Bad CyberArk query  "
            "status=%s %s device=%s zproperty=%s query=%s "
            "result=%s",
            status,
            httplib.responses.get(status),
            devId,
            zprop,
            query,
            "Unexpected format",
        )

        mgr.add(devId, zprop, query)

        mgr.update(devId)
        client.request.assert_called_once_with(query)
        t.assertIsNone(mgr.getPropertiesFor(devId)[0].value)
        actual = t.log.error.mock_calls[0]
        t.assertEqual(expected, actual)

    def test_update_failure(t):
        client = Mock(spec=CyberArkClient)
        ex = RuntimeError("boom")
        client.request.side_effect = ex

        ttl = 100
        devId = "thedevice"
        zprop = "password"
        query = _default_config[_CFG_QUERY] + "foo&safe=Test&object=bar"
        mgr = CyberArkManager(ttl, client)

        expected = call(
            "Failed to execute CyberArk query - %s  "
            "device=%s zproperty=%s query=%s",
            ex,
            devId,
            zprop,
            query,
        )

        mgr.add(devId, zprop, query)

        mgr.update(devId)
        client.request.assert_called_once_with(query)
        t.assertIsNone(mgr.getPropertiesFor(devId)[0].value)
        actual = t.log.error.mock_calls[0]
        t.assertEqual(expected, actual)


class TestCyberArkClient(TestCase):
    def setUp(t):
        t.log_patcher = patch("{src}.log".format(**PATH), autospec=True)
        t.log = t.log_patcher.start()
        t.addCleanup(t.log_patcher.stop)

        t.load_certificates_patcher = patch(
            "{src}.load_certificates".format(**PATH),
            autospec=True,
        )
        t.load_certificates = t.load_certificates_patcher.start()
        t.addCleanup(t.load_certificates_patcher.stop)

        t.agent_patcher = patch(
            "{src}.client.Agent".format(**PATH),
            autospec=True,
        )
        t.agent = t.agent_patcher.start()
        t.addCleanup(t.agent_patcher.stop)

        t.readBody_patcher = patch(
            "{src}.client.readBody".format(**PATH),
            autospec=True,
        )
        t.readBody = t.readBody_patcher.start()
        t.addCleanup(t.readBody_patcher.stop)

    def test_from_dict(t):
        url = "https://vault"
        port = "443"
        path = "/foo/bar"
        conf = {
            _CFG_URL: url,
            _CFG_PORT: port,
            _CFG_CERT_PATH: path,
        }

        client = CyberArkClient.from_dict(conf)
        t.assertEqual(client.base_url, url)
        t.load_certificates.assert_called_once_with(url, path)

    def test_non_standard_port(t):
        url = "https://vault/alias"
        port = "8443"
        options = Mock()
        client = CyberArkClient(url, port, options)
        t.assertEqual(client.base_url, "https://vault:8443")
        t.assertEqual(client.base_path, "/alias")

    def test_url_normalization(t):
        url = "https://vault:443/alias"
        port = "443"
        options = Mock()
        client = CyberArkClient(url, port, options)
        t.assertEqual(client.base_url, "https://vault")
        t.assertEqual(client.base_path, "/alias")

    def test_no_path(t):
        url = "https://vault"
        port = "443"
        options = Mock()
        client = CyberArkClient(url, port, options)
        t.assertEqual(client.base_url, "https://vault")
        t.assertEqual(client.base_path, "")

    def test_request(t):
        client = CyberArkClient("https://vault", 443, Mock())
        expected_result = t.readBody.return_value
        ag = t.agent.return_value
        expected_code = ag.request.return_value.code

        dfr = client.request("/bar/baz?appid=foo&object=foo")
        code, result = dfr.result
        t.assertEqual(result, expected_result)
        t.assertEqual(code, expected_code)
        ag.request.assert_called_once_with(
            "GET", "https://vault/bar/baz?appid=foo&object=foo", None, None
        )

    def test_request_with_extra_path(t):
        client = CyberArkClient("https://vault/alias", 443, Mock())
        expected_result = t.readBody.return_value
        ag = t.agent.return_value
        expected_code = ag.request.return_value.code

        dfr = client.request("/bar/baz?appid=foo&object=foo")
        code, result = dfr.result
        t.assertEqual(result, expected_result)
        t.assertEqual(code, expected_code)
        ag.request.assert_called_once_with(
            "GET",
            "https://vault/alias/bar/baz?appid=foo&object=foo",
            None,
            None,
        )

    def test_request_failure(t):
        client = CyberArkClient("https://vault", 443, Mock())
        ex = RuntimeError("boom")
        t.agent.return_value.request.side_effect = ex

        dfr = client.request("/bar/baz?appid=foo&object=foo")
        dfr.addErrback(lambda x: x.value)
        t.assertEqual(ex, dfr.result)
        t.log.exception.assert_called_once_with(
            "Request failed  url=%s",
            "https://vault/bar/baz?appid=foo&object=foo",
        )

    def test_readBody_failure(t):
        client = CyberArkClient("https://vault", 443, Mock())
        ex = RuntimeError("boom")

        def go_boom(*args, **kw):
            raise ex

        t.readBody.side_effect = go_boom

        dfr = client.request("/bar/baz?appid=foo&object=foo")
        dfr.addErrback(lambda x: x.value)
        t.assertEqual(ex, dfr.result)
        t.log.exception.assert_called_once_with(
            "Failed to read message body  url=%s",
            "https://vault/bar/baz?appid=foo&object=foo",
        )


class TestCyberArkProperty(TestCase):
    def test_init(t):
        dev = "device1"
        zprop = "prop1"
        query = "/foo/bar?h=g"

        prop = CyberArkProperty(dev, zprop, query)

        t.assertEqual(prop.deviceId, dev)
        t.assertEqual(prop.name, zprop)
        t.assertEqual(prop.query, query)
        t.assertIsNone(prop.value)


# openssl genrsa -aes256 -passout pass:qwerty -out ca.pass.key 4096
# openssl rsa -passin pass:qwerty -in ca.pass.key -out ca.key
# openssl req -new -x509 -days 3650 -key ca.key -out ca.crt
rootCA_crt = """
-----BEGIN CERTIFICATE-----
MIIFazCCA1OgAwIBAgIUbQjJ7ZePquLJ74Wi+WFWJTqChM8wDQYJKoZIhvcNAQEL
BQAwRTELMAkGA1UEBhMCQVUxEzARBgNVBAgMClNvbWUtU3RhdGUxITAfBgNVBAoM
GEludGVybmV0IFdpZGdpdHMgUHR5IEx0ZDAeFw0yMzA4MzAwNzAzNTdaFw0zMzA4
MjcwNzAzNTdaMEUxCzAJBgNVBAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEw
HwYDVQQKDBhJbnRlcm5ldCBXaWRnaXRzIFB0eSBMdGQwggIiMA0GCSqGSIb3DQEB
AQUAA4ICDwAwggIKAoICAQCZlHDhq9m+eBuOgMAqREL3HQk0KJzJatYFSlj1zuFF
zJwDd6Q4LRxEu89PVf3l8xa09WY7Wa1t0NXXqndIzvh5gpha9uJ0I2hiq4IHBjql
8vEMLYeYWVdr9yePeOPF/OHnVRW3YWkj+G+cHgYweMMbWuLoxZHXyM+md5t2SmvH
4YrcgdcPD7Actl9GqIq4AMvqtu+X3W9jDyX6+S5TCgtcKHaBq0r3vSZ4BOn+zlgA
DejIjMyp8ws75vGrrP6aiP++Am4lVHnXV0EB3d1rx/WAH3Kf36uDwuD2+KRNwTVW
KJWkCUHUhp6GyZQT/OkuObROaar1DH3lPale0ka45JJlngFZQxXeHdpG4CSRD8pQ
j3WRGg1bmHx47m9lOaTqtmktjRXzGYNG/0eDwOQEs013unxBUw11gzL44W/AWqC8
Hp3qZp2ZyzSLl+yrkKHcmgj3PpAcWtm/Vu0rMddjtkIIcXXf6nLOkpmDC+S6xIbc
Ksgd6ewy2tyxE5s3eNgKqPj4LJK0ANpDan/pVRpdQb0T5UUeNKCl4EeoZpwsHly6
inltPqqZjwKOxqO037uBbc3gc/qacHBfb8yThm98PPR7A2C4BOwxNMvQ5e2Ey9+o
/w6qJNHOfX6W7YZhuf4OXBBMWj5LKoO/uVImg1fRATpGCwBK4kNqtVszWx6zy4bb
pwIDAQABo1MwUTAdBgNVHQ4EFgQU9lu+gYAb++EtfoAP3djV++c/SrYwHwYDVR0j
BBgwFoAU9lu+gYAb++EtfoAP3djV++c/SrYwDwYDVR0TAQH/BAUwAwEB/zANBgkq
hkiG9w0BAQsFAAOCAgEAKLtUhk7tP0f9fjzc8qnseG+QsmdObJuMd/x7m/h7GOjn
0VqOkE8hRJJXVIIDv8ZssK3d+MNhHKIHuH3bRfFtqopXXOxnLR5FvI4Z9t88po8V
75IreWyqBW2u3fCNzYTgxkqKR2aOc4TN6qTRtAS17BJybbpT8GMu8lQ3ubSAjVY7
CWh3RxXalUw9vGQ9LIzeyASiOWRDXeeEIeuNcwPzXGjssGPQGjbR2Cbes88A3Sf5
By8da/dlZMxQOtlryOgaLKmXg/P3x6DzCmhS2tWfBMQ23ifuegYylFPecqpJw8L7
Atz8TmULt2raWk+rrzcBwcBnx+t5WtFT7SrhEOiBtA5BwWNprLi9XyFqXQBsMpog
t/vSlCT8MmnleCmaXvHk/+xqasHDxaowSibOjJHxrkQzhkSC7atfKc9Qqw8kABAL
ZlaSBRGFs9MIGCIO0crMzYkHlxH9BuORnJDKGYRFzPVgov/QlnrZWoz67G7foj6U
Dt/HXx+taPY1WXjl5f+njgVXnQaEiH6kSfc3GP7zHVW8G/KYXGLdoKjYIn3iOFYr
mZtK7sQdO4g/RVH9arKj6JHlPo6l7b/RybamY0pny4ptiVPv0qq2cgxXMj8s7XeO
Tj65afHGguoEE61o/QbH5I+KDgcCOrIHq7vyjBfH/kQzViqTIBSpajVZ46V99Xc=
-----END CERTIFICATE-----
"""

# openssl req -new -key server.key -out server.csr
# openssl x509 -CAcreateserial -req -days 3650 -in server.csr -CA ca.crt -CAkey ca.key -out server.crt
client_crt = """
-----BEGIN CERTIFICATE-----
MIIFETCCAvkCFHHU+QLzVaIAlzUoRGeFjk9PtLsRMA0GCSqGSIb3DQEBCwUAMEUx
CzAJBgNVBAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRl
cm5ldCBXaWRnaXRzIFB0eSBMdGQwHhcNMjMwODMwMDcwNzIyWhcNMzMwODI3MDcw
NzIyWjBFMQswCQYDVQQGEwJBVTETMBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UE
CgwYSW50ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMIICIjANBgkqhkiG9w0BAQEFAAOC
Ag8AMIICCgKCAgEApZbM2FwREXdRztX/WqIwr3fK1BA5juT/t3aNuT5BVgYtPrJW
7FqoYTUVAcbK662A/yMMpNYTP5lejpEhwuFQXDi3rhNAI6oamhIKfEaZcEvj1VwS
O2JF+FNWl6t0y+gwd6RQTGJcpd5i2aszpc7BTBYjRxG1RQch4Uue5/fx9eD2XgxS
YgbLq6ODa1KVdm2yoWT+Tp8soaWPNFfeTDQrrQcsb5IT+oCclwsMK49z4hK2uxko
Pg7NsvrpLUNNlQCiFoiGdlswdfEumGolKDkS893vLF2pIGhykCGjKbVl+xVAQ6ch
TlkuOH2q91CDnojZwd6pkkPCiSG0v/crIROrGAu8mhKQkkzQ7IMixNLiBEdk9tum
2fCeqVhz/mGp6W5xlKXEIdoLPxtFRHpOI96PGGyHo5GhAIlrqqzUmuRSDnr4Iiyo
vwlX1pmVl1y4WK25oxhExf2qMAOSHH0eA8RhqIulKhbQCYnfwxbgSIBFyWGJR4bD
pyIpPum99RzUUQ5ez848cvK7LiNASeCHoBAeutG0YpXSBTHL+ql/UVLQ7e1yvdV/
sDi1rnztLBPwUK6+To7Kn67eErdbi/50q/rXryF6YGbPsBZ5xVMmX9nleLkqSTSp
PPPWniHm6GBcZPWmAUWauBCa7XmJmdREoRZ1afA+efvpTgTm7/S4+GVvs+0CAwEA
ATANBgkqhkiG9w0BAQsFAAOCAgEAg2XMP4PAM96soOXNKFeihT4ccQvzzVOtMBV4
Cc2OP1Ak5BUGRHRfd9AbjYLyRr5L9EyKJmckwZZtFEcRtZLAabUGYiu2L76wwgw3
uZ3rtkt860N8bj7id9+P8139sIuKnBfnGf7YBp3fbH0GarWFQYyRBehCdsy6FS6o
gV9jmO3NYfXYHX6cR0uYKW9Bv7+xZrJf0+ZHtjwxDNGy3WRyVnTxDChbRFgN5irR
chiRkuOLI4sDa8dc0xrD9WiZ28+PeIiwYfjjHZqresSkOTPB0mzqYMLEDTClrf+M
Q8vW41k0rRvcudousTyrKuMfHxmdC8Ei1OuXjhVQ3nvJnRfWlAqlfSLAcfab0mNb
nptMwzyKDNWJB4aNUDT5RZ4Wbt2Khy9ol9F8STINQ6B71l8/1ORQrZol3QMR/hdu
SCEGu9rpKI+Yti+s0C6IDXU6qDP0kDAzITGrjeBkYSoIj7Tk6L4g1oaZQtQD9Pb8
xF4SAAt+tc7/U7mvLolHTHpvZzxclHLoyyyRDJ2PkMNhcwQcYag/GCm31K42dKU/
Zcsd5ZhlNhxmzipuJjzhqrICXCt+WGEiz0/KlxtHhJYEBrjimPoc6Mhm7Byo+4To
1HHU0t80+sRir1j+waNepTsdEdaNVKVweBu0lem2CU2IMzjkSQRu4UOssvJNTw0Y
hk+hfo0=
-----END CERTIFICATE-----
"""

# openssl genrsa -aes256 -passout pass:ytrewq -out server.pass.key 4096
# openssl rsa -passin pass:ytrewq -in server.pass.key -out server.key
client_pem = """
-----BEGIN RSA PRIVATE KEY-----
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
-----END RSA PRIVATE KEY-----
"""


class TestLoadCertificates(TestCase):
    def setUp(t):
        t.FilePath_patcher = patch(
            "{src}.FilePath".format(**PATH),
            autospec=True,
        )
        t.FilePath = t.FilePath_patcher.start()
        t.addCleanup(t.FilePath_patcher.stop)

        def content(path):
            m = Mock()
            if path.endswith("RootCA.crt"):
                m.getContent.return_value = rootCA_crt
            elif path.endswith("client.crt"):
                m.getContent.return_value = client_crt
            elif path.endswith("client.pem"):
                m.getContent.return_value = client_pem
            return m

        t.FilePath.side_effect = content

    def test_load_certificates(t):
        result = load_certificates("https://vault", "/var/zenoss/cyberark")
        t.assertTrue(verifyObject(IOpenSSLClientConnectionCreator, result))
