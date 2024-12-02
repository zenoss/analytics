##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import logging
log = logging.getLogger("zen.Manufacturers")
from zope.component import adapts
from zope.interface import implements
from Products.Zuul.tree import TreeNode
from Products.Zuul.infos import InfoBase, ProxyProperty
from Products.Zuul.decorators import info
from Products.Zuul.interfaces import IManufacturersInfo, IManufacturers, IInfo 
from Products.ZenModel.ManufacturerRoot import ManufacturerRoot
from Products.ZenModel.Manufacturer import Manufacturer



class ManufacturersInfo(InfoBase):
    implements(IManufacturersInfo)
    adapts(Manufacturer)


