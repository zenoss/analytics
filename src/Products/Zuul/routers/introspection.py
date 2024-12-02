##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import inspect

from Products import Zuul
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.ZenUtils.extdirect.zope.metaconfigure import allDirectRouters


class IntrospectionRouter(DirectRouter):
    """
    Provide a JSON API to explore the available routers and their methods.

    from Products.Zuul.routers.introspection import IntrospectionRouter
    zz = IntrospectionRouter(dmd)
    """

    def _getAllRouters(self):
        return allDirectRouters

    def getAllRouters(self):
        """
        Return a description of the Zenoss routers available.

        from Products.Zuul.routers.introspection import IntrospectionRouter
        zz = IntrospectionRouter(dmd)
        pprint(zz.getAllRouters().data)
        """
        routers = self._getAllRouters()
        data = map(self._getRouterInfo, routers)
        return DirectResponse(data=Zuul.marshal(data))
        
    def _getRouterInfo(self, router=None):
        klass = self.__class__ if router is None else router
        filename = inspect.getfile(klass)
        data = allDirectRouters.get(klass, {}).copy()
        data.update( dict(action=klass.__name__, filename=filename,
                    documentation=inspect.getdoc(router),
                    urlpath='/zport/dmd/'+data['name'],
        ))
        return data

    def getRouterInfo(self, router=None):
        """
        Return information about the router
        """
        data = self._getRouterInfo(router)
        return DirectResponse(data=Zuul.marshal(data))

    def _getRouterByName(self, router):
        routers = [x for x in self._getAllRouters() if router in x.__name__]
        return routers

    def getRouterMethods(self, router=None):
        """
        Return a JSON list of methods, arguments and documentation

        Example usage from zendmd:

        from Products.Zuul.routers.introspection import IntrospectionRouter
        zz = IntrospectionRouter(dmd)
        pprint(zz.getRouterMethods('DeviceRouter').data)
        """
        if router is not None:
            klasses = self._getRouterByName(router)
            if klasses:
                # TODO: log something?
                klass = klasses[0]
            else:
                return DirectResponse.fail(msg="No router named '%s' found" % router)
        else:
            klass = self.__class__

        methods = {}
        for name, code in inspect.getmembers(klass):
            if name.startswith('_'):
                continue
            if not inspect.ismethod(code):
                continue

            argspec = inspect.getargspec(code)
            if argspec.defaults is None:
                args = argspec.args[1:] # Ignore 'self'
                kwargs = {}
            else:
                n = len(argspec.defaults)
                args = argspec.args[1:-n] # Ignore 'self'
                kwargs = dict(zip(argspec.args[-n:], argspec.defaults))

            methods[name] = dict(
                documentation=inspect.getdoc(code),
                kwargs=kwargs,
                args=args,
            )

        return DirectResponse(data=Zuul.marshal(methods))

