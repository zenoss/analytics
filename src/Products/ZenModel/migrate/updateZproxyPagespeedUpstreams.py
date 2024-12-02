##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import re

log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")

new_content = """
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

worker_processes 2;
error_log /opt/zenoss/zproxy/logs/error.log error;
daemon off;

user zenoss;

events {
    worker_connections 1024;
}

http {

    access_log off;
    error_log /opt/zenoss/zproxy/logs/error.log error;

    lua_package_path "./lib/lua/5.1/?.lua;;";
    lua_package_cpath "./lib/?.so;./lib/lua/5.1/?.so;;";
    # Backend servers that did not respond
    lua_shared_dict deads 10m;

    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Port $server_port;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Protocol $scheme;
    proxy_set_header X-Real-IP $remote_addr;

    # Force cookies to HTTPOnly
    proxy_cookie_path / "/; HttpOnly";

    proxy_read_timeout 600;
    proxy_connect_timeout 10;

    proxy_temp_path /opt/zenoss/var/zproxy/proxy_temp;
    client_body_temp_path /opt/zenoss/var/zproxy/client_body_temp;

    gzip on;
    gzip_comp_level 9;
    gzip_proxied any;
    gzip_min_length 1000;
    gzip_buffers 4 32k;
    gzip_types text/css text/plain application/atom+xml application/x-javascript application/javascript text/javascript;
    gzip_disable msie6;
    gzip_vary on;

    resolver 8.8.8.8;

    # this is needed to send the correct content type for things like css
    include mime.types;

    upstream zopes {
        least_conn;
        include zope-upstreams.conf;
        keepalive 64;
    }

    pagespeed ListOutstandingUrlsOnError on;
    pagespeed RewriteDeadlinePerFlushMs 100;
    pagespeed RateLimitBackgroundFetches off;
    pagespeed FileCachePath /opt/zenoss/var/zproxy/ngx_pagespeed_cache;
    pagespeed ImageMaxRewritesAtOnce -1;

    server {

        listen 8080;
        set $myhost $http_host;

        pagespeed off;
        pagespeed RewriteLevel CoreFilters;
        pagespeed EnableFilters add_instrumentation,move_css_above_scripts,move_css_to_head,rewrite_style_attributes,in_place_optimize_for_browser,dedup_inlined_images,prioritize_critical_css;
        pagespeed RespectXForwardedProto on;
        pagespeed AvoidRenamingIntrospectiveJavascript off;
        pagespeed MaxCombinedJsBytes -1;
        pagespeed JsInlineMaxBytes 102400;
        pagespeed StatisticsPath "/ngx_pagespeed_statistics";
        pagespeed Disallow "*/api/metrics*";
        pagespeed Disallow "*/api/performance*";
        pagespeed Disallow "*/ws/metrics*";
        pagespeed Disallow "*/ping/status*";
        pagespeed Disallow "*/static/*";

        # Ensure requests for pagespeed optimized resources go to the pagespeed handler
        # and no extraneous headers get set.
        location ~ "\.pagespeed\.([a-z]\.)?[a-z]{2}\.[^.]{10}\.[^.]+" {
         add_header "" "";
        }
        location ~ "^/pagespeed_static/" { }
        location ~ "^/ngx_pagespeed_beacon$" { }
        location ~ "^/ngx_pagespeed_statistics" {}

        include zope-static.conf;

        location / {
            proxy_pass http://zopes;
            proxy_set_header Host $myhost;
            proxy_http_version 1.1;
            add_header X-Frame-Options SAMEORIGIN;
            add_header X-XSS-Protection "1; mode=block";
        }

        location ^~ /ping/ {
            include zenoss-zapp-ping-nginx.cfg;
            proxy_no_cache 1;
            proxy_cache_bypass 1;
            proxy_set_header Host $myhost;
            proxy_method HEAD;
        }

        location ^~ /api/controlplane/kibana {
            set $http_ws true;
            proxy_pass http://127.0.0.1:5601;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            rewrite /api/controlplane/kibana$ / break;
            rewrite /api/controlplane/kibana/(.*)$ /$1 break;
        }

        # Legacy apps that don't do any auth validation
        # Should 'include zenoss-legacy-nginx.cfg;'

        # /api is for zapp rest APIs
        location ^~ /api/ {
            # Zapps do their own auth validation
            include zenoss-zapp-nginx.cfg;
            proxy_set_header Host $myhost;
        }

        # /ws is for zapp websockets
        location ^~ /ws/ {
            set $http_ws true;
            # Zapps do their own auth validation
            include zenoss-zapp-nginx.cfg;
            proxy_set_header Host $myhost;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # /static is for static files
        location ^~ /static/ {
            # Static data should always be allowed
            include zenoss-authenticated-nginx.cfg;
            proxy_http_version 1.1;
        }

        # /zauth is for authentication and authorization
        location ^~ /zauth/ {
            # ZAuth requests should always be allowed
            include zenoss-authenticated-nginx.cfg;
            proxy_set_header Host $myhost;
            proxy_http_version 1.1;
            proxy_set_header  Accept-Encoding  "";
        }

    }
}
""".strip()


class UpdateZproxyPagespeedUpstreams(Migrate.Step):

    version = Migrate.Version(108, 0, 0)

    config_file = "/opt/zenoss/zproxy/conf/zproxy-nginx.conf"
    save_file = "/opt/zenoss/var/ext/zproxy-nginx.conf.orig"

    def update_zope_imports(self, zproxy):
        for endpoint in zproxy.endpoints:
            if endpoint.application == "zope":
                if endpoint.purpose == "import":
                    endpoint.purpose = "import_all"
                    return True
                return False

    def update_config(self, zproxy):
        commit, wrote = False, False
        current_config, orig_config = None, None

        for cfg in zproxy.configFiles:
            if cfg.filename == self.config_file:
                current_config = cfg
                break

        for cfg in zproxy.originalConfigs:
            if cfg.filename == self.config_file:
                orig_config = cfg
                break

        if orig_config and orig_config.content != new_content:
            orig_config.content = new_content
            commit = True

        if current_config and current_config.content != new_content:
            with open(self.save_file, 'w+') as f:
                f.write(current_config.content)
            current_config.content = new_content
            commit = True
            wrote = True

        return commit, wrote


    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zproxy = ctx.getTopService()

        commit, wrote = self.update_config(zproxy)
        commit = self.update_zope_imports(zproxy) or commit

        try:
            if commit:
                log.info("Updated zproxy configuration to the latest version.")
                ctx.commit()
        finally:
            if wrote:
                log.info(("A copy of your existing configuration has been saved to %s."
                        " If you had made changes to zproxy-nginx.conf in the Control Center UI, "
                        "please reapply them manually, then restart the service.") % self.save_file)


UpdateZproxyPagespeedUpstreams()
