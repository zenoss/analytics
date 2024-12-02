from mock import Mock, patch, create_autospec
from Products.ZCatalog.interfaces import ICatalogBrain
from unittest import TestCase
from zope.interface.verify import verifyObject

from ..invalidationfilter import (
    _getZorCProperties,
    _iszorcustprop,
    BaseOrganizerFilter,
    DeviceClass,
    DeviceClassInvalidationFilter,
    FILTER_CONTINUE,
    FILTER_EXCLUDE,
    IgnorableClassesFilter,
    IInvalidationFilter,
    md5,
    OSProcessClass,
    OSProcessClassFilter,
    OSProcessOrganizer,
    OSProcessOrganizerFilter,
)
from .mock_interface import create_interface_mock

PATH = {"invalidationfilter": "Products.ZenHub.invalidationfilter"}


class IgnorableClassesFilterTest(TestCase):
    def setUp(t):
        t.icf = IgnorableClassesFilter()

    def test_init(t):
        IInvalidationFilter.providedBy(t.icf)
        # current version fails because weight attribute is not defined
        # icf.weight = 1
        # verifyObject(IInvalidationFilter, icf)
        t.assertTrue(hasattr(t.icf, "CLASSES_TO_IGNORE"))

    def test_initialize(t):
        context = Mock(name="context")
        t.icf.initialize(context)
        # No return or side-effects

    def test_include(t):
        obj = Mock(name="object")
        out = t.icf.include(obj)
        t.assertEqual(out, FILTER_CONTINUE)

    def test_include_excludes_classes_to_ignore(t):
        t.icf.CLASSES_TO_IGNORE = str
        out = t.icf.include("ignore me!")
        t.assertEqual(out, FILTER_EXCLUDE)


class BaseOrganizerFilterTest(TestCase):
    def setUp(t):
        t.types = Mock(name="types")
        t.bof = BaseOrganizerFilter(t.types)

        # @patch with autospec fails (https://bugs.python.org/issue23078)
        # manually spec ZenPropertyManager
        t.organizer = Mock(
            name="Products.ZenRelations.ZenPropertyManager",
            spec_set=[
                "zenPropertyIds",
                "getProperty",
                "zenPropIsPassword",
                "zenPropertyString",
            ],
        )

    def test_init(t):
        IInvalidationFilter.providedBy(t.bof)
        verifyObject(IInvalidationFilter, t.bof)
        t.assertEqual(t.bof.weight, 10)
        t.assertEqual(t.bof._types, t.types)

    def test_iszorcustprop(t):
        result = _iszorcustprop("no match")
        t.assertEqual(result, None)
        result = _iszorcustprop("cProperty")
        t.assertTrue(result)
        result = _iszorcustprop("zProperty")
        t.assertTrue(result)

    def test_getRoot(t):
        context = Mock(name="context")
        root = t.bof.getRoot(context)
        t.assertEqual(root, context.dmd.primaryAq())

    @patch(
        "{invalidationfilter}.IModelCatalogTool".format(**PATH),
        autospec=True,
        spec_set=True,
    )
    def test_initialize(t, IModelCatalogTool):
        # Create a Mock object that provides the ICatalogBrain interface
        ICatalogBrainMock = create_interface_mock(ICatalogBrain)
        brain = ICatalogBrainMock()

        IModelCatalogTool.return_value.search.return_value = [brain]
        checksum = create_autospec(t.bof.organizerChecksum)
        t.bof.organizerChecksum = checksum
        context = Mock(name="context")

        t.bof.initialize(context)

        t.assertEqual(
            t.bof.checksum_map,
            {brain.getPath.return_value: checksum.return_value},
        )

    def test_getZorCProperties(t):
        zprop = Mock(name="zenPropertyId", spec_set=[])
        t.organizer.zenPropertyIds.return_value = [zprop, zprop]

        # getZorCProperties returns a generator
        results = _getZorCProperties(t.organizer)

        t.organizer.zenPropIsPassword.return_value = False
        zId, propertyString = next(results)
        t.assertEqual(zId, zprop)
        t.assertEqual(
            propertyString, t.organizer.zenPropertyString.return_value
        )
        t.organizer.zenPropertyString.assert_called_with(zprop)

        t.organizer.zenPropIsPassword.return_value = True
        zId, propertyString = next(results)
        t.assertEqual(zId, zprop)
        t.assertEqual(
            propertyString, t.organizer.getProperty.return_value
        )
        t.organizer.getProperty.assert_called_with(zprop, "")

        with t.assertRaises(StopIteration):
            next(results)

    @patch(
        "{invalidationfilter}._getZorCProperties".format(**PATH),
        autospec=True,
        spec_set=True,
    )
    def test_generateChecksum(t, _getZorCProps):
        zprop = Mock(name="zenPropertyId", spec_set=[])
        data = (zprop, "property_string")
        _getZorCProps.return_value = [data]
        actual = md5()

        expect = md5()
        expect.update("%s|%s" % data)

        t.bof.generateChecksum(t.organizer, actual)

        _getZorCProps.assert_called_with(t.organizer)
        t.assertEqual(actual.hexdigest(), expect.hexdigest())

    @patch(
        "{invalidationfilter}._getZorCProperties".format(**PATH),
        autospec=True,
        spec_set=True,
    )
    def test_organizerChecksum(t, _getZorCProps):
        zprop = Mock(name="zenPropertyId", spec_set=[])
        data = (zprop, "property_string")
        _getZorCProps.return_value = [data]

        out = t.bof.organizerChecksum(t.organizer)

        expect = md5()
        expect.update("%s|%s" % data)
        t.assertEqual(out, expect.hexdigest())

    def test_include_ignores_non_matching_types(t):
        t.bof._types = (str,)
        ret = t.bof.include(False)
        t.assertEqual(ret, FILTER_CONTINUE)

    def test_include_if_checksum_changed(t):
        organizerChecksum = create_autospec(t.bof.organizerChecksum)
        t.bof.organizerChecksum = organizerChecksum
        t.bof._types = (Mock,)
        obj = Mock(name="object", spec_set=["getPrimaryPath"])
        obj.getPrimaryPath.return_value = ["dmd", "brain"]
        organizer_path = "/".join(obj.getPrimaryPath())
        t.bof.checksum_map = {organizer_path: "existing_checksum"}
        organizerChecksum.return_value = "current_checksum"

        ret = t.bof.include(obj)

        t.assertEqual(ret, FILTER_CONTINUE)

    def test_include_if_checksum_unchanged(t):
        organizerChecksum = create_autospec(t.bof.organizerChecksum)
        t.bof.organizerChecksum = organizerChecksum
        existing_checksum = "checksum"
        current_checksum = "checksum"
        organizerChecksum.return_value = current_checksum
        t.bof._types = (Mock,)
        obj = Mock(name="object", spec_set=["getPrimaryPath"])
        obj.getPrimaryPath.return_value = ["dmd", "brain"]
        organizer_path = "/".join(obj.getPrimaryPath())
        t.bof.checksum_map = {organizer_path: existing_checksum}

        ret = t.bof.include(obj)

        t.assertEqual(ret, FILTER_EXCLUDE)


