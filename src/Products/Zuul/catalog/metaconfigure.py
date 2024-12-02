##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.component.zcml import utility

from .interfaces import IComponentFieldSpec
from .component_catalog import ComponentFieldSpec

def componentFieldSpecDirective(_context, class_, fields=()):
    meta_type = class_.meta_type
    klass = type('ComponentFieldSpec',
                 (ComponentFieldSpec,),
                 {
                     'fields':fields,
                     'meta_type':meta_type,
                 }
            )
    utility(_context, name=meta_type, factory=klass, provides=IComponentFieldSpec)
