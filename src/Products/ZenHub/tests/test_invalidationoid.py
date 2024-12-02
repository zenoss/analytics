from mock import Mock
from unittest import TestCase
from zope.component import adaptedBy
from zope.interface.verify import verifyObject

from ..invalidationoid import (
    DefaultOidTransform,
    IInvalidationOid,
    PrimaryPathObjectManager,
)


class DefaultOidTransformTest(TestCase):
    def setUp(self):
        self.obj = Mock(spec_set=PrimaryPathObjectManager)
        self.default_oid_transform = DefaultOidTransform(self.obj)

    def test_implements_IInvalidationOid(self):
        # Provides the interface
        IInvalidationOid.providedBy(self.default_oid_transform)
        # Implements the interface it according to spec
        verifyObject(IInvalidationOid, self.default_oid_transform)

    def test_adapts_PrimaryPathObjectManager(self):
        self.assertEqual(
            list(adaptedBy(DefaultOidTransform)), [PrimaryPathObjectManager]
        )

    def test_init(self):
        self.assertEqual(self.default_oid_transform._obj, self.obj)

    def test_transformOid(self):
        ret = self.default_oid_transform.transformOid("unmodified oid")
        self.assertEqual(ret, "unmodified oid")
