##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
ControlPlaneClient
"""

import fnmatch
import json
import logging
import urllib
import urllib2

from cookielib import CookieJar
from socket import error as socket_error
from errno import ECONNRESET
from urlparse import urlunparse

import six

from .data import (
    HostJsonDecoder,
    InstanceV2ToServiceStatusJsonDecoder,
    ServiceJsonDecoder,
    ServiceJsonEncoder,
    ServiceStatusJsonDecoder,
)
from .environment import configuration as cc_config

LOG = logging.getLogger("zen.controlplane.client")


def getCCVersion():
    """
    Checks if the client is connecting to Hoth or newer. The cc version
    is injected in the containers by serviced
    """
    cc_version = cc_config.version
    if cc_version:  # CC is >= 1.2.0
        LOG.debug("Detected CC version >= 1.2.0")
    else:
        cc_version = "1.1.X"
    return cc_version


class ControlCenterError(Exception):
    pass


class _Request(urllib2.Request):
    """
    Extend urllib2.Request to override the get_method() method so that
    the HTTP method can be specified.
    """

    def __init__(self, *args, **kwargs):
        self.__method = kwargs.pop("method", None)
        urllib2.Request.__init__(self, *args, **kwargs)

    def get_method(self):
        return (
            self.__method
            if self.__method
            else urllib2.Request.get_method(self)
        )


class ControlPlaneClient(object):
    """ """

    def __init__(self, user, password, host=None, port=None):
        """ """
        self._cj = CookieJar()
        self._opener = urllib2.build_opener(
            urllib2.HTTPHandler(),
            urllib2.HTTPSHandler(),
            urllib2.HTTPCookieProcessor(self._cj),
        )
        # Zproxy always provides a proxy to serviced on port 443
        self._server = {
            "host": "127.0.0.1",
            "port": 443,
        }
        self._creds = {"username": user, "password": password}
        self._netloc = "%(host)s:%(port)s" % self._server
        self.cc_version = getCCVersion()
        self._hothOrNewer = False if self.cc_version == "1.1.X" else True
        self._useHttps = self._checkUseHttps()
        self._v2loc = "/api/v2"
        self._servicesEndpoint = "%s/services" % self._v2loc

    def _checkUseHttps(self):
        """
        Starting in CC 1.2.0, port 443 in the containers does not support https.
        """
        use_https = True
        cc_master = self._server.get("host")
        if self._hothOrNewer and cc_master in ["localhost", "127.0.0.1"]:
            use_https = False
        return use_https

    def queryServices(self, name=None, tags=None, tenantID=None):
        """
        Returns a sequence of ServiceDefinition objects that match
        the given requirements.
        """
        query = {}
        if name:
            namepat = fnmatch.translate(name)
            # controlplane regex accepts \z, not \Z.
            namepat = namepat.replace("\\Z", "\\z")
            query["name"] = namepat
        if tags:
            if isinstance(tags, six.string_types):
                tags = [tags]
            query["tags"] = ",".join(tags)
        if tenantID:
            query["tenantID"] = tenantID
        response = self._dorequest(self._servicesEndpoint, query=query)
        body = "".join(response.readlines())
        response.close()
        decoded = ServiceJsonDecoder().decode(body)
        if decoded is None:
            decoded = []
        return decoded

    def getService(self, serviceId, default=None):
        """
        Returns the ServiceDefinition object for the given service.
        """
        response = self._dorequest("/services/%s" % serviceId)
        body = "".join(response.readlines())
        response.close()
        return ServiceJsonDecoder().decode(body)

    def getChangesSince(self, age):
        """
        Returns a sequence of ServiceDefinition objects that have changed
        within the given age.  If there are no changes, and empty sequence
        is returned.

        :param age: How far back to look, in milliseconds, for changes.
        """
        query = {"since": age}
        response = self._dorequest(self._servicesEndpoint, query=query)
        body = "".join(response.readlines())
        response.close()
        decoded = ServiceJsonDecoder().decode(body)
        if decoded is None:
            decoded = []
        return decoded

    def updateServiceProperty(self, service, prop):
        """
        Updates the launch property of a service.

        :param ServiceDefinition service: The modified definition
        """
        oldService = self.getService(service.id)
        oldService._data[prop] = service._data[prop]
        body = ServiceJsonEncoder().encode(oldService)
        LOG.info(
            "Updating prop '%s' for service '%s':%s resourceId=%s",
            prop,
            service.name,
            service.id,
            service.resourceId,
        )
        LOG.debug("Updating service %s", body)
        response = self._dorequest(service.resourceId, method="PUT", data=body)
        body = "".join(response.readlines())
        response.close()

    def updateService(self, service):
        """
        Updates the definition/state of a service.

        :param ServiceDefinition service: The modified definition
        """
        body = ServiceJsonEncoder().encode(service)
        LOG.info("Updating service '%s':%s", service.name, service.id)
        LOG.debug("Updating service %s", body)
        response = self._dorequest(service.resourceId, method="PUT", data=body)
        body = "".join(response.readlines())
        response.close()

    def startService(self, serviceId):
        """
        Start the given service

        :param string ServiceId: The service to start
        """
        LOG.info("Starting service '%s", serviceId)
        response = self._dorequest(
            "/services/%s/startService" % serviceId, method="PUT"
        )
        body = "".join(response.readlines())
        response.close()
        return ServiceJsonDecoder().decode(body)

    def stopService(self, serviceId):
        """
        Stop the given service

        :param string ServiceId: The service to stop
        """
        LOG.info("Stopping service %s", serviceId)
        response = self._dorequest(
            "/services/%s/stopService" % serviceId, method="PUT"
        )
        body = "".join(response.readlines())
        response.close()
        return ServiceJsonDecoder().decode(body)

    def addService(self, serviceDefinition):
        """
        Add a new service

        :param string serviceDefinition: json encoded representation of service
        :returns string: json encoded representation of new service's links
        """
        LOG.info("Adding service")
        LOG.debug(serviceDefinition)
        response = self._dorequest(
            "/services/add", method="POST", data=serviceDefinition
        )
        body = "".join(response.readlines())
        response.close()
        return body

    def deleteService(self, serviceId):
        """
        Delete a service

        :param string serviceId: Id of the service to delete
        """
        LOG.info("Removing service %s", serviceId)
        response = self._dorequest("/services/%s" % serviceId, method="DELETE")
        response.close()

    def deployService(self, parentId, service):
        """
        Deploy a new service

        :param string parentId: parent service id
        :param string service: json encoded representation of service
        :returns string: json encoded representation of new service's links
        """
        LOG.info("Deploying service")
        data = {"ParentID": parentId, "Service": json.loads(service)}
        LOG.debug(data)
        response = self._dorequest(
            "/services/deploy", method="POST", data=json.dumps(data)
        )
        body = "".join(response.readlines())
        response.close()
        return body

    def queryServiceInstances(self, serviceId):
        """
        Returns a sequence of ServiceInstance objects.
        """
        response = self._dorequest("/services/%s/running" % serviceId)
        body = "".join(response.readlines())
        response.close()
        return ServiceJsonDecoder().decode(body)

    def queryServiceStatus(self, serviceId):
        """
        CC version-independent call to get the status of a service.
        Calls queryServiceStatusImpl or queryServiceInstancesV2 to get the
        status for serviceId.

        :param serviceId: The serviceId to get the status of
        :type serviceId: string

        :returns: The result of the query decoded
        :rtype: dict of ServiceStatus objects with ID as key
        """
        if self._hothOrNewer:
            raw = self.queryServiceInstancesV2(serviceId)
            decoded = self._convertInstancesV2ToStatuses(raw)
        else:
            decoded = self.queryServiceStatusImpl(serviceId)

        return decoded

    def queryServiceStatusImpl(self, serviceId):
        """
        Implementation for queryServiceStatus that uses the
        /services/:serviceid/status endpoint.

        :param serviceId: The serviceId to get the status of
        :type serviceId: string

        :returns: The result of the query decoded
        :rtype: dict of ServiceStatus objects with ID as key
        """
        response = self._dorequest("/services/%s/status" % serviceId)
        body = "".join(response.readlines())
        response.close()
        decoded = ServiceStatusJsonDecoder().decode(body)
        return decoded

    def queryServiceInstancesV2(self, serviceId):
        """
        Uses the CC V2 api to query the instances of serviceId.

        :param serviceId: The serviceId to get the instances of
        :type serviceId: string

        :returns: The raw result of the query
        :rtype: json formatted string
        """
        response = self._dorequest(
            "%s/services/%s/instances" % (self._v2loc, serviceId)
        )
        body = "".join(response.readlines())
        response.close()
        return body

    def _convertInstancesV2ToStatuses(self, rawV2Instance):
        """
        Converts a list of raw Instance (V2) json to a dict of ServiceStatuses.
        This is for compatibility sake.

        :param rawV2Instance: The result from a call to queryServiceInstancesV2
        :type rawV2Instance: json formatted string

        :returns: An acceptable output from queryServiceStatus
        :rtype: dict of ServiceStatus objects with ID as key
        """
        decoded = InstanceV2ToServiceStatusJsonDecoder().decode(rawV2Instance)
        # V2 gives us a list, we need a dict with ID as key
        decoded = {instance.id: instance for instance in decoded}
        return decoded

    def queryHosts(self):
        """
        Returns a sequence of Host objects.
        """
        response = self._dorequest("/hosts")
        body = "".join(response.readlines())
        response.close()
        return HostJsonDecoder().decode(body)

    def getHost(self, hostId):
        """
        Returns a sequence of Host objects.
        """
        response = self._dorequest("/hosts/%s" % hostId)
        body = "".join(response.readlines())
        response.close()
        return HostJsonDecoder().decode(body)

    def getInstance(self, serviceId, instanceId, default=None):
        """
        Returns the requested ServiceInstance object.
        """
        response = self._dorequest(
            "/services/%s/running/%s" % (serviceId, instanceId)
        )
        body = "".join(response.readlines())
        response.close()
        return ServiceJsonDecoder().decode(body)

    def getServiceLog(self, serviceId, start=0, end=None):
        """ """
        response = self._dorequest("/services/%s/logs" % serviceId)
        body = "".join(response.readlines())
        response.close()
        log = json.loads(body)
        return log["Detail"]

    def getInstanceLog(self, serviceId, instanceId, start=0, end=None):
        """ """
        response = self._dorequest(
            "/services/%s/%s/logs" % (serviceId, instanceId)
        )
        body = "".join(response.readlines())
        response.close()
        log = json.loads(body)
        return str(log["Detail"])

    def killInstance(self, hostId, uuid):
        """ """
        response = self._dorequest(
            "/hosts/%s/%s" % (hostId, uuid), method="DELETE"
        )
        response.close()

    def getServicesForMigration(self, serviceId):
        """ """
        query = {"includeChildren": "true"}
        response = self._dorequest("/services/%s" % serviceId, query=query)
        body = "".join(response.readlines())
        response.close()
        return json.loads(body)

    def postServicesForMigration(self, data, serviceId):
        """ """
        response = self._dorequest(
            "/services/%s/migrate" % serviceId, method="POST", data=data
        )
        body = "".join(response.readlines())
        response.close()
        return body

    def getPoolsData(self):
        """
        Get all the pools and return raw json
        """
        response = self._dorequest("/pools")
        body = "".join(response.readlines())
        response.close()
        return body

    def getHostsData(self):
        """
        Get all the pools and return raw json
        """
        response = self._dorequest("/hosts")
        body = "".join(response.readlines())
        response.close()
        return body

    def getRunningServicesData(self):
        """
        Get all the running services and return raw json
        """
        body = ""
        if not self._hothOrNewer:
            response = self._dorequest("/running")
            body = "".join(response.readlines())
            response.close()
        else:
            hostsData = self.queryHosts()
            for hostID in hostsData:
                response = self._dorequest("/hosts/%s/running" % hostID)
                body = body + "".join(response.readlines())
                response.close()
        return body

    def getStorageData(self):
        """
        Get the storage information and return raw json
        """
        response = self._dorequest("/storage")
        body = "".join(response.readlines())
        response.close()
        return body

    def _makeRequest(self, uri, method=None, data=None, query=None):
        query = urllib.urlencode(query) if query else ""
        url = urlunparse(
            (
                "https" if self._useHttps else "http",
                self._netloc,
                uri,
                "",
                query,
                "",
            )
        )
        args = {}
        if method:
            args["method"] = method
        if data:
            args["data"] = data
            args["headers"] = {"Content-Type": "application/json"}
        return _Request(url, **args)

    def _login(self):
        # Clear the cookie jar before logging in.
        self._cj.clear()
        encodedbody = json.dumps(self._creds)
        request = self._makeRequest("/login", data=encodedbody)
        response = self._opener.open(request)
        response.close()
        self._opener.close()

    def _dorequest(self, uri, method=None, data=None, query=None):
        # Try to perform the request up to five times
        for trycount in range(5):
            request = self._makeRequest(
                uri, method=method, data=data, query=query
            )
            try:
                return self._opener.open(request)
            except urllib2.HTTPError as ex:
                if ex.getcode() == 401:
                    self._login()
                    continue
                elif ex.getcode() == 500:
                    # Make the exception prettier and reraise it
                    try:
                        msg = json.load(ex)
                    except ValueError:
                        raise ex  # This stinks because we lose the stack
                    detail = msg.get("Detail")
                    if not detail:
                        raise
                    detail = detail.replace("Internal Server Error: ", "")
                    raise ControlCenterError(detail)
                raise
            # The CC server resets the connection when an unauthenticated
            # POST requesti is made.  Depending on when during the request
            # lifecycle the connection is reset, we can get either an
            # URLError with a socket.error as the reason, or  a naked
            # socket.error.  In either case, the socket.error.errno
            # indicates that the connection was reset with an errno of
            # ECONNRESET (104). When we get a connection reset exception,
            # assume that the reset was caused by lack of authentication,
            # login, and retry the request.
            except urllib2.URLError as ex:
                reason = ex.reason
                if (
                    isinstance(reason, socket_error)
                    and reason.errno == ECONNRESET
                ):
                    self._login()
                    continue
                raise
            except socket_error as ex:
                if ex.errno == ECONNRESET:
                    self._login()
                    continue
                raise
            else:
                # break the loop so we skip the loop's else clause
                break

        else:
            # raises the last exception that was raised (the 401 error)
            raise

    def _get_cookie_jar(self):
        return self._cj

    def cookies(self):
        """
        Get the cookie(s) being used.  If the cookie/cookiejar implementation
        changes, this method should be revisited.

        Return a list of dicts of cookies of the form:
            {
                'name':  'cookieName',
                'value': 'cookieValue',
                'domain': 'cookieDomain',
                'path': 'cookiePath',
                'expires': seconds from epoch to expore cookie, # leave blank to be a session cookie
                'secure': False/True,
            }
        """
        self._login()
        cookies = []
        for cookie in self._get_cookie_jar():
            cookies.append(
                {
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain,
                    "path": cookie.path,
                    "expires": cookie.expires,
                    "secure": cookie.discard,
                }
            )
        return cookies


# Define the names to export via 'from client import *'.
__all__ = ("ControlPlaneClient", "ControlCenterError")
