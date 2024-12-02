##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import datetime
import unittest

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.controlplane.data import (
    ServiceDefinition, ServiceDefinitionFactory,
    ServiceInstance, ServiceInstanceFactory,
    ServiceJsonDecoder
)


definition_json_src = """[{
"ID": "b6b04c70-707d-293f-f78b-88c496656938",
"Name": "zenperfsnmp",
"Context": "null",
"Startup": "su - zenoss -c \\"/opt/zenoss/bin/zenperfsnmp run -c -v10\\"",
"Description": "",
"Tags": [
    "daemon",
    "collector"
],
"ConfigFiles": null,
"Instances": 1,
"ImageID": "zenoss/zenoss5x",
"PoolID": "default",
"DesiredState": 1,
"Launch": "auto",
"Endpoints": [
    {
        "Protocol": "tcp",
        "PortNumber": 8789,
        "Application": "zenhubPB",
        "Purpose": "import"
    },
    {
        "Protocol": "tcp",
        "PortNumber": 6379,
        "Application": "redis",
        "Purpose": "import"
    }
],
"ParentServiceID": "02ef8505-eebd-6493-0c6c-630287847688",
"Volumes": null,
"CreatedAt": "2013-12-12T09:07:51.172715172-06:00",
"UpdatedAt": "2013-12-12T09:30:12.341234232-06:00"
}]
"""

definition_json_obj = {
    "ID": "b6b04c70-707d-293f-f78b-88c496656938",
    "Name": "zenperfsnmp",
    "Context": "null",
    "Startup": "su - zenoss -c \"/opt/zenoss/bin/zenperfsnmp run -c -v10\"",
    "Description": "",
    "Tags": [
        "daemon",
        "collector"
    ],
    "ConfigFiles": None,
    "Instances": 1,
    "ImageID": "zenoss/zenoss5x",
    "PoolID": "default",
    "DesiredState": 1,
    "Launch": "auto",
    "Endpoints": [
        {
            "Protocol": "tcp",
            "PortNumber": 8789,
            "Application": "zenhubPB",
            "Purpose": "import"
        },
        {
            "Protocol": "tcp",
            "PortNumber": 6379,
            "Application": "redis",
            "Purpose": "import"
        }
    ],
    "ParentServiceID": "02ef8505-eebd-6493-0c6c-630287847688",
    "Volumes": None,
    "CreatedAt": "2013-12-12T09:07:51.172715172-06:00",
    "UpdatedAt": "2013-12-12T09:30:12.341234232-06:00"
}

instance_json_src = """[{
"ID": "35948b18-86d5-780d-e9b7-37614e7c1755",
"ServiceID": "0ee72a73-9883-739b-0c92-9d1fd1c55fd2",
"HostID": "007f0101",
"DockerID": "9012fe5973bb3f4648ee94614123ca4da4e1612cbf428695fc555f3abbc238bc",
"StartedAt": "2013-12-13T10:53:05.41346859-06:00",
"Name": "ZenHub",
"Startup": "su - zenoss -c \\"/opt/zenoss/bin/zenhub run -v10\\"",
"Description": "",
"Instances": 1,
"ImageID": "zenoss/zenoss5x",
"PoolID": "default",
"DesiredState": 1,
"ParentServiceID": "0bcc7571-5b3d-6044-2bf6-e783e915e5b9"
}]"""

instance_json_obj = {
    "ID": "35948b18-86d5-780d-e9b7-37614e7c1755",
    "ServiceID": "0ee72a73-9883-739b-0c92-9d1fd1c55fd2",
    "HostID": "007f0101",
    "DockerID": "9012fe5973bb3f4648ee94614123ca4da4e1612cbf428695fc555f3abbc238bc",
    "StartedAt": "2013-12-13T10:53:05.41346859-06:00",
    "Name": "ZenHub",
    "Startup": "su - zenoss -c \"/opt/zenoss/bin/zenhub run -v10\"",
    "Description": "",
    "Instances": 1,
    "ImageID": "zenoss/zenoss5x",
    "PoolID": "default",
    "DesiredState": 1,
    "ParentServiceID": "0bcc7571-5b3d-6044-2bf6-e783e915e5b9"
}


class ServiceObjectFactoryTest(BaseTestCase):
    """
    """

    def test001(self):
        factory = ServiceDefinitionFactory()
        result = factory()
        self.assertTrue(isinstance(result, ServiceDefinition))

    def test002(self):
        factory = ServiceInstanceFactory()
        result = factory()
        self.assertTrue(isinstance(result, ServiceInstance))