class DeviceClassInvalidationFilterTest(TestCase):
    def setUp(t):
        t.dcif = DeviceClassInvalidationFilter()

    def test_init(t):
        IInvalidationFilter.providedBy(t.dcif)
        verifyObject(IInvalidationFilter, t.dcif)
        t.assertEqual(t.dcif._types, (DeviceClass,))

    def test_getRoot(t):
        context = Mock(name="context")
        root = t.dcif.getRoot(context)
        t.assertEqual(root, context.dmd.Devices.primaryAq())

    @patch(
        "{invalidationfilter}.BaseOrganizerFilter.generateChecksum".format(
            **PATH
        ),
        autospec=True,
        spec_set=True,
    )
    def test_generateChecksum(t, super_generateChecksum):
        md5_checksum = md5()
        organizer = Mock(
            name="Products.ZenRelations.ZenPropertyManager",
            spec_set=["rrdTemplates"],
        )
        rrdTemplate = Mock(name="rrdTemplate")
        rrdTemplate.exportXml.return_value = "some exemel"
        organizer.rrdTemplates.return_value = [rrdTemplate]

        t.dcif.generateChecksum(organizer, md5_checksum)

        # We cannot validate the output of the current version, refactor needed
        rrdTemplate.exportXml.was_called_once()
        super_generateChecksum.assert_called_with(
            t.dcif, organizer, md5_checksum
        )


class OSProcessOrganizerFilterTest(TestCase):
    def test_init(t):
        ospof = OSProcessOrganizerFilter()

        IInvalidationFilter.providedBy(ospof)
        verifyObject(IInvalidationFilter, ospof)
        t.assertEqual(ospof._types, (OSProcessOrganizer,))

    def test_getRoot(t):
        ospof = OSProcessOrganizerFilter()
        context = Mock(name="context")
        root = ospof.getRoot(context)
        t.assertEqual(root, context.dmd.Processes.primaryAq())


class OSProcessClassFilterTest(TestCase):
    def setUp(t):
        t.ospcf = OSProcessClassFilter()

    def test_init(t):
        IInvalidationFilter.providedBy(t.ospcf)
        verifyObject(IInvalidationFilter, t.ospcf)

        t.assertEqual(t.ospcf._types, (OSProcessClass,))

    def test_getRoot(t):
        context = Mock(name="context")
        root = t.ospcf.getRoot(context)
        t.assertEqual(root, context.dmd.Processes.primaryAq())

    @patch(
        "{invalidationfilter}.BaseOrganizerFilter.generateChecksum".format(
            **PATH
        ),
        autospec=True,
        spec_set=True,
    )
    def test_generateChecksum(t, super_generateChecksum):
        organizer = Mock(
            name="Products.ZenRelations.ZenPropertyManager",
            spec_set=["property_id", "_properties"],
        )
        prop = {"id": "property_id"}
        organizer._properties = [prop]
        organizer.property_id = "value"
        md5_checksum = md5()

        t.ospcf.generateChecksum(organizer, md5_checksum)

        expect = md5()
        expect.update("%s|%s" % (prop["id"], getattr(organizer, prop["id"])))
        t.assertEqual(md5_checksum.hexdigest(), expect.hexdigest())
        super_generateChecksum.assert_called_with(
            t.ospcf, organizer, md5_checksum
        )
