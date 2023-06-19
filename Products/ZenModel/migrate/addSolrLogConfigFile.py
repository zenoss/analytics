##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import Migrate
import os
import servicemigration as sm
from Products.ZenUtils.path import zenPath

log = logging.getLogger("zen.migrate")
sm.require("1.1.5")

class addSolrLogConfigFile(Migrate.Step):
    """
    Add audit log level config to service definition.
    """
    version = Migrate.Version(200, 3, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        solrs = filter(lambda s: s.name == "Solr", ctx.services)
        log.info("Found {0} services with 'Solr' in their service path".format(len(solrs)))
        commit = False

        filename = 'Products/ZenModel/migrate/data/log4j.properties'
        with open(zenPath(filename)) as configFile:
            try:
                configCnt = configFile.read()
            except Exception as e:
                log.error("Error reading {0} logfilter file: {1}".format(filename, e))
                return
            logLvlCfg = sm.ConfigFile(
                name = "/var/solr/log4j.properties",
                filename = "/var/solr/log4j.properties",
                owner = "root:root",
                permissions = "0664",
                content = configCnt
            )
        for solr in solrs:
            #if there is a log level config do not overwrite it
            if logLvlCfg.name not in [cf.name for cf in solr.originalConfigs]:
                solr.originalConfigs.append(logLvlCfg)
                commit = True
                log.info("Adding log level config to Zope originalConfigs")
            if logLvlCfg.name not in [cf.name for cf in solr.configFiles]:
                solr.configFiles.append(logLvlCfg)
                commit = True
                log.info("Adding log level config to Zope configFiles")
        if commit:
            ctx.commit()

addSolrLogConfigFile()

