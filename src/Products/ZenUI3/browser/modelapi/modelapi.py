##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, 2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json
import logging
import os

import requests

from Products.Five.browser import BrowserView

from Products import Zuul

log = logging.getLogger("zen.RMMonitor.modelapi")


class RabbitQueues(BrowserView):
    """
    This view emits the RabbitMQ queues of the Zenoss system
    """

    def __call__(self):
        from Products.ZenUtils.GlobalConfig import getGlobalConfiguration

        config = getGlobalConfiguration()
        user = config.get("amqpuser", "zenoss")
        password = config.get("amqppassword", "zenoss")
        queueData = json.loads(
            requests.get(
                "http://localhost:15672/api/queues/%2Fzenoss",
                auth=requests.auth.HTTPBasicAuth(user, password),
            ).content
        )
        queueMaps = [
            dict(id=queue["name"]) for queue in queueData if queue["durable"]
        ]
        self.request.response.write(json.dumps(dict(durableQueues=queueMaps)))


class ZenossRMDevice(BrowserView):
    """
    This view emits the device level info for modeling a Zenoss system
    """

    def __call__(self):
        modelInfo = {}
        modelInfo["controlplaneTenantId"] = os.environ.get(
            "CONTROLPLANE_TENANT_ID", None
        )
        self.request.response.write(json.dumps(modelInfo))


class CollectorInfo(BrowserView):
    """
    This view emits the hub component info for modeling a Zenoss system
    """

    def __call__(self):
        appfacade = Zuul.getFacade("applications")
        zenHubs = []
        collectors = []
        collectorDaemons = []

        for hub in self.context.dmd.Monitors.Hub.objectValues(spec="HubConf"):
            hubService = appfacade.queryHubDaemons(hub.id)[0]
            zenHubs.append(
                dict(
                    id="hub_{}".format(hub.id),
                    title=hub.id,
                    controlplaneServiceId=hubService.id,
                    lastModeledState=str(hubService.state).lower(),
                    RAMCommitment=getattr(hubService, "RAMCommitment", None),
                    instanceCount=hubService.instances,
                )
            )

            for collector in hub.collectors():
                collectors.append(
                    dict(
                        id="collector_{}".format(collector.id),
                        title=collector.id,
                        set_hub="hub_{}".format(hub.id),
                    )
                )

                for collectorDaemon in appfacade.queryMonitorDaemons(
                    collector.id
                ):
                    if collectorDaemon.name in (
                        "collectorredis",
                        "MetricShipper",
                        "zenmodeler",
                        "zminion",
                    ):
                        continue
                    collectorDaemons.append(
                        dict(
                            id="{}_{}".format(
                                collectorDaemon.name, collector.id
                            ),
                            title="{} - {}".format(
                                collectorDaemon.name, collector.id
                            ),
                            controlplaneServiceId=collectorDaemon.id,
                            instanceCount=collectorDaemon.instances,
                            lastModeledState=str(
                                collectorDaemon.state
                            ).lower(),
                            RAMCommitment=getattr(
                                collectorDaemon, "RAMCommitment", None
                            ),
                            set_collector="collector_{}".format(collector.id),
                            monitor=collectorDaemon.autostart,
                        )
                    )

        self.request.response.write(
            json.dumps(
                dict(
                    zenHubs=zenHubs,
                    collectors=collectors,
                    collectorDaemons=collectorDaemons,
                )
            )
        )


