##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from zope.interface import implements
from zope.component import adapts
from Products.ZenRelations.ToOneRelationship import ToOneRelationship
from interfaces import IPathReporter, IGloballyIndexed

def relPath(obj, relname):
    paths = set()
    rel = getattr(obj, relname, None)
    if rel:
        obid = obj.getId()
        remoteName = rel.remoteName()
        if isinstance(rel, ToOneRelationship):
            obs = (rel.obj,)
        else:
            obs = rel.objectValuesGen()
        for ob in obs:
            if ob is None:
                continue
            path = ob.getPrimaryPath()
            paths.add(path + (remoteName, obid))
    return list(paths)


def devicePathsFromComponent(comp):
    c_paths = IPathReporter(comp).getPaths()
    return [path + ('device',) for path in c_paths]


class DefaultPathReporter(object):
    implements(IPathReporter)
    adapts(IGloballyIndexed)

    def __init__(self, context):
        self.context = context

    def getPaths(self):
        paths = [self.context.getPhysicalPath()]
        # since all component path reporters extend DefaultPathReporter
        # we need to add our component Group hook in here as opposed to a subclass
        from Products.ZenModel.ManagedEntity import ManagedEntity
        if isinstance(self.context, ManagedEntity):
            componentGroups = self.context.getComponentGroups()
            if componentGroups:
                paths.extend(relPath(self.context, "componentGroups"))
        return paths

class DevicePathReporter(DefaultPathReporter):
    def getPaths(self):
        paths = super(DevicePathReporter, self).getPaths()
        dev = self.context
        paths.extend(relPath(dev, 'location'))
        paths.extend(relPath(dev, 'systems'))
        paths.extend(relPath(dev, 'groups'))
        #for iface in self.context.os.interfaces.objectValuesGen(): # @TODO need to find an alternative
        #    paths.extend(devicePathsFromComponent(iface))
        return paths


class ServicePathReporter(DefaultPathReporter):
    def getPaths(self):
        paths = super(ServicePathReporter, self).getPaths()
        paths.extend(relPath(self.context, 'serviceclass'))
        return paths


class InterfacePathReporter(DefaultPathReporter):
    def getPaths(self):
        paths = super(InterfacePathReporter, self).getPaths()
        for ip in self.context.ipaddresses.objectValuesGen():
            paths.extend(relPath(ip, 'network'))
        return paths


class IpAddressPathReporter(DefaultPathReporter):
    def getPaths(self):
        paths = super(IpAddressPathReporter, self).getPaths()
        if self.context.interface(): 
            paths.append(self.context.interface().getPrimaryPath() + ('ipaddresses',))
        return paths


class ProcessPathReporter(DefaultPathReporter):
    def getPaths(self):
        paths = super(ProcessPathReporter, self).getPaths()
        paths.extend(relPath(self.context, 'osProcessClass'))
        return paths


class ProductPathReporter(DefaultPathReporter):
    def getPaths(self):
        paths = super(ProductPathReporter, self).getPaths()
        pc = self.context.productClass()
        if pc:
            paths.append(pc.getPhysicalPath())
        return paths
