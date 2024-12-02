##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""ConfonPropManager

add keyedselect to property manager

$Id: ConfmonPropManager.py,v 1.4 2002/12/08 18:27:53 edahl Exp $"""

__version__ = "$Revision: 1.4 $"[11:-2]

from OFS.PropertyManager import PropertyManager
from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass

class ConfmonPropManager(PropertyManager):

    manage_propertiesForm=DTMLFile('dtml/properties', globals(),
                                   property_extensible_schema__=1)
    
    def _setPropValue(self, id, value):
        """override from PerpertyManager to handle checks and ip creation"""
        self._wrapperCheck(value)
        if self.getPropertyType(id) == 'keyedselection':
            value = int(value)
        setattr(self,id,value)


    def manage_editProperties(self, REQUEST):
        """Edit object properties via the web.
        The purpose of this method is to change all property values,
        even those not listed in REQUEST; otherwise checkboxes that
        get turned off will be ignored.  Use manage_changeProperties()
        instead for most situations.
        """
        for prop in self._propertyMap():
            name=prop['id']
            if 'w' in prop.get('mode', 'wd'):
                value=REQUEST.get(name, '')
                self._updateProperty(name, value)
        self.index_object()
        if REQUEST:
            message="Saved changes."
            return self.manage_propertiesForm(self,REQUEST,
                                              manage_tabs_message=message)


InitializeClass(ConfmonPropManager)
