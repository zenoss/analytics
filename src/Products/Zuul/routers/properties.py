##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from DateTime import DateTime

from Products import Zuul
from Products.ZenMessaging.audit import audit
from Products.ZenModel.ZenossSecurity import ZEN_ZPROPERTIES_EDIT
from Products.ZenUtils.Ext import DirectResponse
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.jsonutils import unjson
from Products.Zuul.decorators import contextRequire, serviceConnectionError

_exclusions = ('zCollectorPlugins', 'zCredentialsZProperties')


def _filterData(params, data):
    """
    @param params: params passed to the caller and used here for filtering
    @param data: data to be filtered and returned
    """
    if params:
        if isinstance(params, basestring):
            filters = unjson(params)
        else:
            filters = params

        def hasFilter(row, key, value):
            if row.get(key) is not None:
                return value.lower() in str(row.get(key)).lower()

        for key, value in filters.iteritems():
            # assume AND for sorting
            data = [row for row in data if hasFilter(row, key, value)]

    return data


def _sortData(sort, data, dir):
    """
    @param data: data to be sorted and returned
    """
    reverse = (dir != "ASC")
    return sorted(data, key=lambda row: row.get(sort, None), reverse=reverse)


class PropertiesRouter(DirectRouter):

    def _getFacade(self):
        return Zuul.getFacade('properties', self.context)

    @serviceConnectionError
    def getZenProperties(
            self, uid, start=0, params="{}", limit=None, sort=None,
            page=None, dir='ASC'):
        """
        Returns the definition and values of all
        the zen properties for this context
        @type  uid: string
        @param uid: unique identifier of an object
        """
        facade = self._getFacade()
        data = facade.getZenProperties(uid, exclusionList=_exclusions)
        data = _filterData(params, data)
        if sort:
            data = _sortData(sort, data, dir)
        return DirectResponse(data=Zuul.marshal(data), totalCount=len(data))

    @serviceConnectionError
    def getZenProperty(self, uid, zProperty):
        """
        Returns information about a zproperty for a given context,
        including its value.

        @rtype:   Dictionary
        @return:  B{Properties}:
             - path: (string) where the property is defined
             - type: (string) type of zproperty it is
             - options: (Array) available options for the zproperty
             - value (Array) value of the zproperty
             - valueAsString (string)
        """
        facade = self._getFacade()
        data = facade.getZenProperty(uid, zProperty)
        return DirectResponse.succeed(data=Zuul.marshal(data))

    @serviceConnectionError
    def getCustomProperties(
            self, uid, start=0, params="{}", limit=None, sort=None,
            page=None, dir='ASC'):
        """
        Returns the definition and values of all
        the zen properties for this context
        @type  uid: string
        @param uid: unique identifier of an object
        """
        facade = self._getFacade()
        data = facade.getCustomProperties(uid)
        data = _filterData(params, data)
        if sort:
            data = _sortData(sort, data, dir)
        return DirectResponse(data=Zuul.marshal(data), totalCount=len(data))

    def addCustomProperty(self, id, value, label, uid, type):
        """
        Adds a new property to the / of the tree
        """
        facade = self._getFacade()
        facade.addCustomProperty(id, value, label, uid, type)
        return DirectResponse.succeed(
            msg="Property %s added successfully." % (id,)
        )

    @serviceConnectionError
    @contextRequire(ZEN_ZPROPERTIES_EDIT, 'uid')
    def setZenProperty(self, uid, zProperty, value=None):
        """
        Sets the zProperty value.

        @type  uid: string
        @param uid: unique identifier of an object
        @type  zProperty: string or dictionary
        @param zProperty: either a string that represents which zproperty
            we are changing or key value pair dictionary that is the list
            of zproperties we wish to change.
        @type  value: anything
        @param value: if we are modifying a single zproperty then it is the
            value, it is not used if a dictionary is passed in for zProperty
        """
        facade = self._getFacade()
        properties = {}
        # Allow for zProperty to be a map of zproperties that need to
        # be saved in case there is more than one
        if not isinstance(zProperty, dict):
            properties[zProperty] = value
        else:
            properties = zProperty
        for key, value in properties.iteritems():
            # Get old value for auditing
            oldProperty = facade.getZenProperty(uid, key)
            oldValue = oldProperty['value'] if 'value' in oldProperty else ''

            facade.setZenProperty(uid, key, value)
            data = facade.getZenProperty(uid, key)

            # stringify falsey values
            value = str(value) if not value else value
            oldValue = str(oldValue) if not oldValue else oldValue

            obj = facade._getObject(uid)
            maskFields = 'value' if obj.zenPropIsPassword(key) else None
            audit('UI.zProperty.Edit', key, maskFields_=maskFields,
                  data_={obj.meta_type: uid, 'value': value},
                  oldData_={'value': oldValue})

        return DirectResponse(data=Zuul.marshal(data))

    @serviceConnectionError
    @contextRequire(ZEN_ZPROPERTIES_EDIT, 'uid')
    def deleteZenProperty(self, uid, zProperty):
        """
        Removes the local instance of the each property in properties. Note
        that the property will only be deleted if a hasProperty is true
        * also used on custom properties or cProperties
        @type  uid: String
        @param uid: unique identifier of an object
        @type  properties: String
        @param properties: zenproperty identifier
        """
        facade = self._getFacade()
        data = facade.deleteZenProperty(uid, zProperty)
        obj = facade._getObject(uid)
        audit('UI.zProperty.Delete', zProperty, data_={obj.meta_type: uid})
        return DirectResponse(data=Zuul.marshal(data))

    @serviceConnectionError
    def query(self, uid, constraints=None, params=None, **kw):
        """Returns a list of properties matching the given constraints
        and parameters.

        There are two constraints that can be specified: idPrefix and type

        idPrefix: Should be 'c' to return only cProperties or 'z' to
            return only zProperties.  If not specified, then both cProperties
            and zProperties are returned.

        type: Is a string naming the property type that returned properties
            should have.  If multiple types are desired, this value can be
            a list of strings.

        @param uid {str} From properties from this object path
        @param params {dict} Return properties matching the given fields.
        @param fields {list} List of fields to return for each property.
        @param kw {dict} The 'limit', 'sort', 'page', and 'dir' parameters
            are extracted from here.
        """
        requirements = [lambda x: x["id"] not in _exclusions]

        idPrefix = constraints.pop("idPrefix", None)
        if idPrefix:
            idPrefix = idPrefix.lower()
            if idPrefix not in ('c', 'z'):
                idPrefix = None
            else:
                requirements.append(lambda x: x["id"].startswith(idPrefix))
        if idPrefix is None:
            requirements.append(lambda x: x["id"].startswith(('c', 'z')))

        propTypes = constraints.pop("type", None)
        if propTypes:
            if not isinstance(propTypes, list):
                propTypes = [propTypes]
            requirements.append(lambda x: x["type"] in propTypes)

        facade = self._getFacade()
        data = facade.query(uid, constraints=requirements)

        if params is not None:
            data = _filterData(params, data)

        totalCount = len(data)

        sort = kw.pop("sort", None)
        if sort:
            direction = kw.pop("dir", "ASC")
            data = _sortData(sort, data, direction)

        limit = kw.pop("limit", None)
        if limit:
            start = kw.pop("start", 0)
            data = data[start:(start + limit)]

        # transform some data since there isn't any IInfo support
        # for properties (properties don't have a type other than dict).
        for prop in data:
            if isinstance(prop.get("value"), DateTime):
                prop["value"] = prop.get("value").timeTime()

        return DirectResponse(totalCount=totalCount, data=Zuul.marshal(data))

    @serviceConnectionError
    @contextRequire(ZEN_ZPROPERTIES_EDIT, 'uid')
    def add(self, uid, id, value, label, description,
            type, select_variable=None):
        """Adds a new property to uid.
        """
        facade = self._getFacade()
        if type == "selection" and select_variable:
            facade.addCustomProperty(
                id, select_variable, label, uid, type,
                description=description
            )
            facade.setZenProperty(uid, id, value)
        else:
            facade.addCustomProperty(
                id, value, label, uid, type,
                description=description
            )
        return DirectResponse.succeed(
            msg="Property %s successfully added." % (id,)
        )

    @serviceConnectionError
    @contextRequire(ZEN_ZPROPERTIES_EDIT, 'uid')
    def update(self, uid, id, value, select_variable=None):
        """Updates an existing property.
        """
        facade = self._getFacade()
        if select_variable:
            facade.updateCustomProperty(
                uid, id, select_variable=select_variable
            )

        # Transform date value from milliseconds into DateTime object.
        prop = facade.getZenProperty(uid, id)
        if prop.get("type") == "date":
            userfacade = Zuul.getFacade('properties', self.context)
            usersettings = userfacade._dmd.ZenUsers.getUserSettings()
            tz = usersettings.timezone
            dt = DateTime(value, tz) if tz else DateTime(value)
            value = dt.ISO8601()

        facade.setZenProperty(uid, id, value)
        return DirectResponse.succeed(
            msg="Property %s successfully updated." % (id,)
        )

    @serviceConnectionError
    @contextRequire(ZEN_ZPROPERTIES_EDIT, 'uid')
    def remove(self, uid, id=None, properties=None):
        """Removes the local instance of the each property in properties.
        Note that the property will only be deleted if a hasProperty is true

        @param uid {str} Path to the object owning the properties.
        @param id {str} The ID of the property to delete.
        @param properties {list[str]} List of property IDs to delete.

        Note that specifying both 'id' and 'properties' is valid.
        Duplicate property IDs skipped.
        """
        facade = self._getFacade()
        names = set()
        if id is not None:
            names.add(id)
        if properties is not None:
            if not isinstance(properties, (list, tuple)):
                properties = [properties]
            names.update(properties)
        for name in names:
            facade.deleteZenProperty(uid, name)
            obj = facade._getObject(uid)
            audit('UI.zProperty.Delete', name, data_={obj.meta_type: uid})
        if len(names) == 1:
            return DirectResponse.succeed(
                msg="Property %s successfully deleted." % names.pop()
            )
        return DirectResponse.succeed(
            msg="Successfully deleted %s properties." % len(names)
        )
