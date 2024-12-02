##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__="""Location

$Id: Location.py,v 1.12 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.12 $"[11:-2]

from AccessControl.class_init import InitializeClass
from App.special_dtml import DTMLFile
import transaction
from AccessControl import ClassSecurityInfo

from AccessControl import Permissions as permissions
from ZenossSecurity import ZEN_COMMON, ZEN_MANAGE_DMD
from Products.ZenRelations.RelSchema import *

from DeviceOrganizer import DeviceOrganizer
from ZenPackable import ZenPackable
from zExceptions import NotFound
from Products.ZenUtils.jsonutils import json
from Products.ZenUtils.Utils import extractPostContent

def manage_addLocation(context, id, description = "",
                       address="", REQUEST = None):
    """make a Location"""
    loc = Location(id, description)
    context._setObject(id, loc)
    loc.description = description
    loc.address = address
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() +'/manage_main')


addLocation = DTMLFile('dtml/addLocation',globals())


class Location(DeviceOrganizer, ZenPackable):
    """
    Location is a DeviceGroup Organizer that manages physical device Locations.
    """

    # Organizer configuration
    dmdRootName = "Locations"

    address = ''
    latlong = None
    portal_type = meta_type = event_key = 'Location'

    _properties = DeviceOrganizer._properties + (
        {'id':'address','type':'string','mode':'w'},
        {'id':'latlong', 'type':'string','mode':'w'}
    )

    _relations = DeviceOrganizer._relations + ZenPackable._relations + (
        ("devices", ToMany(ToOne,"Products.ZenModel.Device","location")),
        ("networks", ToMany(ToOne,"Products.ZenModel.IpNetwork","location")),
    )

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'immediate_view' : 'deviceOrganizerStatus',
            'actions'        :
            (
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'deviceOrganizerStatus'
                , 'permissions'   : (permissions.view,)
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (permissions.view,)
                },
#                { 'id'            : 'historyEvents'
#                , 'name'          : 'History'
#                , 'action'        : 'viewHistoryEvents'
#                , 'permissions'   : (permissions.view,)
#                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'deviceOrganizerManage'
                , 'permissions'   : ('Manage DMD',)
                },
                { 'id'            : 'geomap'
                , 'name'          : 'Map'
                , 'action'        : 'locationGeoMap'
                , 'permissions'   : (permissions.view,)
                },
            )
         },
        )

    security = ClassSecurityInfo()

    def __init__(self, id, description = '', address=''):
        super(Location, self).__init__(id, description)
        self.address = address


    security.declareProtected(ZEN_MANAGE_DMD, 'setAddress')
    def setAddress(self, address):
        """Sets the mailing address for this location"""
        self.address = address

    def getChildLinks(self):
        """ Returns child link data ready for GMaps """
        results = self.dmd.ZenLinkManager.getChildLinks(self)
        # make sure we don't get any conflict errors (this is a read only call)
        transaction.abort()
        return results

    def numMappableChildren(self):
        children = self.children()
        return len(
            filter(lambda x:getattr(x, 'address', None), children)
        )

    def getGeomapData(self):
        """
        Gather data for Google Maps. This is not a JSON method; it must be put
        into a data structure appropriate for JS consumption by another method
        (specifically, getChildGeomapData, below).
        """
        worstSeverity = self.getWorstEventSeverity()
        colors = 'red orange yellow green green'.split()
        colors.reverse()
        color = 'green'
        if worstSeverity:
            try:
                color = colors[worstSeverity - 1]
            except IndexError:
                # show green rather than error
                pass
        link = self.absolute_url_path()
        linkToMap = self.numMappableChildren()
        if linkToMap:
            link+='/locationGeoMap'
        summarytext = self.mapTooltip() # mapTooltip is a page template
        uid = "/".join(self.getPhysicalPath())
        return [self.address, color, link, summarytext, uid]

    @json
    def getChildGeomapData(self):
        """
        Return info ready for Google Maps.
        """
        allnodes = []
        data = []
        children = self.children()
        allnodes.extend(children)
        data = [x.getGeomapData() for x in allnodes if x.address]
        if not data: data = [self.getGeomapData()]
        return data

    def getSecondaryNodes(self):
        """ Returns geomap info on cousin nodes that should be
            included in the view due to outside linking.
        """
        data = []
        # Short-circuit the method for now
        return data

    security.declareProtected(ZEN_COMMON, 'getGeoCache')
    @json
    def getGeoCache(self):
        cache = dict()
        for loc in self.children():
            uid = "/".join(loc.getPhysicalPath())
            cache[uid] = dict(latlong=loc.latlong,
                                      address=loc.address)
        return cache

    security.declareProtected(ZEN_COMMON, 'setGeocodeCache')
    def setGeocodeCache(self, REQUEST=None):
        """
        This method takes the geocodecache from the client and
        updates the methods on the locations with the latest latlong
        """
        cache = extractPostContent(REQUEST)
        try: cache = cache.decode('utf-8')
        except Exception: pass
        from json import loads
        geocode = loads(cache)
        for uid, geo in geocode.iteritems():
            try:
                loc = self.unrestrictedTraverse(str(uid))
                if loc.latlong != geo['latlong']:
                    loc.latlong = geo['latlong']
            except (KeyError, NotFound):
                # the location might have been removed or renamed
                # and the client still had the cache.
                continue

InitializeClass(Location)
