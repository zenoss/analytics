# The keys are the service names, and the values the (EmergencyShutdown, StartLevel) tuples.
serviceRunLevels = {
          "HMaster": (0, 1),
          "RegionServer": (1, 2),
          "ZooKeeper": (3, 1),
          "RabbitMQ": (2, 1),
          "mariadb": (1, 1),
          "memcached": (0, 1),
          "reader": (0, 3),
          "opentsdb": (0, 3),
          "writer": (0, 3),
          "redis": (2, 1),
          "collectorredis": (2, 2),
          "zenhub": (0, 2),
          "zeneventserver": (2, 2),
          "CentralQuery": (0, 3),
          "MetricConsumer": (0, 3),
          "MetricShipper": (0, 0),
          "Zauth": (0, 2),
          "Zope": (0, 0),
          "Zenoss.core.full": (0, 2),
          "Zenoss.core": (0, 2),
          "mariadb-events": (1, 1),
          "mariadb-model": (1, 1),
          "zencatalogservice": (2, 1),
          "Zenoss.resmgr.lite": (0, 2),
          "Zenoss.resmgr": (0, 2),
          "nfvi": (0, 2),
          "ucspm.lite": (0, 2),
          "ucspm": (0, 2),
          "Impact": (1, 1)
}
