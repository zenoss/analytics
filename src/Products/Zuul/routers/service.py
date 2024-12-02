##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""
Operations for Services.

Available at:  /zport/dmd/service_router
"""

from Products import Zuul
from Products.Zuul.routers import TreeRouter
from Products.Zuul.decorators import require
from Products.ZenUtils.Ext import DirectResponse
from Products.ZenUtils.jsonutils import unjson
from Products.ZenMessaging.audit import audit


class ServiceRouter(TreeRouter):
    """
    A JSON/ExtDirect interface to operations on services
    """

    def __init__(self, context, request):
        self.api = Zuul.getFacade('service')
        self.context = context
        self.request = request
        super(ServiceRouter, self).__init__(context, request)

    def _getFacade(self):
        return self.api

    def _canDeleteUid(self,uid):
        # check the number of levels deep it is
        levels = len(uid.split('/'))
        return levels > 5

    def getClassNames(self, uid=None, query=None):
        data = self.api.getClassNames(uid, query)
        return DirectResponse.succeed(data=data)

    @require('Manage DMD')
    def addClass(self, contextUid, id, posQuery=None):
        """
        Add a new service class.

        @type  contextUid: string
        @param contextUid: Unique ID of the service ogranizer to add new class to
        @type  id: string
        @param id: ID of the new service
        @type  posQuery: dictionary
        @param posQuery: Object defining a query where the returned position will lie
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - newIndex: (integer) Index of the newly added class in the query
             defined by posQuery
        """
        newUid = self.api.addClass(contextUid, id)
        audit('UI.Service.Add', contextUid + '/' + id)
        return DirectResponse()

    def query(self, limit=None, start=None, sort=None, dir=None, params=None,
              page=None, history=False, uid=None, criteria=()):
        """
        Retrieve a list of services based on a set of parameters.

        @type  limit: integer
        @param limit: (optional) Number of items to return; used in pagination
                      (default: None)
        @type  start: integer
        @param start: (optional) Offset to return the results from; used in
                      pagination (default: None)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return results (default:
                     None)
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: None)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
        @type  history: boolean
        @param history: not used
        @type  uid: string
        @param uid: Service class UID to query
        @type  criteria: list
        @param criteria: not used
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - services: ([dictionary]) List of objects representing services
             - totalCount: (integer) Total number of services
             - hash: (string) Hashcheck of the current services state
             - disabled: (boolean) True if current user cannot manage services
        """
        if uid is None:
            uid = "/".join(self.context.getPhysicalPath())

        if isinstance(params, basestring):
            params = unjson(params)
        services = self.api.getList(limit, start, sort, dir, params, uid,
                                  criteria)

        disabled = not Zuul.checkPermission('Manage DMD')

        data = Zuul.marshal(services['serviceInfos'], keys=('name','description', 'count', 'uid','port'))
        return DirectResponse(services=data, totalCount=services['total'],
                              hash=services['hash'], disabled=disabled)


    def getTree(self, id):
        """
        Returns the tree structure of an organizer hierarchy.

        @type  id: string
        @param id: Id of the root node of the tree to be returned
        @rtype:   [dictionary]
        @return:  Object representing the tree
        """
        tree = self.api.getTree(id)
        data = Zuul.marshal(tree)
        return [data]

    def getOrganizerTree(self, id):
        """
        Returns the tree structure of an organizer hierarchy, only including
        organizers.

        @type  id: string
        @param id: Id of the root node of the tree to be returned
        @rtype:   [dictionary]
        @return:  Object representing the organizer tree
        """
        tree = self.api.getOrganizerTree(id)
        data = Zuul.marshal(tree)
        return [data]

    def getInfo(self, uid, keys=None):
        """
        Get the properties of a service.

        @type  uid: string
        @param uid: Unique identifier of a service
        @type  keys: list
        @param keys: (optional) List of keys to include in the returned
                     dictionary. If None then all keys will be returned
                     (default: None)
        @rtype:   DirectResponse
        @return:  B{Properties}
            - data: (dictionary) Object representing a service's properties
            - disabled: (boolean) True if current user cannot manage services
        """
        service = self.api.getInfo(uid)
        data = Zuul.marshal(service, keys)
        if 'serviceKeys' in data and isinstance(data['serviceKeys'], (tuple, list)):
            data['serviceKeys'] = ', '.join(data['serviceKeys'])
        disabled = not Zuul.checkPermission('Manage DMD')
        return DirectResponse.succeed(data=data, disabled=disabled)

    @require('Manage DMD')
    def setInfo(self, **data):
        """
        Set attributes on a service.
        This method accepts any keyword argument for the property that you wish
        to set. The only required property is "uid".

        @type    uid: string
        @keyword uid: Unique identifier of a service
        @rtype:   DirectResponse
        @return:  Success message
        """
        serviceUid = data['uid']
        service = self.api.getInfo(serviceUid)
        if 'serviceKeys' in data and isinstance(data['serviceKeys'], str):
            data['serviceKeys'] = tuple(l.strip() for l in data['serviceKeys'].split(','))
        Zuul.unmarshal(data, service)   # removes data['uid']
        audit('UI.Service.Edit', serviceUid, data_=data)
        return DirectResponse.succeed()

    def getInstances(self, uid, start=0, params=None, limit=50, sort='name',
                     page=None, dir='ASC'):
        """
        Get a list of instances for a service UID.

        @type  uid: string
        @param uid: Service UID to get instances of
        @type  start: integer
        @param start: (optional) Offset to return the results from; used in
                      pagination (default: 0)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
        @type  limit: integer
        @param limit: (optional) Number of items to return; used in pagination
                      (default: 50)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return results (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: ([dictionary]) List of objects representing service instances
             - totalCount: (integer) Total number of instances
        """
        if isinstance(params, basestring):
            params = unjson(params)
        instances = self.api.getInstances(uid, start=start, params=params,
                                          limit=limit, sort=sort, dir=dir)

        keys = ['description', 'device', 'locking', 'monitored', 'name',
                 'pingStatus', 'uid']
        data = Zuul.marshal(instances, keys)
        return DirectResponse.succeed(data=data, totalCount=instances.total)

    @require('Manage DMD')
    def moveServices(self, sourceUids, targetUid):
        """
        Move service(s) from one organizer to another.

        @type  sourceUids: [string]
        @param sourceUids: UID(s) of the service(s) to move
        @type  targetUid: string
        @param targetUid: UID of the organizer to move to
        @rtype:   DirectResponse
        @return:  Success messsage
        """
        self.api.moveServices(sourceUids, targetUid)
        for uid in sourceUids:
            audit('UI.Service.Move', uid, target=targetUid)
        return DirectResponse.succeed()

    def getUnmonitoredStartModes(self, uid):
        """
        Get a list of unmonitored start modes for a Windows service.

        @type  uid: string
        @param uid: Unique ID of a Windows service.
        @rtype:   DirectResponse
        @return:  B{Properties}:
            - data: ([string]) List of unmonitored start modes for a Windows service
        """
        data = self.api.getUnmonitoredStartModes(uid)
        return DirectResponse.succeed(data=Zuul.marshal(data))

    def getMonitoredStartModes(self, uid, query=''):
        """
        Get a list of monitored start modes for a Windows service.

        @type  uid: string
        @param uid: Unique ID of a Windows service.
        @rtype:   DirectResponse
        @return:  B{Properties}:
            - data: ([string]) List of monitored start modes for a Windows service
        """
        data = self.api.getMonitoredStartModes(uid)
        return DirectResponse.succeed(data=Zuul.marshal(data))
