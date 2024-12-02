##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009-2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""
Operations for Processes.

Available at:  /zport/dmd/process_router
"""
import re
from sre_parse import parse_template

from Products import Zuul
from Products.Zuul.decorators import require
from Products.Zuul.routers import TreeRouter
from Products.ZenUtils.Ext import DirectResponse
from Products.ZenUtils.jsonutils import unjson
from Products.ZenMessaging.audit import audit

class ProcessRouter(TreeRouter):
    """
    A JSON/ExtDirect interface to operations on processes
    """

    def _getFacade(self):
        return Zuul.getFacade('process', self.context)

    def getTree(self, id):
        """
        Returns the tree structure of an organizer hierarchy where
        the root node is the organizer identified by the id parameter.

        @type  id: string
        @param id: Id of the root node of the tree to be returned
        @rtype:   [dictionary]
        @return:  Object representing the tree
        """
        facade = self._getFacade()
        tree = facade.getTree(id)
        data = Zuul.marshal(tree)
        return [data]

    def moveProcess(self, uid, targetUid):
        """
        Move a process or organizer from one organizer to another.

        @type  uid: string
        @param uid: UID of the process or organizer to move
        @type  targetUid: string
        @param targetUid: UID of the organizer to move to
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - uid: (dictionary) The new uid for moved process or organizer
        """
        facade = self._getFacade()
        old_uid = uid
        primaryPath = facade.moveProcess(uid, targetUid)
        id = '.'.join(primaryPath)
        uid = '/'.join(primaryPath)
        # TODO: Common method for all the "move" user actions.
        #       Be consistent via:  process=old_uid, target=org_uid
        audit('UI.Process.Move', uid, old=old_uid)
        return DirectResponse.succeed(uid=uid, id=id)

    def getInfo(self, uid, keys=None):
        """
        Get the properties of a process.

        @type  uid: string
        @param uid: Unique identifier of a process
        @type  keys: list
        @param keys: (optional) List of keys to include in the returned
                     dictionary. If None then all keys will be returned
                     (default: None)
        @rtype:   DirectResponse
        @return:  B{Properties}
            - data: (dictionary) Object representing a process's properties
        """
        facade = self._getFacade()
        process = facade.getInfo(uid)
        data = Zuul.marshal(process, keys)
        return DirectResponse.succeed(data=data)

    @require('Manage DMD')
    def setInfo(self, **data):
        """
        Set attributes on a process.
        This method accepts any keyword argument for the property that you wish
        to set. The only required property is "uid".

        @type    uid: string
        @keyword uid: Unique identifier of a process
        @rtype:   DirectResponse
        @return:  B{Properties}
            - data: (dictionary) Object representing a process's new properties
        """
        facade = self._getFacade()
        processUid = data['uid']
        for regexParam in ['includeRegex', 'excludeRegex', 'replaceRegex']:
            regex = data.get(regexParam)
            if regex:
                try:
                    re.compile(regex)
                except re.error as e:
                    m = "%s : %s" % (regexParam, e)
                    return DirectResponse.fail(msg=m)
        replaceRegex = data.get('replaceRegex')
        if replaceRegex:
            replaceRegex = re.compile(replaceRegex)
            replacement = data.get('replacement')
            if replacement:
                try:
                    groups, literals = parse_template(replacement,replaceRegex)
                    for index, group in groups:
                        if group > replaceRegex.groups:
                            m = "Group (%s) referenced in replacement must be defined in replaceRegex" % group
                            return DirectResponse.fail(msg=m)
                except re.error as e:
                    m = "replacement : %s" % (e,)
                    return DirectResponse.fail(msg=m)

        process = facade.getInfo(processUid)
        audit('UI.Process.Edit', processUid, data_=data, skipFields_=('uid'))
        return DirectResponse.succeed(data=Zuul.unmarshal(data, process))

    def getInstances(self, uid, start=0, params=None, limit=50, sort='name',
                     page=None, dir='ASC'):
        """
        Get a list of instances for a process UID.

        @type  uid: string
        @param uid: Process UID to get instances of
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
             - data: ([dictionary]) List of objects representing process instances
             - total: (integer) Total number of instances
        """
        facade = self._getFacade()
        instances = facade.getInstances(uid, start, limit, sort, dir, params)
        keys = ['device', 'monitored', 'pingStatus', 'processName', 'name', 
                'uid', 'minProcessCount', 'maxProcessCount']
        data = Zuul.marshal(instances, keys)
        return DirectResponse.succeed(data=data, totalCount=instances.total)

    def getSequence(self, *args, **kwargs):
        """
        Get the current processes sequence.

        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: ([dictionary]) List of objects representing processes in
             sequence order
        """
        facade = self._getFacade()
        sequence = facade.getSequence()
        data = Zuul.marshal(sequence)
        return DirectResponse.succeed(data=data)

    def setSequence(self, uids):
        """
        Set the current processes sequence.

        @type  uids: [string]
        @param uids: The set of process uid's in the desired sequence
        @rtype:   DirectResponse
        @return:  Success message
        """
        facade = self._getFacade()
        facade.setSequence(uids)
        audit('UI.Process.SetSequence', sequence=uids)
        return DirectResponse.succeed()

    def getSequence2(self, *args, **kwargs):
        """
        Get the current processes sequence.

        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: ([dictionary]) List of objects representing processes in
             sequence order
        """
        facade = self._getFacade()
        sequence = facade.getSequence2()
        data = Zuul.marshal(sequence)
        return DirectResponse.succeed(data=data)

    def applyOSProcessClassMatchers(self, *args, **kwargs):
        """
        Get the current processes sequence.

        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: ([dictionary]) List of objects representing processes in
             sequence order
        """
        facade = self._getFacade()
        sequence = facade.applyOSProcessClassMatchers(kwargs['uids'], kwargs['lines'])
        data = Zuul.marshal(sequence)
        return DirectResponse.succeed(data=data, total=len(data))
        
    def getProcessList(self, *args, **kwargs):
        """
        @type  deviceGuid: string
        @param deviceGuid: Service class UUID of the device to get process list
        """
        facade = self._getFacade()
        processList = facade.getProcessList(kwargs['deviceGuid'])
        data = Zuul.marshal(processList)
        return DirectResponse.succeed(data=data)


    def query(self, limit=None, start=None, sort=None, dir=None, params=None,
              page=None, history=False, uid=None, criteria=()):
        """
        Retrieve a list of processes based on a set of parameters.

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
             - processes: ([dictionary]) List of objects representing processes
             - totalCount: (integer) Total number of processes
             - hash: (string) Hashcheck of the current processes state
             - disabled: (boolean) True if current user cannot manage processes
        """
        facade = self._getFacade()
        if uid is None:
            uid = self.context

        if isinstance(params, basestring):
            params = unjson(params)

        processes = facade.getList(limit, start, sort, dir, params, uid,
                                  criteria)
        disabled = not Zuul.checkPermission('Manage DMD')

        data = Zuul.marshal(processes)
        return DirectResponse(processes=data, totalCount=processes.total,
                              hash=processes.hash_, disabled=disabled)

    
