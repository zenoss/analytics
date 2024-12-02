from unittest import TestCase
from mock import Mock

from Products.ZenRelations.PrimaryPathObjectManager import (
    PrimaryPathObjectManager,
)
from ..oids import (
    IdentityOidTransform,
    ComponentOidTransform,
    IInvalidationOid,
)

from zope.interface.verify import verifyObject


class IdentityOidTransformTest(TestCase):
    def setUp(self):
        self.obj = Mock(spec_set=PrimaryPathObjectManager)
        self.default_oid_transform = IdentityOidTransform(self.obj)

    def test_implements_IInvalidationOid(self):
        # Provides the interface
        IInvalidationOid.providedBy(self.default_oid_transform)
        # Implements the interface it according to spec
        verifyObject(IInvalidationOid, self.default_oid_transform)

    def test_init(self):
        self.assertEqual(self.default_oid_transform._entity, self.obj)

    def test_transformOid(self):
        ret = self.default_oid_transform.transformOid("unmodified oid")
        self.assertEqual(ret, "unmodified oid")


class ComponentOidTransformTest(TestCase):
    def setUp(self):
        self.obj = Mock(spec_set=PrimaryPathObjectManager)
        self.device_oid_transform = ComponentOidTransform(self.obj)

    def test_implements_IInvalidationOid(self):
        # Provides the interface
        IInvalidationOid.providedBy(self.device_oid_transform)
        # Implements the interface it according to spec
        verifyObject(IInvalidationOid, self.device_oid_transform)

    def test_init(self):
        self.assertEqual(self.device_oid_transform._entity, self.obj)

    def test_transformOid(self):
        """returns unmodified oid, if _entity has no device attribute"""
        self.assertFalse(hasattr(self.obj, "device"))
        ret = self.device_oid_transform.transformOid("unmodified oid")
        self.assertEqual(ret, "unmodified oid")

    def test_transformOid_returns_device_oid(self):
        """returns obj.device()._p_oid if obj.device exists"""
        obj = Mock(name="PrimaryPathObjectManager", spec_set=["device"])
        device = Mock(name="device", spec_set=["_p_oid"])
        obj.device.return_value = device

        device_oid_transform = ComponentOidTransform(obj)
        ret = device_oid_transform.transformOid("ignored oid")

        self.assertEqual(ret, obj.device.return_value._p_oid)
