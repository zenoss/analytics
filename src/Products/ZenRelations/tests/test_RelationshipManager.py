##############################################################################
#
# Copyright (C) Zenoss, Inc. 2021, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from unittest import TestCase
from mock import Mock, create_autospec, call

from ..RelationshipManager import RelationshipManager


PATH = {"src": "Products.ZenRelations.RelationshipManager"}


class TestRelationshipManager(TestCase):
    def test_exportXml(t):
        rm = RelationshipManager("test_id")
        ofile = Mock(name="output_file")
        # getProductionState may not be set on all instances
        rm.exportProdState = create_autospec(rm.exportProdState)
        rm.exportXmlProperties = create_autospec(rm.exportXmlProperties)
        rm.exportXmlRelationships = create_autospec(rm.exportXmlRelationships)

        rm.exportXml(ofile)

        ofile.write.assert_has_calls(
            [
                call(
                    "<object id='test_id'"
                    " module='Products.ZenRelations.RelationshipManager'"
                    " class='RelationshipManager' move='False'>\n"
                ),
                call("</object>\n"),
            ]
        )
        rm.exportXmlProperties.assert_called_with(ofile, False)
        rm.exportXmlRelationships.assert_called_with(ofile, [])
        rm.exportProdState.assert_called_with(ofile)
        # TODO: test for zendocAdapter.exportZendoc, and self.exportXmlHook
        # aquisition is messy, and may need some refactoring to be testable

    def test_exportProdState(t):
        rm = RelationshipManager("test_id")
        ofile = Mock(name="output_file")
        # getProductionState may not be set on all instances
        rm.getProductionState = Mock(return_value="mystate")

        rm.exportProdState(ofile)

        ofile.write.assert_called_with(
            "<property id='prodstate' mode='w' type='string'>"
            "mystate"
            "</property>"
        )
