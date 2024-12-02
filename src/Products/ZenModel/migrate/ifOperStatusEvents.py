##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.Zuul.facades import ObjectNotFoundException

__doc__ = """
Adds a ValueChangeThreshold to the ifOperStatus datapoint. Also adds a transform
to set the ifOperStatus if the threshold is violated
"""

import Migrate
import logging
from Products.Zuul import getFacade
log = logging.getLogger('zen.migrate')


OPERSTATUS_TRANSFORM = """
# SET OPERSTATUS ON IPINTERFACE COMPONENT
if component is not None and evt.eventKey == 'ifOperStatus_ifOperStatus|ifOperStatusChange':
    evt._action='drop'
    operStatus = int(float(getattr(evt,'current', '0')))
    if component.operStatus != operStatus:
        @transact
        def updateDb():
            component.operStatus=operStatus
        updateDb()
"""

class ifOperStatusEvents(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def __init__(self):
        Migrate.Step.__init__(self)
        import ifOperStatusEthernetCsmacd64
        self.dependencies = [ ifOperStatusEthernetCsmacd64.ifOperStatusEthernetCsmacd64 ]

    def cutover(self, dmd):
        template64Id = '/zport/dmd/Devices/rrdTemplates/ethernetCsmacd_64'
        template32Id = '/zport/dmd/Devices/rrdTemplates/ethernetCsmacd'
        dpIdSuffix = '/datasources/ifOperStatus/datapoints/ifOperStatus'
        tf = getFacade('template', dmd)
        for templateId in (template32Id, template64Id):
            try:
                etherInfo = tf.getInfo(templateId)
                dpInfo = tf.getInfo(templateId+dpIdSuffix)
                if etherInfo and dpInfo:
                    tf.addThreshold(etherInfo.uid, 'ValueChangeThreshold', 'ifOperStatusChange', [dpInfo.uid])
            except ObjectNotFoundException as e:
                log.info("Object not found" + e.message)
            except Exception as e:
                log.info(e.message)
        #now add transform that sets the operstatus on the interface component
        eventClass = dmd.Events.Status.Perf
        if eventClass.transform is None or "# SET OPERSTATUS ON IPINTERFACE COMPONENT" not in eventClass.transform:
            previous = eventClass.transform
            eventClass.transform = "%s\n%s" %(previous or '', OPERSTATUS_TRANSFORM)

ifOperStatusEvents()
