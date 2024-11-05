##############################################################################
#
# Copyright (C) Zenoss, Inc. 2022, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
This updates solr configs during the migrations from 7.7.3 to 8.11.1 version.
"""

import logging
import Migrate
import servicemigration as sm
from Products.ZenUtils.path import zenPath

log = logging.getLogger("zen.migrate")

SOLR_IN = '''
SOLR_JAVA_MEM="-Xmx{{.RAMCommitment}} -Xms{{.RAMCommitment}}"
SOLR_OPTS="-Dsolr.http1=true"
'''


class UpdateSolrConfigs(Migrate.Step):
    version = Migrate.Version(300, 1, 0)

    def __read_file_content(self, name):
        with open(zenPath("Products/ZenModel/migrate/data/%s" % name)) as f:
            try:
                content = f.read()
            except Exception as e:
                log.error("Error reading {0} file: {1}".format(name, e))
        return content

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return
        service = filter(lambda s: s.name == "Solr", ctx.services)[0]
        configFiles = service.originalConfigs + service.configFiles

        for (name, cfg_name) in (('log4j2-8.11.1.xml', '/var/solr/log4j2.xml'),
                                 ('zoo-8.11.1.cfg', '/opt/solr/zenoss/bin/zoo.cfg')):
            if len(filter(lambda x: x.name == cfg_name, configFiles)) > 0:
                continue
            content = self.__read_file_content(name)
            cfg_obj = sm.configfile.ConfigFile(name=cfg_name, filename=cfg_name, owner="root:root",
                                               permissions="0664", content=content)
            service.configFiles.append(cfg_obj)
            service.originalConfigs.append(cfg_obj)

        for volume in service.volumes:
            if volume.containerPath == "/opt/solr/server/logs":
                volume.containerPath = '/var/solr/logs'

        logPath = "/var/solr/logs/solr_slow_requests.log"
        if len(filter(lambda x: x.path == logPath, service.logConfigs)) == 0:
            service.logConfigs.append(sm.logconfig.LogConfig(path=logPath, logType='solr'))

        for cfg in filter(lambda x: x.name == "/opt/solr/server/solr/configsets/zenoss_model/conf/solrconfig.xml",
                          configFiles):
            cfg.content = self.__read_file_content('solrconfig-8.11.1.xml')

        for cfg in filter(lambda x: x.name == "/opt/solr/zenoss/etc/solr.in.sh",
                          configFiles):
            cfg.content = SOLR_IN

        ctx.commit()


UpdateSolrConfigs()
