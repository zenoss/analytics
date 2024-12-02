##############################################################################
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

class ServiceTree (object):
    """
    This class allows for the caching and traversal of trees comprised of
    ServiceDefinition objects.
    """

    def __init__(self, services=[]):
        """
        :param services: all services in the tree
        :type services: list of ServiceDefinition objects
        """
        self.setServices(services)


    def setServices(self, services):
        """
        Set the state of the service tree

        :param services: all services in the tree
        :type services list of ServiceDefinition objects
        """
        self._services = services
        self._idToService = dict((i.id, i) for i in services)
        self._serviceChildren = dict((i, []) for i in services)
        for i in (i for i in services if i.parentId):
            self._serviceChildren[self._idToService[i.parentId]].append(i)


    def getChildren(self, service):
        """
        Returns a list of all child services of a given service

        @param service: the service for which to return children
        @type service: service object or string containing service id
        @rtype: list of service objects
        """
        if isinstance(service, basestring):
            service = self._idToService[service]
        return self._serviceChildren[service]


    def getService(self, serviceId):
        """
        Return the service object corresponding to a given service id

        @param serviceId: the service id
        @type serviceId: string
        @rtype: ServiceDefinition object
        """
        return self._idToService[serviceId]


    def getPath(self, service):
        """
        Return the path to the given service
        @param service: the service
        @type service: service object or string containing service id
        @return: list of ancestor services leading to the service
        @rtype: [ServiceDefinition object]
        """
        if isinstance(service, basestring):
            try:
                service = self._idToService[service]
            except KeyError:
                raise LookupError("Specified current service ('%s') not found" % currentServiceId)

        retval = [service]
        while service.parentId:
            service = self.getService(service.parentId)
            retval.insert(0,service)
        return retval


    def matchServicePath(self, currentServiceId, path):
        """
        Return a list of services which match the given service path

        A "service path" is a string which applies file-system semantics to the
        service hierarchy.  I.e., it is a string of components separated by slashes.
        Like a FS path it may be absolute (i.e, beginning with '/') or relative;
        absolute means that it starts with the root of the tree containing the
        given current service.  Legitimate components include '.' and '..' with
        the same semantics as in FS paths.  Component which start with '=' match
        services whose name equals the remainder of the component; other components
        are matched against the tags of the candidate services; this implies that
        a path can match multiple services at any given level.  e.g.,

           '/hub/collector' will match all services tagged 'collector' inside
           all services tagged 'hub' which are children of the root service; i.e.,
           all collectors in all hubs

           '/=localhost/=localhost' will match the localhost service inside the
           root localhost service; i.e., the localhost collector inside the
           localhost hub

           '/hub/=collector1' will match all services named collector1 which are
            children of root services tagged 'hub'; i.e., collector1 no matter
            which root hub it is on

        @param currentServiceId: id of service from which to do relative path matching
        @param currentServiceId: string
        @param path: path to match
        @param path: string
        @rtype: list of ServiceDefinition objects
        """
        try:
            service = self._idToService[currentServiceId]
        except KeyError:
            raise LookupError("Specified current service ('%s') not found" % currentServiceId)
        if path.startswith('/'):
            # absolute path; find the root of the current service tree
            path = path[1:]
            while service.parentId:
                 service = self.getService(service.parentId)
        current = [service]

        for component in path.split('/'):
            if component in ('.', ''):
                pass
            elif component == '..':
                current = [self._idToService[i.parentId] if i.parentId else i
                            for i in current]
            else:
                if component[0] != '=':
                    tag, name = component, object()
                else:
                    tag, name = object(), component[1:]
                next = []
                for service in current:
                    children = self._serviceChildren[service]
                    next.extend (i for i in children if tag in (i.tags or []) or i.name==name)
                current = next
        return current


    def findMatchingServices(self, service, pattern):
        """
        Find all services beneath a given service matching a given pattern

        The pattern to be matched is the same as the component matching in
        matchServicePath(): if the first character is '=' it matches the name of
        the service; otherwise it matches a tag.

        :param services: service(s) whose descendants will be searched
        :type services: ServiceDefinition object
        :param pattern: pattern to be matched.  See description above for format
        :type pattern: string
        :rtype list of ServiceDefinition objects
        """
        if pattern[0] != '=':
            tag, name = pattern, object()
        else:
            tag, name = object(), pattern[1:]

        def walktree(service):
            for child in self._serviceChildren[service]:
                for i in walktree(child):
                    yield i
            if service.name == name or tag in (service.tags or []):
                yield service

        return [i for i in walktree(service)]