class MetricServices(BrowserView):
    """
    This view emits info for redis, MetricShipper, and MetricConsumer services
    """

    def __call__(self):
        appfacade = Zuul.getFacade("applications")
        idFormat = "{}_{}"
        titleFormat = "{} - {}"

        def getRedises(svcName, metricShipperParent=None):
            redises = []
            for svc in appfacade.query(svcName):
                parentName = appfacade.get(svc.parentId).name
                shipperParentName = (
                    metricShipperParent if metricShipperParent else parentName
                )
                metricShipper = "MetricShipper_{}".format(shipperParentName)
                redises.append(
                    dict(
                        id=idFormat.format(svc.name, parentName),
                        title=titleFormat.format(svc.name, parentName),
                        controlplaneServiceId=svc.id,
                        RAMCommitment=getattr(svc, "RAMCommitment", None),
                        instanceCount=svc.instances,
                        lastModeledState=str(svc.state).lower(),
                        set_metricShipper=metricShipper,
                    )
                )
            return redises

        redises = getRedises("redis", "Metrics")
        redises.extend(getRedises("collectorredis"))

        metricShippers = []
        for svc in appfacade.query("MetricShipper"):
            parentName = appfacade.get(svc.parentId).name
            if parentName == "Metrics":
                redis = "redis_Infrastructure"
            else:
                redis = "collectorredis_{}".format(parentName)
            data = dict(
                id=idFormat.format(svc.name, appfacade.get(svc.parentId).name),
                title=titleFormat.format(
                    svc.name, appfacade.get(svc.parentId).name
                ),
                controlplaneServiceId=svc.id,
                instanceCount=svc.instances,
                RAMCommitment=getattr(svc, "RAMCommitment", None),
                lastModeledState=str(svc.state).lower(),
                set_redis=redis,
            )
            metricShippers.append(data)

        consumerService = appfacade.query("MetricConsumer")[0]
        metricConsumers = [
            dict(
                id="MetricConsumer",
                title="MetricConsumer",
                controlplaneServiceId=consumerService.id,
                lastModeledState=str(consumerService.state).lower(),
                RAMCommitment=getattr(consumerService, "RAMCommitment", None),
                instanceCount=consumerService.instances,
            )
        ]

        queryService = appfacade.query("CentralQuery")[0]
        centralQueries = [
            dict(
                id="CentralQuery",
                title="CentralQuery",
                controlplaneServiceId=queryService.id,
                lastModeledState=str(queryService.state).lower(),
                RAMCommitment=getattr(queryService, "RAMCommitment", None),
                instanceCount=queryService.instances,
            )
        ]

        data = dict(
            redises=redises,
            metricShippers=metricShippers,
            metricConsumers=metricConsumers,
            centralQueries=centralQueries,
        )

        self.request.response.write(json.dumps(data))


class BaseApiView(BrowserView):
    """
    Base for several highly similar views
    """

    def __init__(self, context, request):
        super(BaseApiView, self).__init__(context, request)
        self._appfacade = Zuul.getFacade("applications")

    def _getServices(self, svcName):
        return [
            dict(
                id=svc.name,
                controlplaneServiceId=svc.id,
                instanceCount=svc.instances,
                RAMCommitment=getattr(svc, "RAMCommitment", None),
                lastModeledState=str(svc.state).lower(),
            )
            for svc in self._appfacade.query(svcName)
        ]

    def __call__(self):
        data = {}
        for compKey, svcName in self._services:
            data[compKey] = self._getServices(svcName)
        self.request.response.write(json.dumps(data))


class EventDaemons(BaseApiView):
    """
    This view emits info for zeneventd, zeneventserver, and zenactiond
    """

    @property
    def _services(self):
        return (
            ("zenEventDs", "zeneventd"),
            ("zenEventServers", "zeneventserver"),
            ("zenActionDs", "zenactiond"),
        )


class Solr(BaseApiView):
    """
    This view emits the Solr stats of the Zenoss system
    """

    @property
    def _services(self):
        return (("solrs", "Solr"),)


class ZenModeler(BaseApiView):
    """
    This view emits info regarding zenmodelers of the Zenoss system
    """

    @property
    def _services(self):
        return (("zenModelers", "zenmodeler"),)

    def _getServices(self, svcName):
        idFormat = "{}_{}"
        titleFormat = "{} - {}"
        return [
            dict(
                id=idFormat.format(
                    svc.name, self._appfacade.get(svc.parentId).name
                ),
                title=titleFormat.format(
                    svc.name, self._appfacade.get(svc.parentId).name
                ),
                controlplaneServiceId=svc.id,
                instanceCount=svc.instances,
                RAMCommitment=getattr(svc, "RAMCommitment", None),
                lastModeledState=str(svc.state).lower(),
            )
            for svc in self._appfacade.query(svcName)
        ]


