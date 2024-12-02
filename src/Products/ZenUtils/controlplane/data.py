##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
Application JSON format:

    'query' result
    [
        <application-node>,...
    ]

    /services/<service-id> 'get' result example
    {
        "ID":              "9827-939070095",
        "Name":            "zentrap",
        "Startup":         "/bin/true",
        "Description":     "This is a collector daemon 4",
        "Instances":       0,
        #"Running": [
        #    {
        #      "ID": "28ea1c28-8491-2afc-fd9d-fe207046be05",
        #      "ServiceID": "c412e4cf-48be-b53d-d144-867ffa596ffa",
        #      "HostID": "007f0101",
        #      "DockerID": "3b52fc18767f",
        #      "StartedAt": "2013-10-29T17:59:13-05:00",
        #    }
        #]
        "ConfigFiles": {
            "/etc/my.cnf": {
                "Filename": "/etc/my.cnf",
                "Owner": "",
                "Permissions": 0,
                "Content": "\n# SAMPLE config file for mysql\n\n[mysqld]\n\ninnodb_buffer_pool_size = 16G\n\n"
            }
        },
        "ImageID":         "zenoss",
        "PoolID":          "default",
        "DesiredState":    1,
        "Launch":          "auto",
        "Endpoints":       {
            "Protocol" : "tcp",
            "PortNumber": 6379,
            "Application": "redis",
            "Purpose": "export"
        },
        "ParentServiceID": "293482085035",
        "CreatedAt":       "0001-01-01T00:00:00Z",
        "UpdatedAt":       "2013-10-29T07:31:22-05:00"
    }
    missing current-state, conf, and log.

    /services/<service-id>/running example
    [
      {
        "ID": "28ea1c28-8491-2afc-fd9d-fe207046be05",
        "ServiceID": "c412e4cf-48be-b53d-d144-867ffa596ffa",
        "HostID": "007f0101",
        "DockerID": "3b52fc18767f",
        "StartedAt": "2013-10-29T17:59:13-05:00",
        "Name": "redis",
        "Startup": "/usr/sbin/redis-server",
        "Description": "",
        "Instances": 1,
        "ImageID": "zenoss/redis",
        "PoolID": "default",
        "DesiredState": 1,
        "ParentServiceID": ""
      }
    ]

    {
        "id":     <string>,
        "name":   <string>,
        "uri":    <string>,
        "tags":   [<string>, ...],
        "log":    <uri-string>,
        "conf":   <uri-string>,
        "status": <string>,
        "state":  <string>,
    }
