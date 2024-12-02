##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """AddReportingZopesSvcDef
Adds service zenreports that provides Zope instances dedicated to generating
resmgr reports.
"""
import logging
log = logging.getLogger("zen.migrate")

import os
import re
import copy
import Migrate
import servicemigration as sm
import servicemigration.thresholdconfig
import servicemigration.threshold
import servicemigration.eventtags
import subprocess
import shutil


sm.require("1.1.8")

class AddReportingZopesSvcDef(Migrate.Step):
    """Adds a svcdef for dedicated reporting Zope"""
    version = Migrate.Version(114,0,0)

    def __init__(self):
        Migrate.Step.__init__(self)
        self.zenreports_upstreams_decl = "\n    upstream zopereports {\n        least_conn;\n        include zopereports-upstreams.conf;\n        keepalive 64;\n    }\n"
        self.zenreports_proxy_incl = "\n        include zopereports-proxy.conf;\n\n"

    def _add_zenreports_service(self, ctx):
        zenreports_svc = filter(lambda x: x.name == "zenreports", ctx.services)
        if zenreports_svc and len(zenreports_svc) > 0:
            zenreports_svc = zenreports_svc[0]
            log.info("The zenreports service already exists. Skipping this migration step.")
            return False

        # Copy zenreports service definition
        zenreports_svc_filepath = os.path.join(os.path.dirname(__file__), "data", "zenreports-service.json")
        zenreports_svc_tempfilepath = '/tmp/zenreports-service.json'
        shutil.copyfile(zenreports_svc_filepath, zenreports_svc_tempfilepath)

        # Substitute the ImageID
        zope_svc = filter(lambda x: x.name == "Zope", ctx.services)[0]
        subprocess.check_call(['sed', '-i', 's#"ImageID": "[a-zA-Z0-9:\/]\+",#"ImageID": "{}",#'.format(zope_svc.imageID), zenreports_svc_tempfilepath])

        with open(zenreports_svc_tempfilepath) as zenreports_jsonfile:
            try:
                user_interface_svc = filter(lambda x: x.name == "User Interface", ctx.services)[0]
                ctx.deployService(zenreports_jsonfile.read(), user_interface_svc)
            except Exception as e:
                log.error("Error deploying zenreports service definition: {}".format(e))
                return False

        return True

    def insertUpstreamDecl(self, matchObj):
        return "{}{}".format(matchObj.group(0), self.zenreports_upstreams_decl)

    def insertProxyDecl(self, matchObj):
        return "{}{}".format(self.zenreports_proxy_incl, matchObj.group(0))

    def _insert_zenreport_nginx_incls(self, zproxy_conf):
        # Insert zenreports upstreams server decl
        if re.search("upstream zopereports", zproxy_conf.content) is not None:
            return False
        if re.search("include zopereports-proxy.conf", zproxy_conf.content) is not None:
            return False
        zproxy_conf_a = re.sub(r'(include mime.types;(?:\r\n|\s+))', self.insertUpstreamDecl, zproxy_conf.content)
        zproxy_conf_b = re.sub('        location / {', self.insertProxyDecl, zproxy_conf_a)
        zproxy_conf.content = zproxy_conf_b
        return True

    def update_zproxy_configs(self, zproxy):

        # Modify zproxy configs for zenreports
        zproxy_conf_orig = filter(lambda x: x.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf", zproxy.originalConfigs)[0]
        zproxy_conf = filter(lambda x: x.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf", zproxy.configFiles)[0]

        # Add endpoint for new zenreports service
        zenreports_endpoint = filter(lambda x: x.name == "zenreports", zproxy.endpoints)
        if not zenreports_endpoint:
            zope_ep = filter(lambda x: x.name == "zope", zproxy.endpoints)[0]
            zenreports_ep = copy.deepcopy(zope_ep)
            zenreports_ep.name = "zenreports"
            zenreports_ep.application = "zenreports"
            zenreports_ep.applicationtemplate = "zenreports"
            zenreports_ep.portnumber = 9290
            zenreports_ep.purpose = "import_all"
            zproxy.endpoints.append(zenreports_ep)

        return self._insert_zenreport_nginx_incls(zproxy_conf_orig) and self._insert_zenreport_nginx_incls(zproxy_conf)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.error("Couldn't generate context, skipping.")
            return

        did_add_zenreports = self._add_zenreports_service(ctx)
        if not did_add_zenreports:
           return

        zproxy = ctx.getTopService()
        did_update_zproxy = self.update_zproxy_configs(zproxy)

        if not did_update_zproxy:
            log.error("Unable to add zenreports and update zproxy configuration")
            return

        ctx.commit()

AddReportingZopesSvcDef()
