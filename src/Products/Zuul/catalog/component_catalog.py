##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import re

from zope.interface import Interface
from zope.component import queryUtility
from OFS.interfaces import IObjectWillBeAddedEvent
from Products.ZCatalog.ZCatalog import manage_addZCatalog

from Products.ZenUtils.Search import (
    makeCaseInsensitiveFieldIndex, 
    makeMultiPathIndex
) 

from ..interfaces import IInfo
from .interfaces import IComponentFieldSpec


class ComponentWrapper(object):
    """
    A wrapper for indexing components in the component type catalogs that does
    some type massaging.
    """
    def __init__(self, obj):
        self._obj = obj
        self._info = IInfo(obj)

    @property
    def path(self):
        return self._obj.getAllPaths()

    def __getattr__(self, attr):
        sort = False
        if attr.endswith('__sort'):
            sort = True
            attr = attr[:-6]
        val = getattr(self._info, attr)
        if isinstance(val, dict):
            return val.get('name')
        return pad_numeric_values_for_indexing(val) if sort else str(val)


class ComponentFieldSpec(object):
    """
    The base class for component field specs. The `fields` and `meta_type`
    attributes will be injected when the class is created (see
    metaconfigure.py:componentFieldSpecDirective())
    """
    def __init__(self):
        self.catalog_name = '%s_componentCatalog' % self.meta_type

    def create_catalog(self, device):
        manage_addZCatalog(device, self.catalog_name, self.catalog_name)
        catalog = device._getOb(self.catalog_name)
        catalog.addIndex('path', makeMultiPathIndex('path'))
        for field in self.fields:
            field = str(field)
            # Add two indexes, one for natural sorting
            sort_field = field + '__sort'
            catalog.addIndex(field, makeCaseInsensitiveFieldIndex(field))
            catalog.addIndex(sort_field, makeCaseInsensitiveFieldIndex(sort_field))
        return catalog

    def index_all_of_type(self, obj, meta_type):
        catalog = self.get_catalog(obj, meta_type)
        for component in obj.device().componentSearch(meta_type=meta_type):
            catalog.catalog_object(ComponentWrapper(component.getObject()), component.getPath())

    def get_catalog(self, obj, meta_type):
        """
        @param obj:       A device component for which a type-specific catalog should get got
        @type obj:        DeviceComponent
        @param meta_type: The meta_type the catalog is being created for
        @type meta_type:  str
        @return:          The component type catalog
        @rtype:           ZCatalog
        """
        device = obj.device()
        try:
            catalog = device._getOb(self.catalog_name)
        except AttributeError:
            catalog = self.create_catalog(device)
            self.index_all_of_type(obj, meta_type)
        if 'path' not in catalog._catalog.indexes:
            catalog.addIndex('path', makeMultiPathIndex('path'))
            self.index_all_of_type(obj, meta_type)
        return catalog


def get_component_field_spec(meta_type):
    return queryUtility(IComponentFieldSpec, meta_type)


def onComponentIndexingEvent(ob, event):
    spec = get_component_field_spec(ob.meta_type)
    if spec is None:
        return
    catalog = spec.get_catalog(ob, ob.meta_type)
    catalog.catalog_object(ComponentWrapper(ob), '/'.join(ob.getPhysicalPath()))


def onComponentRemoved(ob, event):
    if not IObjectWillBeAddedEvent.providedBy(event):
        spec = get_component_field_spec(ob.meta_type)
        if spec is None:
            return
        catalog = spec.get_catalog(ob, ob.meta_type)
        uid = '/'.join(ob.getPrimaryPath())
        if catalog.getrid(uid) is None:
            # Avoid "tried to uncatalog nonexistent object" warnings
            return
        catalog.uncatalog_object(uid)


def pad_numeric_values_for_indexing(val):
    """
    Pad numeric values with 0's so that sort is both alphabetically and
    numerically correct.
    eth1/1  will sort on eth0000000001/0000000001
    eth1/12 will sort on eth0000000001/0000000012
    """
    return re.sub("[\d]+", lambda x:str.zfill(x.group(0),10), str(val))
