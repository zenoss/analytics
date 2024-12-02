##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import re
import Migrate
import servicemigration as sm
from servicemigration import HealthCheck
sm.require("1.0.0")


class UpdateMetricsHealthChecks(Migrate.Step):
    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # find the target services
        zope_svc = None
        zenhub_svc = None
        zenpy_svc = None
        for s in ctx.services:
            if s.name.lower() == "zope":
                zope_svc = s
            if s.name.lower() == "zenhub":
                zenhub_svc = s
            if s.name.lower() == "zenpython":
                zenpy_svc = s

        # remove intended zproxy_answering or previously added HC
        svcs = [s for s in [zope_svc, zenhub_svc, zenpy_svc] if s is not None]
        for svc in svcs:
            log.info("Processing service:%s.", svc.name)
            for hc in filter(lambda hc:
                             hc.name == "zproxy_answering" or
                             hc.name == "central_query_answering" or
                             hc.name == "metric_consumer_answering",
                             svc.healthChecks):
                svc.healthChecks.remove(hc)
                log.info("Removed healthcheck:%s from service:%s.", hc.name, svc.name)

        # add intended health checks
        query_hc = HealthCheck(name="central_query_answering",
                               interval=10.0,
                               script="/opt/zenoss/bin/healthchecks/query_answering")
        metrics_hc = HealthCheck(name="metric_consumer_answering",
                                 interval=10.0,
                                 script="/opt/zenoss/bin/healthchecks/metrics_answering")

        # adding hc to zenpython
        zenpy_svc.healthChecks.append(query_hc)
        log.info("Updated 'central_query_answering' healthcheck for zenpython.")

        # adding hc to query zenhub
        zenhub_svc.healthChecks.append(query_hc)
        log.info("Updated 'Central_query_answering' healthcheck for zenhub.")
        zenhub_svc.healthChecks.append(metrics_hc)
        log.info("Updated 'metric_consumer_answering' healthcheck for zenhub.")

        # now fix the original nginx config files on disk
        top_svc = ctx.getTopService()

        if top_svc.name.find("Zenoss") == 0 or top_svc.name.find("UCS-PM") == 0:
            # assuming the original files are all correct
            cfs = filter(lambda f: f.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf", top_svc.originalConfigs)
            for cf in cfs:
                # fix dos mode to linux
                cf.content = cf.content.replace('\r\n', '\n')

                # skip if the file already contains the new entry
                if cf.content.find('location ^~ /ping/') > 0:
                    log.info("original zproxy-nginx.conf already contains 'ping' resource")
                    continue

                # else insert the new entry behind the markered section
                marker = re.compile(r"(\s*location\s+/\s+{.+?})", re.DOTALL)
                if not marker.search(cf.content):
                    continue

                cf.content = marker.sub(
                    r"""\1

        # inserted by 5.2.0 migration script
        location ^~ /ping/ {
            include zenoss-zapp-ping-nginx.cfg;
            proxy_no_cache 1;
            proxy_cache_bypass 1;
            proxy_set_header Host $myhost;
            proxy_method HEAD;
        }
        #""", cf.content, 1)
                log.info("updated zproxy-nginx.conf")

        ctx.commit()

UpdateMetricsHealthChecks()
