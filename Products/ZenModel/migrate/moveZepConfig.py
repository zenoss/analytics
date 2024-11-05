##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """Move some parameters from zeneventserver.conf to ZepConfig so
changing them doesn't require a restart.
"""
import os
import logging
from Products.ZenUtils.path import zenPath
from Products.ZenModel.migrate import Migrate
from Products.Zuul import getFacade


log = logging.getLogger('zen.migrate')

class moveZepConfig(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    # translates zeneventserver.conf key to ZenConfig protocol buffer key
    _params = {"zep.aging.interval_milliseconds": "aging_interval_milliseconds",
               "zep.aging.limit": "aging_limit",
               "zep.archive.interval_milliseconds": "archive_interval_milliseconds",
               "zep.archive.limit": "archive_limit",
               "zep.index.summary.interval_milliseconds": "index_summary_interval_milliseconds",
               "zep.index.archive.interval_milliseconds": "index_archive_interval_milliseconds",
               "zep.index.limit": "index_limit",
              }

    def _read_from_conf(self, zeneventserver_conf):
        with open(zeneventserver_conf) as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split("=")]
                if len(parts) != 2:
                    continue
                key, value = parts
                for param in self._params:
                    if key == param:
                        yield self._params[key], value
                        break

    def cutover(self, dmd):
        zeneventserver_conf = zenPath("etc", "zeneventserver.conf")
        if not os.path.exists(zeneventserver_conf):
            return
        log.info("Moving parameters from zeneventserver.conf to zenoss_zep config table.")
        values = {}
        for config_name, config_value in self._read_from_conf(zeneventserver_conf):
            values[config_name] = config_value
        zep = getFacade('zep')
        zep.setConfigValues(values)

moveZepConfig()