"""

import json
from datetime import datetime
from functools import wraps

from zope.component import createObject
from zope.component.factory import Factory
from zope.interface import implementer
from Products.ZenUtils.application import ApplicationState
from .interfaces import IServiceDefinition, IServiceInstance, IServiceStatus
from ..host import IHost



class _Value(object):
    """
    Helper class for creating objects that can behave as named
    constants that (optionally) convertable to an integer.
    """

    def __init__(self, name, value=None):
        self._name = name
        self._value = value if value is not None else name

    def __str__(self):
        return self._name

    def __int__(self):
        return int(self._value)

    def __repr__(self):
        return str(self._value)


# The set of keys found in a service definition JSON object.
# Used to identify such objects.
_definitionKeys = set([
    "ID", "Name", "ParentServiceID", "PoolID", "Description", "Launch",
    "DesiredState", "Tags", "ConfigFiles"
])

# The set of keys found in a service details JSON object.
# Used to identify such objects.
_detailsKeys = set([
    "ID", "Name", "ParentServiceID", "PoolID", "Description", "Launch",
    "RAMCommitment", "HasChildren", "InstanceLimits", "Startup", "Instances", "DeploymentID",
    "DesiredState", "Tags", "ImageID"
])

# The set of keys found in a service instance JSON object.
# Used to identify such objects.
_instanceKeys = set([
    "ID", "ServiceID", "HostID", "DockerID", "StartedAt", "Name",
    "Startup", "Description", "Instances", "ImageID",
    "PoolID", "DesiredState", "ParentServiceID"
])

_hostKeys = set([
    "ID", "Name", "PoolID", "Cores", "Memory"
])

def _decodeServiceJsonObject(obj):
    foundKeys = _definitionKeys & set(obj.keys())
    if foundKeys == _definitionKeys:
        service = createObject("ServiceDefinition")
        service.__setstate__(obj)
        return service
    foundKeys = _detailsKeys & set(obj.keys())
    if foundKeys == _detailsKeys:
        service = createObject("ServiceDefinition")
        service.__setstate__(obj)
        return service
    foundKeys = _instanceKeys & set(obj.keys())
    if foundKeys == _instanceKeys:
        instance = createObject("ServiceInstance")
        instance.__setstate__(obj)
        return instance
    return obj

def _decodeHostJsonObject(obj):
    foundKeys = _hostKeys & set(obj.keys())
    if foundKeys == _hostKeys:
        instance = createObject("Host")
        instance.__setstate__(obj)
        return instance
    return obj


class ServiceJsonDecoder(json.JSONDecoder):
    """
    """

    def __init__(self, **kwargs):
        kwargs.update({"object_hook": _decodeServiceJsonObject})
        super(ServiceJsonDecoder, self).__init__(**kwargs)


class HostJsonDecoder(json.JSONDecoder):
    def __init__(self, **kwargs):
        kwargs.update({"object_hook": _decodeHostJsonObject})
        super(HostJsonDecoder, self).__init__(**kwargs)


class ServiceJsonEncoder(json.JSONEncoder):
    """
    """

    def default(self, o):
        if isinstance(o, ServiceDefinition):
            return o.__getstate__()
        return json.JSONEncoder.default(self, o)

def _convertToDateTime(f):
    @wraps(f)
    def wrapper(*args, **kw):
        src = f(*args, **kw)
        trimmed = src[:19]
        if len(trimmed) == 19:
            return datetime.strptime(trimmed, "%Y-%m-%dT%H:%M:%S")
    return wrapper

def _convertToApplicationState(f):
    @wraps(f)
    def wrapper(*args, **kw):
        src = f(*args, **kw)
        return {
            "scheduled": ApplicationState.STARTING,
            "starting":  ApplicationState.STARTING,
            "pausing":   ApplicationState.STOPPING,
            "paused":    ApplicationState.STOPPED,
            "resuming":  ApplicationState.STARTING,
            "running":   ApplicationState.RUNNING,
            "stopping":  ApplicationState.STOPPING,
            "stopped":   ApplicationState.STOPPED,
            "started":   ApplicationState.RUNNING,
            "pulling":   ApplicationState.STARTING,
            "resumed":   ApplicationState.RUNNING,
            "pending_restart": ApplicationState.STARTING,
            "emergency_stopping": ApplicationState.STOPPING,
            "emergency_stopped": ApplicationState.STOPPED,
        }.get(src["Value"].lower(), ApplicationState.UNKNOWN)
    return wrapper

@implementer(IServiceInstance)
class ServiceInstance(object):
    """
    """

    def __getstate__(self):
        return self._data

    def __setstate__(self, data):
        self._data = data

    def __init__(self):
        self._data = {}

    @property
    def id(self):
        return self._data.get("ID")

    @property
    def resourceId(self):
        return "/services/%s/running/%s" % (
            self._data.get("ServiceID"), self._data.get("ID")
        )

    @property
    def serviceId(self):
        return self._data.get("ServiceID")

    @property
    def hostId(self):
        return self._data.get("HostID")

    @property
    @_convertToDateTime
    def startedAt(self):
        return self._data.get("StartedAt")


class ServiceInstanceFactory(Factory):
    """
    Factory for ServiceInstance objects.
    """

    def __init__(self):
        super(ServiceInstanceFactory, self).__init__(
            ServiceInstance, "ServiceInstance",
            "Control Plane Service Instance Description"
        )


@implementer(IServiceStatus)
class ServiceStatus(object):
    """
    """

    def __getstate__(self):
        return self._data

    def __setstate__(self, data):
        self._data = data

        # For V2 compatibility (V2 response doesn't have "State" property)
        if not self._data.get("State"):
            self._reformV2()

    def __init__(self):
        self._data = {}

    def _reformV2(self):
        # /services/:serviceid/status has an arbitrary 36 char UUID
        # V2 uses hostid-serviceid-instanceid
        self._data.setdefault("ID",
        self._data.get("HostID") + "-" +
        self._data.get("ServiceID") + "-" +
        str(self._data.get("InstanceID")))
        status = self._data.setdefault("CurrentState")
        del self._data["CurrentState"]
        self._data = {"State": self._data}
        # /services/:serviceid/status has a Key in Status as well, V2 doesn't
        self._data["Status"] = {"Value": status}

    @property
    def id(self):
        return self._data.get("State", {}).get("ID")

    @property
    def serviceId(self):
        return self._data.get("State", {}).get("ServiceID")

    @property
    def instanceId(self):
        return self._data.get("State", {}).get("InstanceID")

    @property
    def hostId(self):
        return self._data.get("State", {}).get("HostID")

    @property
    @_convertToDateTime
    def startedAt(self):
        return self._data.get("State", {}).get("Started")

    @property
    @_convertToApplicationState
    def status(self):
        return self._data.get("Status")


class ServiceStatusFactory(Factory):
    """
    Factory for ServiceStatus objects.
    """

    def __init__(self):
        super(ServiceStatusFactory, self).__init__(
            ServiceStatus, "ServiceStatus",
            "Control Plane Service Status Description"
        )


class ServiceStatusJsonDecoder(json.JSONDecoder):
    @staticmethod
    def _decodeObject(obj):
        if sorted(obj.keys()) == sorted(('HealthCheckStatuses', 'State', 'Status')):
            service = createObject("ServiceStatus")
            service.__setstate__(obj)
            return service
        return obj
    def __init__(self, **kwargs):
        kwargs.update({"object_hook": ServiceStatusJsonDecoder._decodeObject})
        super(ServiceStatusJsonDecoder, self).__init__(**kwargs)


_serviceStatusV2Keys = {
    'InstanceID', 'HostID', 'HostName', 'ServiceID', 'ServiceName', 'ContainerID',
    'ImageSynced', 'DesiredState', 'CurrentState', 'HealthStatus', 'RAMCommitment',
    'MemoryUsage', 'Scheduled', 'Started', 'Terminated'
}
class InstanceV2ToServiceStatusJsonDecoder(json.JSONDecoder):
    """
    Converts the result of a V2 Service Instance query to a ServiceStatus object
    """
    @staticmethod
    def _decodeObject(obj):
        if (set(obj.keys()) & _serviceStatusV2Keys) == _serviceStatusV2Keys:
            service = createObject("ServiceStatus")
            service.__setstate__(obj)
            return service
        return obj
    def __init__(self, **kwargs):
        kwargs.update({
            "object_hook": InstanceV2ToServiceStatusJsonDecoder._decodeObject
        })
        super(InstanceV2ToServiceStatusJsonDecoder, self).__init__(**kwargs)


@implementer(IServiceDefinition)
class ServiceDefinition(object):
    """
    """

    class LAUNCH_MODE(object):
        AUTO = _Value("AUTO", "auto")
        MANUAL = _Value("MANUAL", "manual")

    class STATE(object):
        RUN = _Value("RUN", 1)
        STOP = _Value("STOP", 0)
        RESTART = _Value("RESTART", -1)

    __map = {
        1: STATE.RUN, 0: STATE.STOP, -1: STATE.RESTART
    }

    def __getstate__(self):
        return self._data

    def __setstate__(self, data):
        self._data = data

    def __init__(self):
        """
        """
        self._data = {}

    def getRawData(self):
        """
        Getter for the _data attribute
        """
        return self._data

    @property
    def id(self):
        return self._data.get("ID")

    @property
    def parentId(self):
        return self._data.get('ParentServiceID')

    @property
    def poolId(self):
        return self._data.get('PoolID')

    @property
    def resourceId(self):
        return "/services/%s" % (self._data.get("ID"),)

    @property
    def name(self):
        return self._data.get("Name")

    @property
    def description(self):
        return self._data.get("Description")

    @property
    def RAMCommitment(self):
        return self._data.get("RAMCommitment")

    @description.setter
    def description(self, desc):
        self._data["Description"] = desc

    @property
    def tags(self):
        return self._data.get("Tags")

    @property
    def launch(self):
        return self.LAUNCH_MODE.__dict__.get(self._data.get("Launch").upper())

    @launch.setter
    def launch(self, value):
        if str(value) not in self.LAUNCH_MODE.__dict__:
            raise ValueError("Invalid status value: %s" % (value,))
        self._data["Launch"] = repr(value)

    @property
    def desiredState(self):
        return self.__map.get(self._data.get("DesiredState"))

    @desiredState.setter
    def desiredState(self, value):
        if str(value) not in self.STATE.__dict__:
            raise ValueError("Invalid state: %s" % (value,))
        self._data["DesiredState"] = int(value)

    @property
    def logResourceId(self):
        return self._data.get("LogId")

    @property
    def configFiles(self):
        """
        Returns a dict with this format:

           {
               "<filename>": {
                  "FileName": "<filename>",
                  "Content": "<contents-of-file-as-string>"
               },
               ...
           }

        The top-level keys are duplicated by the "FileName" key in the
        children dictionaries.
        """
        return self._data.get("ConfigFiles", {})

    @configFiles.setter
    def configFiles(self, configFiles):
        self._data['ConfigFiles'] = configFiles

    @property
    @_convertToDateTime
    def createdAt(self):
        return self._data.get("CreatedAt")

    @property
    @_convertToDateTime
    def updatedAt(self):
        return self._data.get("UpdatedAt")


class ServiceDefinitionFactory(Factory):
    """
    Factory for ServiceDefinition objects.
    """

    def __init__(self):
        super(ServiceDefinitionFactory, self).__init__(
            ServiceDefinition, "ServiceDefinition",
            "Control Plane Service Definition"
        )


@implementer(IHost)
class Host(object):
    """
    """
    def __getstate__(self):
        return self._data

    def __setstate__(self, data):
        self._data = data

    def __init__(self):
        self._data = {}

    @property
    def id(self):
        return self._data.get("ID")

    @property
    def name(self):
        return self._data.get("Name")

    @property
    def poolId(self):
        return self._data.get("PoolID")

    @property
    def ipAddr(self):
        return self._data.get("IPAddr")

    @property
    def cores(self):
        return self._data.get("Cores")

    @property
    def memory(self):
        return self._data.get("Memory")

    @property
    def privateNetwork(self):
        return self._data.get("PrivateNetwork")

    @property
    @_convertToDateTime
    def createdAt(self):
        return self._data.get("CreatedAt")

    @property
    @_convertToDateTime
    def updatedAt(self):
        return self._data.get("UpdatedAt")

    @property
    def kernelVersion(self):
        return self._data.get("KernelVersion")

    @property
    def kernelRelease(self):
        return self._data.get("KernelRelease")

class HostFactory(Factory):
    """
    Factory for Host objects.
    """

    def __init__(self):
        super(HostFactory, self).__init__(Host, "Host", "Control Plane Host Definition")

# Define the names to export via 'from data import *'.
__all__ = (
    "ServiceJsonDecoder", "ServiceJsonEncoder",
    "ServiceDefinition", "ServiceDefinitionFactory",
    "ServiceInstance", "ServiceInstanceFactory",
    "Host", "HostFactory"
)
