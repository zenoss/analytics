##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re

from Acquisition import aq_chain
from DateTime import DateTime
from zope.interface import implementer

from Products.ZenRelations.ZenPropertyManager import ZenPropertyManager
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IPropertiesFacade

iscustprop = re.compile("c[A-Z]").match


def _getOwnerAndProperty(obj, propId):
    # Returns the property dict object and the object that 'owns' the
    # property.  The return value is a tuple, e.g. (obj, dict).
    return next((
        (
            ob,
            next((
                pmap
                for pmap in ob.propertyMap()
                if pmap['id'] == propId
            ), None)
        )
        for ob in aq_chain(obj)
        if isinstance(ob, ZenPropertyManager) and ob.hasProperty(propId)
    ), (None, None))


def _makePropertyData(obj, propId):
    # Returns a dict containing the following keys:
    # id, type, select_variable, label, description, uid, islocal, value,
    # and valueAsString.
    # The value and valueAsString keys are missing for password properties.
    propObj, propData = _getOwnerAndProperty(obj, propId)
    propData = propData.copy()
    if not propObj:
        return None
    # 'visible' and 'mode' are not used in Zenoss.
    for key in ('visible', 'mode'):
        if key in propData:
            propData.pop(key)
    propData['uid'] = '/'.join(propObj.getPrimaryPath())
    propData['islocal'] = (propObj is obj)
    if not propObj.zenPropIsPassword(propId):
        propData['value'] = propObj.getProperty(propId)
        propData['valueAsString'] = propObj.zenPropertyString(propId)
    return propData


def _checkConstraints(self, prop, constraints):
    # 'prop' is the property dict (produced by _makePropertyData).
    # 'constraints' is a dict of predicates that must be true for the
    # given property attribute.  If any predicate fails, this function
    # returns False.
    # Note: a 'predicate' is a function that returns a boolean value based
    # on its arguments.
    for fieldId, predicates in constraints.iteritems():
        if fieldId not in prop:
            continue
        if not isinstance(predicates, (list, tuple)):
            predicates = [predicates]
        if not all(predicate(prop) for predicate in predicates):
            return False
    return True


