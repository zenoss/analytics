##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
Operations for Networks.

Available at:  /zport/dmd/network_router
"""

import logging

from Products import Zuul
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.Ext import DirectResponse
from Products.ZenUtils.IpUtil import IpAddressError
from Products.ZenUtils.jsonutils import unjson
from Products.ZenUtils.Utils import getDisplayType
from Products.Zuul.decorators import require, serviceConnectionError
from Products.Zuul.interfaces import ITreeNode

from . import TreeRouter

log = logging.getLogger("zen.NetworkRouter")


JOBKEYS = [
    "uuid",
    "status",
    "scheduled",
    "finished",
    "duration",
    "logfile",
]


class NetworkRouter(TreeRouter):
    """A JSON/ExtDirect interface to operations on networks.
    """

    def __init__(self, context, request):
        super(NetworkRouter, self).__init__(context, request)
        self.api = Zuul.getFacade("network")

    def _getFacade(self):
        return Zuul.getFacade("network", self.context)

    @require("Manage DMD")
    def discoverDevices(self, uid, collector=None):
        """Discover devices on a network.

        @type  uid: string
        @param uid: Unique identifier of the network to discover
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - jobId: (integer) The id of the discovery job
        """
        jobStatus = self.api.discoverDevices(uid, collector)
        if jobStatus:
            audit("UI.Network.DiscoverDevices", uid)
            return DirectResponse.succeed(
                new_jobs=Zuul.marshal(
                    [jobStatus], keys=("uuid", "description", "started")
                )
            )
        else:
            return DirectResponse.fail()

    @require("Manage DMD")
    def addNode(self, newSubnet, contextUid):
        """Add a new subnet.

        @type  newSubnet: string
        @param newSubnet: New subnet to add
        @type  contextUid: string
        @param contextUid: Unique identifier of the network parent
            of the new subnet
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - newNode: (dictionary) An object representing the new subnet node
        """
        # If the user doesn't include a mask, reject the request.
        if "/" not in newSubnet:
            return DirectResponse.fail("You must include a subnet mask.")

        try:
            netip, netmask = newSubnet.split("/")
            netmask = int(netmask)
            foundSubnet = self.api.findSubnet(netip, netmask, contextUid)

            if foundSubnet is not None:
                response = DirectResponse.fail(
                    "Did not add duplicate subnet: %s (%s/%s)"
                    % (newSubnet, foundSubnet.id, foundSubnet.netmask)
                )
            else:
                newNet = self.api.addSubnet(newSubnet, contextUid)
                node = ITreeNode(newNet)
                audit("UI.Network.AddSubnet", contextUid, subnet=newSubnet)
                response = DirectResponse.succeed(newNode=Zuul.marshal(node))
        except IpAddressError as error:
            response = DirectResponse.exception(error, "Error adding subnet.")
        except Exception as error:
            log.exception("Error adding subnet.")
            response = DirectResponse.exception(error, "Error adding subnet.")
        return response

    @require("Manage DMD")
    def deleteNode(self, uid):
        """Delete a subnet.

        @type  uid: string
        @param uid: Unique identifier of the subnet to delete
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - tree: (dictionary) An object representing the new network tree
        """
        self.api.deleteSubnet(uid)
        audit("UI.Network.DeleteSubnet", subnet=uid)
        return DirectResponse.succeed("Network removed")

    def getTree(self, id="/zport/dmd/Networks"):
        """
        Returns the tree structure of an organizer hierarchy where
        the root node is the organizer identified by the id parameter.

        @type  id: string
        @param id: Id of the root node of the tree to be returned. Defaults to
                   the Networks tree root.
        @rtype:   [dictionary]
        @return:  Object representing the tree
        """
        tree = self.api.getTree(id)
        data = Zuul.marshal(tree)
        return [data]

    def getInfo(self, uid, keys=None):
        """Returns a dictionary of the properties of an object.

        @type  uid: string
        @param uid: Unique identifier of an object
        @type  keys: list
        @param keys: (optional) List of keys to include in the returned
                     dictionary. If None then all keys will be returned
        @rtype:   DirectResponse
        @return:  B{Properties}
            - data: (dictionary) Object properties
        """
        network = self.api.getInfo(uid)
        data = Zuul.marshal(network, keys)
        disabled = not Zuul.checkPermission("Manage DMD")
        return DirectResponse.succeed(data=data, disabled=disabled)

    @require("Manage DMD")
    def setInfo(self, **data):
        """Set attributes on a network or network organizer.

        This method accepts any keyword argument for the property that you wish
        to set. The only required property is "uid".

        @type    uid: string
        @keyword uid: Unique identifier of an object
        @rtype: DirectResponse
        """
        network = self.api.getInfo(data["uid"])
        Zuul.unmarshal(data, network)
        audit(["UI", getDisplayType(network), "Edit"], network, data_=data)
        return DirectResponse.succeed()

    @serviceConnectionError
    def getIpAddresses(
        self,
        uid,
        start=0,
        params=None,
        limit=50,
        sort="ipAddressAsInt",
        page=None,
        dir="ASC",
    ):
        """Given a subnet, get a list of IP addresses and their relations.

        @type  uid: string
        @param uid: Unique identifier of a subnet
        @type  start: integer
        @param start: Offset to return the results from; used in pagination
        @type  params: string
        @param params: Not used
        @type  limit: integer
        @param limit: Number of items to return; used in pagination
        @type  sort: string
        @param sort: (optional) Key on which to sort the return results;
                     defaults to 'name'
        @type  order: string
        @param order: Sort order; can be either 'ASC' or 'DESC'
        @rtype: DirectResponse
        """
        if isinstance(params, basestring):
            params = unjson(params)
        instances = self.api.getIpAddresses(
            uid=uid,
            start=start,
            params=params,
            limit=limit,
            sort=sort,
            dir=dir,
        )

        keys = [
            "name",
            "netmask",
            "pingstatus",
            "snmpstatus",
            "uid",
            "device",
            "interface",
            "macAddress",
            "interfaceDescription",
            "manageDevice",
        ]
        data = Zuul.marshal(instances.results, keys)
        return DirectResponse.succeed(
            data=data, totalCount=instances.total, hash=instances.hash_
        )

    def removeIpAddresses(self, uids=None):
        """
        Removes every ip address specified by uids that are
        not attached to any device.

        @type  uids: Array of Strings
        @param uids: unique identfiers of the ip addresses to delete
        """
        if uids:
            removedCount, errorCount = self.api.removeIpAddresses(uids)
            audit(
                "UI.IPAddress.Remove",
                ips=uids,
                numremoved=removedCount,
                numerrors=errorCount,
            )
            return DirectResponse.succeed(
                removedCount=removedCount, errorCount=errorCount
            )

    def newDiscoveryJob(
        self, networks=None, zProperties=None, collector="localhost"
    ):
        jobs = self.api.newDiscoveryJob(
            networks=networks, zProperties=zProperties, collector=collector
        )
        audit("UI.Discovery.Add", networks=networks, collector=collector)
        return DirectResponse.succeed(data=Zuul.marshal(jobs, keys=JOBKEYS))


class Network6Router(NetworkRouter):
    """A JSON/ExtDirect interface to operations on IPv6 networks.
    """

    def __init__(self, context, request):
        super(NetworkRouter, self).__init__(context, request)
        self.api = Zuul.getFacade("network6")

    def _getFacade(self):
        return Zuul.getFacade("network6", self.context)
