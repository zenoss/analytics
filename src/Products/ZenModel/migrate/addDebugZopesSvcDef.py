##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """AddDebugZopesSvcDef
Adds the service zendebug that provides Zope instances dedicated to serving non-UI JSON API requests.
"""
import logging
log = logging.getLogger("zen.migrate")

import os
import re
import copy
import Migrate
import servicemigration as sm
import subprocess
import shutil


sm.require("1.1.9")

def create_upstream_pattern(upstream_name, server_decl):
    return re.compile("\\n\s+upstream %s {\\n\s+least_conn;\\n\s+%s;\\n\s+keepalive 64;\\n\s+}(?:(?:\\r)?\\n)" % (upstream_name, server_decl))

incl_mimetypes_pat = re.compile(r'include mime\.types;(?:(?:\\r)?\\n)?')
zope_upstream_pat = create_upstream_pattern('zopes', 'include zope-upstreams\.conf')
zopereports_upstream_pat = create_upstream_pattern('zopereports', 'include zopereports-upstreams\.conf')
debugzope_upstream_pat = create_upstream_pattern('debugzopes', 'server 127\.0\.0\.1:9310')
map_whichzopes_pat = re.compile(r'\\n\s+map \$host \$whichzopes {\\n\s+default zopes;\\n\s+~\*zendebug debugzopes;\\n\s+}\\n(?:(?:\\r)?\\n)')

zendebug_upstreams_decl = '\n\n    upstream debugzopes {\n        least_conn;\n        server 127.0.0.1:9310;\n        keepalive 64;\n    }\n'
debugzope_map_clause = '\n        ~*zendebug debugzopes;'
zendebug_map_whichzopes_block_decl = '\n    map $host $whichzopes {\n        default zopes;\n        ~*zendebug debugzopes;\n    }\n'

def find_insertion_point(conf, patterns):
    insertion_point = 0
    if len(patterns) < 1:
        return insertion_point
    for pat in patterns:
        search_result = pat.search(conf)
        if search_result is not None:
            insertion_point = max(insertion_point, search_result.end())
    return insertion_point

def insert_debugzopes_upstreams(conf):
    if debugzope_upstream_pat.search(conf) is not None:
        return conf
    insertion_point = find_insertion_point(conf, [incl_mimetypes_pat, zope_upstream_pat, zopereports_upstream_pat])
    if insertion_point > 0:
        return conf[:insertion_point] + zendebug_upstreams_decl + conf[insertion_point:]
    else:
        return conf

def insert_map_whichzopes_block(conf):
    map_block_begin_pat = re.compile('map \$host \$whichzopes {(?:\\n\s+(?:~|\*)*\w+\s+\w+;)+', re.S)
    if map_whichzopes_pat.search(conf) is not None:
        return conf
    else:
        r1 = map_block_begin_pat.search(conf)
        if r1 is not None:
            insertion_point = r1.end()
            return conf[:insertion_point] + debugzope_map_clause + conf[insertion_point:]
        else:
            insertion_point = find_insertion_point(conf, [incl_mimetypes_pat, zope_upstream_pat, zopereports_upstream_pat, debugzope_upstream_pat])
            return conf[:insertion_point] + zendebug_map_whichzopes_block_decl + conf[insertion_point:]

class AddDebugZopesSvcDef(Migrate.Step):
    """Adds a svcdef for a dedicated debug Zope instance."""
    version = Migrate.Version(114,0,0)

    def __init__(self):
        Migrate.Step.__init__(self)
        self.zendebug_proxy_incl = '        location / {\n            proxy_pass http://$whichzopes;'

    def _add_zendebug_service(self, ctx):
        zendebug_svc = filter(lambda x: x.name == "zendebug", ctx.services)
        if zendebug_svc and len(zendebug_svc) > 0:
            log.info("The zendebug service already exists. Skipping this migration step.")
            return False

        # Copy zendebug service definition
        zendebug_svc_filepath = os.path.join(os.path.dirname(__file__), "data", "zendebug-service.json")
        zendebug_svc_tempfilepath = '/tmp/zendebug-service.json'
        shutil.copyfile(zendebug_svc_filepath, zendebug_svc_tempfilepath)

        # Substitute the ImageID
        zope_svc = filter(lambda x: x.name == "Zope", ctx.services)[0]
        subprocess.check_call(['sed', '-i', 's#"ImageID": "[a-zA-Z0-9:\/]\+",#"ImageID": "{}",#'.format(zope_svc.imageID), zendebug_svc_tempfilepath])

        with open(zendebug_svc_tempfilepath) as zendebug_jsonfile:
            try:
                user_interface_svc = filter(lambda x: x.name == "User Interface", ctx.services)[0]
                ctx.deployService(zendebug_jsonfile.read(), user_interface_svc)
            except Exception:
                log.error("Error deploying zendebug service definition")
                return False

        return True

    def insertProxyDecl(self, matchObj):
        return self.zendebug_proxy_incl

    def _insert_zendebug_nginx_incls(self, zproxy_conf):
        conf_with_upstreams = insert_debugzopes_upstreams(zproxy_conf.content)
        conf_with_map_block = insert_map_whichzopes_block(conf_with_upstreams)
        conf_with_new_location_block = re.sub(r'        location / {\n            proxy_pass http://zopes;', self.insertProxyDecl, conf_with_map_block)
        if conf_with_new_location_block == zproxy_conf.content:
            return False
        else:
            zproxy_conf.content = conf_with_new_location_block
            return True

    def update_zproxy_configs(self, zproxy):

        # Modify zproxy configs for zendebug
        zproxy_conf_orig = filter(lambda x: x.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf", zproxy.originalConfigs)[0]
        zproxy_conf = filter(lambda x: x.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf", zproxy.configFiles)[0]

        # Add endpoint for new zendebug service
        zendebug_endpoint = filter(lambda x: x.name == "zendebug", zproxy.endpoints)
        if not zendebug_endpoint:
            zope_ep = filter(lambda x: x.name == "zope", zproxy.endpoints)[0]
            zendebug_ep = copy.deepcopy(zope_ep)
            zendebug_ep.name = "zendebug"
            zendebug_ep.application = "zendebug"
            zendebug_ep.applicationtemplate = "zendebug"
            zendebug_ep.portnumber = 9310
            zendebug_ep.purpose = "import_all"
            zproxy.endpoints.append(zendebug_ep)

        zproxy_endpoint = filter(lambda x: x.name == "zproxy", zproxy.endpoints)[0]
        zproxy_endpoint.vhostlist.append(sm.vhost.VHost(name="zendebug", enabled=False))
        return self._insert_zendebug_nginx_incls(zproxy_conf_orig) and self._insert_zendebug_nginx_incls(zproxy_conf)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.error("Couldn't generate context, skipping.")
            return

        did_add_zendebug = self._add_zendebug_service(ctx)
        if not did_add_zendebug:
           return

        zproxy = ctx.getTopService()
        did_update_zproxy = self.update_zproxy_configs(zproxy)

        if not did_update_zproxy:
            log.error("Unable to add zendebug and update zproxy configuration")
            return

        ctx.commit()

AddDebugZopesSvcDef()
