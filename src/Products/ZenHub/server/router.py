##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import collections

from .utils import UNSPECIFIED as _UNSPECIFIED, getLogger


class ServiceCallRouter(collections.Mapping):
    """Maps ServiceCall objects to executor objects.

    Service call routing has method priority, meaning that a route having
    a specified method name has higher precedence that a route not having
    that method name specified.

    For example, given the two routes:

        *:s1 -> e1
        m1:* -> e2

    A service call for m1:s1 will route to e1 instead of e2.
    """

    @classmethod
    def from_config(cls, config):
        """Return a ServiceCallRouter initialized from config.

        The config parameter should be mapping of service calls to the
        name of the executor handling the service call.

        A "*:*" route is required to specified in the config.  This
        route is used as the default route when no other route is a
        better match.

        :param config: Mapping of "service:method" -> "executor"
        :type config: Mapping[str, str]
        """
        route_tree = collections.defaultdict(dict)
        for call, executor in config.items():
            service, method = call.split(":")
            route_tree[method][service] = executor
        name = route_tree.get("*", {}).get("*")
        if not name:
            raise ValueError("Missing required '*:*' route")
        return cls(route_tree)

    def __init__(self, routes):
        """Initialize a ServiceCallRouter instance.

        The routes parameter is a nested mapping of:
            method-name -> service-name -> executor-name

        :param routes: Mapping of service calls to executors.
        :type routes: Mapping[str, Mapping[str, str]]
        """
        self.__routes = routes
        self.__log = getLogger(self)

    def get(self, call, default=_UNSPECIFIED):
        """Return the executor name the call routes to.

        If the call's route matches the default route, return the value
        of the default parameter if it was specified.

        :param call: The service call to find a route for
        :type call: .service.ServiceCall
        """
        service, method = self.__resolve(call.service, call.method)
        if (service, method) == ("*", "*") and default is not _UNSPECIFIED:
            return default
        return self.__routes[method][service]

    def __getitem__(self, call):
        """Return the executor name the call routes to.

        :param call: The service call to find a route for
        :type call: .service.ServiceCall
        """
        service, method = self.__resolve(call.service, call.method)
        return self.__routes[method][service]

    def __resolve(self, service, method):
        method = method if method in self.__routes else "*"
        service_routes = self.__routes.get(method)

        # If the service is not named for the method and no default
        # service is specified, then backtrack to the default method.
        if service not in service_routes:
            if "*" not in service_routes:
                method = "*"
                service_routes = self.__routes.get(method)

        service = service if service in service_routes else "*"
        return (service, method)

    def __iter__(self):
        # for method, services in self.__routes.items():
        #     for service, executor in services.items():
        #         yield ((service, method), executor)
        return (
            ((service, method), executor)
            for method, services in self.__routes.items()
            for service, executor in services.items()
        )

    def __len__(self):
        return sum(len(subroutes) for subroutes in self.__routes.values())