class RegionServer(BaseApiView):
    """
    This view emits info for the HBase regionservers in the Zenoss application.
    """

    @property
    def _services(self):
        return (("regionServers", "RegionServer"),)

    def _getServices(self, svcName):
        svc = next(iter(self._appfacade.query(svcName)), None)
        if not svc:
            return []
        count = svc.instances
        titleFormat = "{} - {}"
        return [
            dict(id=str(i), title=titleFormat.format(svc.name, i))
            for i in range(count)
        ]


class Zope(BaseApiView):
    """
    Zope info
    """

    @property
    def _services(self):
        return (("zopes", "zopes"),)

    def _getServiceInstances(self, name):
        idFormat = "{}_{}"
        titleFormat = "{} - {}"
        services = self._appfacade.query(name)
        if not services:
            return []
        svc = services[0]
        data = [
            dict(
                id=idFormat.format(name, i), title=titleFormat.format(name, i)
            )
            for i in range(svc.instances)
        ]
        return data

    def _getServices(self, svcName):
        zopes = self._getServiceInstances("Zope")
        zopes += self._getServiceInstances("zenapi")
        zopes += self._getServiceInstances("zenreports")
        zopes += self._getServiceInstances("Zauth")

        return zopes


class ZODB(BaseApiView):
    """
    This view emits the ZODB stats of the Zenoss system
    """

    @property
    def _services(self):
        return (("zodbs", "mariadb-model"),)


class Reader(BaseApiView):
    """
    This view emits the reader stats of the Zenoss system
    """

    @property
    def _services(self):
        return (("readers", "reader"),)

    def _getServices(self, svcName):
        readers = super(Reader, self)._getServices("reader")
        return readers


class Writer(BaseApiView):
    """
    This view emits the writer stats of the Zenoss system
    """

    @property
    def _services(self):
        return (("writers", "writer"),)

    def _getServices(self, svcName):
        writers = super(Writer, self)._getServices("writer")
        return writers

class ImpactDaemons(BaseApiView):
    """
    This view emits the Impact daemon services
    """
    @property
    def _services(self):
        return (
            ('impacts', 'Impact'),
            ('zenImpactStates', 'zenimpactstate'),
        )

class Memcached(BaseApiView):

    @property
    def _services(self):
        return (
            ('memcacheds', 'memcacheds'),
        )

    def _getServiceInstances(self, name):
        idFormat = '{}'
        titleFormat = '{}'
        services = self._appfacade.query(name)
        if not services:
            return []
        svc = services[0]
        data = [dict(id=idFormat.format(name),
                     title=titleFormat.format(name),
                     controlplaneServiceId=svc.id,
                     instanceCount=svc.instances,
                     RAMCommitment=getattr(svc, 'RAMCommitment', None),
                     lastModeledState=str(svc.state).lower()
                     )
                for i in range(svc.instances)]
        return data

    def _getServices(self, svcName):
        memcacheds = self._getServiceInstances('memcached')
        memcacheds += self._getServiceInstances('memcached-session')
        return memcacheds

class ConfigCacheDaemons(BaseApiView):
    """
    This view emits info for configcache services: invalidator, builders, and manager
    """
    @property
    def _services(self):
        return (
            ('configCacheInvalidators', 'invalidator'),
            ('configCacheBuilders', 'builder'),
            ('configCacheManagers', 'manager'),
        )

class ZenjobsMonitor(BaseApiView):
    """
    This view emits info for zenjobs-monitor
    """
    @property
    def _services(self):
        return (
            ('zenjobsMonitors', 'zenjobs-monitor'),
        )