@implementer(IPropertiesFacade)
class PropertiesFacade(ZuulFacade):

    def getZenProperties(self, uid, exclusionList=()):
        """
        Returns information about and the value of every zen property.

        @type  uid: string
        @param uid: unique identifier of an object
        @type  exclusionList: Collection
        @param exclusionList: List of zproperty ids that we do not
            wish to retrieve
        """
        obj = self._getObject(uid)
        return obj.exportZProperties(exclusionList)

    def deleteZenProperty(self, uid, zProperty):
        """
        Removes the local instance of the each property in properties. Note
        that the property will only be deleted if a hasProperty is true
        @type  uid: String
        @param uid: unique identifier of an object
        @type  properties: Array
        @param properties: list of zenproperty identifiers that
            we wish to delete
        """
        obj = self._getObject(uid)
        if obj.hasProperty(zProperty):
            prop = self.getZenProperty(uid, zProperty)
            if not iscustprop(zProperty):
                if prop['path'] == '/':
                    raise Exception(
                        "Unable to delete root definition of a property '%s'"
                        % (zProperty,)
                    )
            obj.deleteZenProperty(zProperty)

    def _checkType(self, obj, prop, type, value):
        """
        @param obj: the object returned in the caller from getObject(uid)
        @param prop: the id, zProperty, or cProperty
        @param type: the type of property value
        @param value: the value itself
        """
        # make sure it is the correct type
        ztype = obj.getPropertyType(prop)
        if ztype == 'int':
            try:
                value = int(value)
            except ValueError:
                raise Exception('Invalid value entered for {}'.format(prop))
        if ztype == 'float':
            value = float(value)
        if ztype == 'string':
            value = str(value)
        if ztype == 'date':
            value = value.replace('%20', ' ')  # Ugh. Manually decode spaces
            value = DateTime(value)
        if ztype == "lines" and isinstance(value, basestring):
            value = value.split("\n") if value else []
        return value

    def addCustomProperty(
            self, id, value, label, uid, type, description=None):
        """
        Adds a custom property from the UI
        """
        obj = self._getObject(uid)
        value = self._checkType(obj, id, type, value)
        id = id.strip()
        if not iscustprop(id):
            raise Exception(
                "Invalid Custom Property. Must start with lower case c"
            )
        elif obj.hasProperty(id):
            raise Exception("Custom Property already exists.")
        else:
            obj._setProperty(id, value, type, label, description=description)

    def setZenProperty(self, uid, zProperty, value):
        """
        Sets the value of the zProperty for this user.
        The value will be forced into the type, throwing
        an exception if it fails
        @type  uid: String
        @param uid: unique identifier of an object
        @type  zProperty: String
        @param zProperty: identifier of the property
        @type  value: Anything
        @param value: What you want the new value of the property to be
        """
        obj = self._getObject(uid)
        # Make sure it is the correct type
        value = self._checkType(obj, zProperty, type, value)
        # Do not save * as passwords
        if obj.zenPropIsPassword(zProperty) \
                and value == obj.zenPropertyString(zProperty):
            return
        return obj.setZenProperty(zProperty, value)

    def getCustomProperties(self, uid, exclusionList=()):
        """
        Returns information about and the value of every zen property.

        @type  uid: string
        @param uid: unique identifier of an object
        @type  exclusionList: Collection
        @param exclusionList: List of cproperty ids that we do not
            wish to retrieve
        """
        obj = self._getObject(uid)
        return self.exportCustomProperties(obj, exclusionList)

    def exportCustomProperties(self, obj, exclusionList=()):
        """
        TODO: This really belongs in ZenRelations/ZenRelationManager.py

        @param exclusionList: list of cproperties we do not want to export
        @type exclusionList: collection

        For this manager will return the following about each cProperty
        Will return the following about each Zen Property
        - id - identifier
        - islocal - if this object has a local definition
        - value - value for this object
        - valueAsString - string representation of the property
        - type - int string lines etc
        - path - where it is defined
        - options - acceptable values of this zProperty
        """
        props = []
        for entry in obj.custPropertyMap():
            cId = entry["id"]
            if cId in exclusionList:
                continue
            prop = {
                "id":      cId,
                "islocal": obj.hasProperty(cId),
                "type":    obj.getPropertyType(cId),
                "path":    obj.zenPropertyPath(cId),
                "options": obj.zenPropertyOptions(cId),
                "label":   entry.get("label"),
            }
            if not obj.zenPropIsPassword(cId):
                prop['value'] = obj.getZ(cId)
                prop['valueAsString'] = obj.zenPropertyString(cId)
            props.append(prop)
        return props

    def getZenProperty(self, uid, zProperty):
        """
        Returns information about a zproperty for a
        given context, including its value
        @rtype:   Dictionary
        @return:  B{Properties}:
             - path: (string) where the property is defined
             - type: (string) type of zproperty it is
             - options: (Array) available options for the zproperty
             - value (Array) value of the zproperty
             - valueAsString (string)
        """
        obj = self._getObject(uid)
        prop = {
            "path":    obj.zenPropertyPath(zProperty),
            "options": obj.zenPropertyOptions(zProperty),
            "type":    obj.getPropertyType(zProperty),
        }
        if not obj.zenPropIsPassword(zProperty):
            prop['value'] = obj.getZ(zProperty)
            prop['valueAsString'] = obj.zenPropertyString(zProperty)
        return prop

    def updateCustomProperty(
            self, uid, id,
            select_variable=None, label=None, description=None):
        """Change the attributes of a custom property.
        """
        obj = self._getObject(uid)
        propId = id.strip()

        if not iscustprop(propId):
            raise ValueError(
                "Invalid Custom Property. Name must start with lower case c"
            )

        owner, pmap = _getOwnerAndProperty(obj, propId)
        if owner is None:
            raise ValueError("Custom property does not exist.")

        if select_variable:
            if not obj.hasProperty(select_variable, useAcquisition=True):
                raise ValueError(
                    "Selection source variable does not exist: %s"
                    % select_variable
                )
            if description is None:
                description = pmap.get("description")
            if owner != obj:
                self.addCustomProperty(
                    id, select_variable, label, uid, 'selection',
                    description=description
                )
            else:
                obj.propdict()[propId]['select_variable'] = select_variable
            newowner, newmap = _getOwnerAndProperty(obj, propId)

    def query(self, uid, constraints=None):
        """Returns a list of properties.

        E.g. to select all custom properties:
            cprops = facade.query(
                '/zport/dmd/Devices',
                constraints=[lambda x: x['id'].startswith('c')]
            )

        This method returns a list of dicts that resemble the following
        example:

            {
                'uid': str,
                'id': str,
                'label': str,
                'description': str,
                'type': str,
                'select_variable': str or None,
                'value': object,
                'valueAsString': str
                'islocal': boolean
            }

        Notes:
          * For password properties, the 'value' and 'valueAsString'
            fields are always None.
          * 'ctxId' is the combination of 'uid' and 'id' and serves as the
            unique identifer for the dict.

        @param constraints {list} A list of predicate functions.  The
            property must be valid for all predicates for inclusion
            in the result.
        """
        if constraints is None:
            constraints = []
        if not isinstance(constraints, (list, tuple)):
            constraints = [constraints]

        obj = self._getObject(uid)
        result = []
        for pdict in obj.getZenRootNode().propertyMap():
            propData = _makePropertyData(obj, pdict['id'])
            if not propData:
                continue
            if all(constraint(propData) for constraint in constraints):
                result.append(propData)
        return result
