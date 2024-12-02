##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Re-index the event history table.

'''

__version__ = "$Revision$"[11:-2]

import os
import sys
import Migrate

from Products.ZenModel.RRDDataPoint import RRDDataPoint, SEPARATOR

from Products.ZenRelations.RelSchema import *
from Products.ZenModel.DeviceClass import DeviceClass
DeviceClass._relations = DeviceClass._relations + (
        ("nagiosTemplates", ToManyCont(ToOne,"Products.ZenModel.NagiosTemplate","deviceClass")),
        )

MOVED_PROPERTIES = 'createCmd rrdtype isrow rpn rrdmax color linetype limit format'.split()
COMMAND_PROPERTIES = 'enabled usessh component eventClass eventKey severity commandTemplate cycletime'.split()

def copyProperty(source, dest, name):
    try:
        s = getattr(source, name)
    except AttributeError:
        return
    try:
        d = getattr(dest, name)
    except AttributeError:
        pass

    if s != d:
        setattr(dest, name, s)
    try:
        delattr(s, name)
    except AttributeError:
        pass


class DataPoints(Migrate.Step):
    "Convert a data source into a data source with a data point"
    version = Migrate.Version(0, 23, 0)

    def __init__(self):
        Migrate.Step.__init__(self)
        self.renames = []

    def cutoverDataSource(self, s):
        s.buildRelations()
        if not s.datapoints():
            p = RRDDataPoint(s.id)
            for prop in MOVED_PROPERTIES:
                copyProperty(s, p, prop)
            s.datapoints._setObject(p.id, p)

    def cutoverTemplate(self, t, rrdPath):
        from Products.ZenUtils.Utils import zenPath
        oldbase = zenPath('perf')
        for s in t.datasources()[:]:
            self.cutoverDataSource(s)
            oldname = os.path.join(oldbase + rrdPath, s.id)
            newname = '%s%c%s' % (oldname, SEPARATOR, s.id)
            oldname += ".rrd"
            newname += ".rrd"
            if os.path.exists(oldname):
                self.renames.append( (oldname, newname) )
                os.rename(oldname, newname)
            oldname = s.id
            newname = '%s%c%s' % (s.id, SEPARATOR, s.id)
            for part in t.graphs() + t.thresholds():
                dsnames = part.dsnames[:]
                if oldname in dsnames:
                    dsnames.remove(oldname)
                    dsnames.append(newname)
                    part.dsnames = dsnames
                        
    def cutoverCommands(self, obj):
        try:
            sourceTemplate = obj.getNagiosTemplate()
        except AttributeError:
            return
        destTemplate = obj.getRRDTemplate(obj.getRRDTemplateName())
        for n in sourceTemplate.nagiosCmds():
            try:
                ds = destTemplate.datasources._getOb(n.id)
            except AttributeError:
                destTemplate.manage_addRRDDataSource(n.id, dsOption='COMMAND')
                ds = destTemplate.datasources._getOb(n.id)
                ds.sourcetype = 'COMMAND'
            if ds.sourcetype in ('NAGIOS', 'COMMAND'):
                for attr in COMMAND_PROPERTIES:
                    setattr(ds, attr, getattr(n, attr))
                ds.sourcetype = 'COMMAND'

    def cutover(self, dmd):
        for org in dmd.Devices.getSubOrganizers():
            for t in org.getRRDTemplates():
                for s in t.datasources():
                    self.cutoverDataSource(s)
        for i, d in enumerate(dmd.Devices.getSubDevicesGen()):
            if i % 10 == 0:
                sys.stdout.write('#')
                sys.stdout.flush()
            self.cutoverTemplate(d.getRRDTemplate(), d.rrdPath())
            self.cutoverCommands(d)
            for o in d.getDeviceComponents():
                self.cutoverTemplate(o.getRRDTemplate(), o.rrdPath())
                self.cutoverCommands(o)
        sys.stdout.write('\n')
        for t in dmd.Devices.rrdTemplates():
            self.cutoverTemplate(t, 'bogusName')

    def revert(self):
        for oldname, newname in self.renames:
            os.renames(newname, oldname)

DataPoints()
