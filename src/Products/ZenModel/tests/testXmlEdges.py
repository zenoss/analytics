##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from ZenModelBaseTest import ZenModelBaseTest
from Products.ZenUtils.Utils import edgesToXML

class TestXmlEdges(ZenModelBaseTest):
    
    def testXMLEdges(self):
        """
        Test that checks correct convertion of edges to an XML file
        """
        start = ('10.111.23.0', '/some_path/10.111.23.0')
        node = ('10.111.23.0', 'network.png', '0xffffff', '10.111.23.0')
        child1 = ('ip-10-111-23-1.zenoss.loc', 'server.png', '0x00ff00', '10.111.23.1')
        child2 = ('ip-10-111-23-2.zenoss.loc', 'server.png', '0x00ff00', '10.111.23.2')
        
        output_template = ('<graph>'
        '<Start name="10.111.23.0" url="/some_path/10.111.23.0"/>'
        '<Node id="10.111.23.0" prop="10.111.23.0" icon="network.png" color="0xffffff"/>'
        '<Node id="10.111.23.1" prop="ip-10-111-23-1.zenoss.loc" icon="server.png" color="0x00ff00"/>'
        '<Node id="10.111.23.2" prop="ip-10-111-23-2.zenoss.loc" icon="server.png" color="0x00ff00"/>'
        '<Edge fromID="10.111.23.0" toID="10.111.23.1"/>'
        '<Edge fromID="10.111.23.0" toID="10.111.23.2"/>'
        '</graph>')

        edges = (
            (node, child1),
            (node, child2)
            )

        self.assertEqual(edgesToXML(edges, start), output_template)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestXmlEdges))
    return suite

if __name__=="__main__":
    framework()
