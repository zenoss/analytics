##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016-2017, all rights reserved.
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
sm.require("1.0.0")


class UpdateNginxKibanaRule(Migrate.Step):
    """
    Update zproxy nginx config to enable auth for kiban URLs
    """

    version = Migrate.Version(113, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zproxy = ctx.getTopService()

        if migrateConf(zproxy):
            ctx.commit()

def migrateConf(zproxy):
    commit = False
    configs = filter(lambda f: f.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf", zproxy.originalConfigs + zproxy.configFiles )
    for config in configs:
        if not kibanaAuthAlreadySet(config.content):
            #add the auth check to kibana location
            lines = config.content.split('\n')
            newContent = []
            inKibanaRule = False;
            for line in lines:
                newContent.append(line)
                stripped = line.strip()
                if line.strip().startswith('location ^~ /api/controlplane/kibana'):
                    inKibanaRule = True;
                elif inKibanaRule and stripped == 'set $http_ws true;':
                    newContent.append("            access_by_lua_file 'conf/zenoss-require-auth.lua';")
                    inKibanaRule = False
            if len(newContent) != len(lines):
                #we added something
                commit = True;
                config.content = '\n'.join(newContent)

    return commit



def kibanaAuthAlreadySet(configContent):
    #try to find auth line even if white space modified
    pattern = "^access_by_lua_file\s+[']conf/zenoss-require-auth\.lua['][\s]*\;"
    lines = configContent.split('\n')
    inKibanaRule = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('location ^~ /api/controlplane/kibana'):
            inKibanaRule = True
        elif inKibanaRule and stripped == '}':
            #End of kibana rule and pattern not found
            return False
        elif inKibanaRule and re.search(pattern, stripped):
            return True

    return False

UpdateNginxKibanaRule()