class ServiceJsonDecoderTest(BaseTestCase):
    """
    """

    def testDecodeDefinition(self):
        result = ServiceJsonDecoder().decode(definition_json_src)
        self.assertEqual(len(result), 1)
        svcdef = result[0]
        self.assertTrue(isinstance(svcdef, ServiceDefinition))
        self.assertEqual(svcdef.__getstate__(), definition_json_obj)

    def testDecodeInstance(self):
        result = ServiceJsonDecoder().decode(instance_json_src)
        self.assertEqual(len(result), 1)
        svcinst = result[0]
        self.assertTrue(isinstance(svcinst, ServiceInstance))
        self.assertEqual(svcinst.__getstate__(), instance_json_obj)


class ServiceDefinitionTest(BaseTestCase):
    """
    """

    def setUp(self):
        svcdef = ServiceDefinition()
        svcdef.__setstate__(definition_json_obj)
        self.svcdef = svcdef

    def testId(self):
        self.assertEqual(
            self.svcdef.id, "b6b04c70-707d-293f-f78b-88c496656938")

    def testResourceId(self):
        self.assertEqual(
            self.svcdef.resourceId,
            "/services/b6b04c70-707d-293f-f78b-88c496656938"
        )

    def testName(self):
        self.assertEqual(self.svcdef.name, "zenperfsnmp")

    def testDescription(self):
        self.assertEqual(self.svcdef.description, "")

    def testTags(self):
        self.assertEqual(self.svcdef.tags, ["daemon", "collector"])

    def testConfigFiles(self):
        self.assertEqual(self.svcdef.configFiles, None)

    def testDesiredState(self):
        self.assertEqual(
            self.svcdef.desiredState, ServiceDefinition.STATE.RUN)
        self.svcdef.desiredState = ServiceDefinition.STATE.STOP
        self.assertEqual(
            self.svcdef.desiredState, ServiceDefinition.STATE.STOP)
        data = self.svcdef.__getstate__()
        self.assertEqual(data.get("DesiredState"), 0)
        self.svcdef.desiredState = ServiceDefinition.STATE.RESTART
        self.assertEqual(
            self.svcdef.desiredState, ServiceDefinition.STATE.RESTART)
        self.assertEqual(data.get("DesiredState"), -1)

    def testLaunch(self):
        self.assertEqual(
            self.svcdef.launch, ServiceDefinition.LAUNCH_MODE.AUTO)
        self.svcdef.launch = ServiceDefinition.LAUNCH_MODE.MANUAL
        self.assertEqual(
            self.svcdef.launch, ServiceDefinition.LAUNCH_MODE.MANUAL)
        data = self.svcdef.__getstate__()
        self.assertEqual(data.get("Launch"), "manual")

    def testParentId(self):
        self.assertEqual(
            self.svcdef.parentId, "02ef8505-eebd-6493-0c6c-630287847688"
        )

    def testCreatedAt(self):
        dttm = datetime.datetime(2013, 12, 12, 9, 7, 51)
        self.assertEqual(self.svcdef.createdAt, dttm)

    def testUpdatedAt(self):
        dttm = datetime.datetime(2013, 12, 12, 9, 30, 12)
        self.assertEqual(self.svcdef.updatedAt, dttm)


class ServiceInstanceTest(BaseTestCase):
    """
    """

    def setUp(self):
        svcinst = ServiceInstance()
        svcinst.__setstate__(instance_json_obj)
        self.svcinst = svcinst

    def testId(self):
        self.assertEqual(self.svcinst.id, instance_json_obj["ID"])

    def testServiceId(self):
        self.assertEqual(
            self.svcinst.serviceId, instance_json_obj["ServiceID"])

    def testHostId(self):
        self.assertEqual(self.svcinst.hostId, instance_json_obj["HostID"])

    def testResourceId(self):
        self.assertEqual(
            self.svcinst.resourceId,
            "/services/%s/running/%s" % (
                instance_json_obj["ServiceID"], instance_json_obj["ID"]
            )
        )

    def testStartedAt(self):
        self.assertEqual(
            self.svcinst.startedAt,
            datetime.datetime(2013, 12, 13, 10, 53, 5)
        )


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(ServiceObjectFactoryTest),
        unittest.makeSuite(ServiceJsonDecoderTest),
        unittest.makeSuite(ServiceDefinitionTest),
        unittest.makeSuite(ServiceInstanceTest),
    ))


if __name__ == "__main__":
    unittest.main(default="test_suite")
