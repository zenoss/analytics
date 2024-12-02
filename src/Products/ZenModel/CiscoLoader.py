##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""CiscoLoader.py

CiscoLoader.py populates the sysObjectIdClassifier with Cisco product data
by parsing their Products mib.

$Id: CiscoLoader.py,v 1.2 2004/02/18 16:19:18 edahl Exp $"""

__version__ = "$Revision: 1.2 $"[11:-2]

import re


from Products.ZenUtils.BasicLoader import BasicLoader
from Products.ZenModel.Manufacturer import manage_addManufacturer
from Products.ZenModel.HardwareClass import HardwareClass

class CiscoLoader(BasicLoader):
    '''Load a machine'''

    def __init__(self):
        '''Handle command line options, get app instance,
        load caches and setup log file'''
        BasicLoader.__init__(self)
        manuf = self.dmd.Manufacturers
        if not hasattr(manuf, 'Cisco'):
            manage_addManufacturer(manuf, 'Cisco')
        self.cisco = manuf._getOb('Cisco')


    lineparser1 = re.compile(
        r'^(?P<model>\w+)\s+OBJ.*Products (?P<id>\d+) \}.*-- (?P<descr>.*)')
    lineparser2 = re.compile(
        r'^(?P<model>\w+)\s+OBJ.*Products (?P<id>\d+) \}.*')

    modelclean = re.compile(r'cisco|catalyst')

    def loaderBody(self,line):
        """loader body override to customize what will load"""
        m = self.lineparser1.match(line)
        if not m: m = self.lineparser2.match(line)
        if not m: return
        fullid = '.1.3.6.1.4.1.9.1.' + m.group('id')
        model = self.modelclean.sub('', m.group('model'))
        description = ""
        try:
            description = m.group('descr')
        except Exception:pass
        self.log.debug("Loading fullid=%s,prodpath=%s,descr=%s", fullid, model, description)
        prod = HardwareClass(model,productKey=fullid,description=description)
        self.cisco.products._setObject(model, prod)

   

    def buildOptions(self):
        self.usage = "%prog [options] file"
        BasicLoader.buildOptions(self)
   

    def parseOptions(self):
        (self.options, args) = self.parser.parse_args()
        if len(args) < 1:
            self.parser.error("incorrect number of arguments")    
        self.filename = args[0]


if __name__ == "__main__":
    loader = CiscoLoader()
    loader.loadDatabase()
    print "Database Load is finished!"
