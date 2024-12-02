##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate


import logging
log = logging.getLogger("zen.migrate")

class TwoTwoIndexing(Migrate.Step):
    version = Migrate.Version(2, 2, 4)

    def __init__(self):
        Migrate.Step.__init__(self)
        import maintwindowcatalog, devicepathindex, monitorTemplateMenu, \
                makeTemplateCatalog, networkindexes
        self.dependencies = [ maintwindowcatalog.maintwindowcatalog,
                              devicepathindex.devicepathindex,
                              networkindexes.networkindexes,
                              makeTemplateCatalog.makeTemplateCatalog,
                              monitorTemplateMenu.monitorTemplateMenu ]

    def cutover(self, dmd):  
        indexit = lambda x:x.index_object()
        for dev in dmd.Devices.getSubDevices_recursive():

        # For devicepathindex
            dev.index_object()

        # For maintwindowcatalog
            map(indexit, dev.maintenanceWindows())
            # Index rrdTemplates on the device and its components
            map(indexit, dev.objectValues('RRDTemplate'))
            for comp in dev.getDeviceComponents():
                map(indexit, comp.objectValues('RRDTemplate'))
            
        for name in 'Systems', 'Locations', 'Groups', 'Devices':
            organizer = getattr(dmd, name)
            indexRRDTemplates = name == 'Devices'
            for org in organizer.getSubOrganizers():
                map(indexit, org.maintenanceWindows())
                if indexRRDTemplates:
                    map(indexit, org.rrdTemplates())
            map(indexit, organizer.maintenanceWindows())
            if indexRRDTemplates:
                map(indexit, organizer.rrdTemplates())

        # for networkindexes
        dmd.Networks.reIndex()

        # Need to index the rrdTemplates on perf monitors too
        map(indexit, dmd.Monitors.getAllRRDTemplates())
        
        # Need to make sure user alerting rule schedule are indexed
        for us in dmd.ZenUsers.objectValues(spec=['UserSettings', 'GroupSettings']):
            for ar in us.objectValues(spec="ActionRule"):
                map(indexit, ar.windows())


twotwoindexing = TwoTwoIndexing()
