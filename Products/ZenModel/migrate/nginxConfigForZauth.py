import logging
import Migrate
import os
import re

import servicemigration as sm
from Products.ZenUtils.path import zenPath

log = logging.getLogger("zen.migrate")
sm.require("1.0.0")


incl_mimetypes_pat = re.compile(r'include mime\.types;(?:(?:\\r)?\\n)?')
zauth_upstream_pat = re.compile("\\n\s+upstream zauth {\\n\s+least_conn;\\n\s+include zauth-upstreams\.conf;\\n\s+keepalive 64;\\n\s+}(?:(?:\\r)?\\n)")
zauth_upstreams_decl = '\n\n    upstream zauth {\n        least_conn;\n        include zauth-upstreams.conf;\n        keepalive 64;\n    }'
zauth_location_pat = re.compile(r'location .* /zauth/')

def find_insertion_point(conf, patterns):
    insertion_point = 0
    if len(patterns) < 1:
        return insertion_point
    for pat in patterns:
        search_result = pat.search(conf)
        if search_result is not None:
            insertion_point = max(insertion_point, search_result.end())
    return insertion_point

def insert_zauth_upstreams(conf):
    if zauth_upstream_pat.search(conf):
        log.info('Zauth upstream block already exists.')
        return conf
    insertion_point = find_insertion_point(conf, [incl_mimetypes_pat])
    if insertion_point > 0:
        return conf[:insertion_point] + zauth_upstreams_decl + conf[insertion_point:]
    else:
        return conf

def indent_str(string, indent):
    return string.rjust(indent + len(string))

def modify_zauth_location(conf):
    if not zauth_location_pat.search(conf):
        log.info('Zauth location block not found.')
        return conf

    new_conf = []
    lines = conf.split('\n')
    in_zauth_loc = False
    add_rewrite_login = True
    add_rewrite_validate = True

    for line in lines:
        if line.strip().startswith('location ^~ /zauth/ {'):
            in_zauth_loc = True # We are inside zauth location block.
            stack = [] # To figure out the end of the zauth location block
        if in_zauth_loc:
            if '{' in line:
                stack.append('{')

            if '}' in line:
                stack.pop()

            if line.strip().startswith('# ZAuth requests should always be allowed'):
                # Skip this line. Don't need any more.
                continue

            if line.strip().startswith('include zenoss-authenticated-nginx.cfg'):
                indent = len(line) - len(line.lstrip())
                line = indent_str('proxy_pass http://zauth;', indent)

            if line.strip().startswith('rewrite /zauth/api/login /authorization/login break;'):
                add_rewrite_login = False

            if line.strip().startswith('rewrite /zauth/api/validate /authorization/validate break;'):
                add_rewrite_validate = False

            if len(stack) == 0: # End of the zauth location block
                indent = len(line) - len(line.lstrip())

                if add_rewrite_login:
                    string = 'rewrite /zauth/api/login /authorization/login break;'
                    indented = indent_str(string, indent + 4)
                    new_conf.append(indented)

                if add_rewrite_validate:
                    string = 'rewrite /zauth/api/validate /authorization/validate break;'
                    indented = indent_str(string, indent + 4)
                    new_conf.append(indented)

                in_zauth_loc = False

        new_conf.append(line)

    return '\n'.join(new_conf)

def update_zproxy_conf(zproxy_conf):
    conf = insert_zauth_upstreams(zproxy_conf.content)
    conf = modify_zauth_location(conf)

    if conf == zproxy_conf.content:
        return False
    else:
        zproxy_conf.content = conf
        return True

class NginxConfigForZauth(Migrate.Step):
    """
    Nginx configuration change for Zauth (ZEN-28297)
    """
    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context. Skipping.")
            return

        top_service = ctx.getTopService()
        log.info("Found top level service: '{0}'".format(top_service.name))
        if top_service.name in ['Zenoss.core', 'Zenoss.resmgr.lite', 'UCS-PM.lite']:
            log.info("This top service does not need this migration. Skipping.")
            return

        changed = False

        # Change Zauth endpoint to import_all
        try:
            zauth_endpoint = [endpoint for endpoint in top_service.endpoints if endpoint.name == 'zauth'][0]
            if zauth_endpoint.purpose == 'import':
                zauth_endpoint.purpose = 'import_all'
                changed = True
        except IndexError:
            log.warn('Cannot find Zauth endpoint.')

        # Add upstream block and modify location block for zauth in the nginx configuration file
        try:
            zproxy_conf_orig = filter(
                    lambda x: x.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf",
                    top_service.originalConfigs)[0]
            zproxy_conf = filter(
                    lambda x: x.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf",
                    top_service.configFiles)[0]

            orig_conf_changed = update_zproxy_conf(zproxy_conf_orig)
            conf_changed = update_zproxy_conf(zproxy_conf)

            changed = changed or orig_conf_changed or conf_changed
        except IndexError:
            log.warn('Cannot find zproxy nginx configuration file in service definition.')

        if changed:
            ctx.commit()

NginxConfigForZauth()
