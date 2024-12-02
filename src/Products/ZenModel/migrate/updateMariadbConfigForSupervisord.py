##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import servicemigration as sm
import Migrate

from string import Template


log = logging.getLogger("zen.migrate")
sm.require("1.1.11")


_svc_dbname_map = {
    "mariadb-model": "zodb",
    "mariadb-events": "zep",
}


class UpdateMariadbConfigForSupervisord(Migrate.Step):
    """Allow supervisord to manage mariadb completely."""

    version = Migrate.Version(200, 5, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Load supervisord configuration template
        supervisord_template = loadTemplate()
        updateSupervisordConf = SupervisordConfigUpdater(supervisord_template)

        mariadbs = [
            s for s in ctx.services
            if s.name in _svc_dbname_map.keys()
        ]
        for svc in mariadbs:
            # Remove the PIDFile from the service definition
            svc.pidFile = None

            configFiles = getConfigFiles(svc.configFiles)

            updateSupervisordConf(
                configFiles["mariadb_supervisor.conf"],
                _svc_dbname_map[svc.name], svc.name,
            )
            updateMariadbConf(configFiles["my.cnf"])

            originalConfigs = getConfigFiles(svc.originalConfigs)
            updateSupervisordConf(
                originalConfigs["mariadb_supervisor.conf"],
                _svc_dbname_map[svc.name], svc.name,
            )
            updateMariadbConf(originalConfigs["my.cnf"])

        if len(mariadbs):
            ctx.commit()


def getConfigFiles(configs):
    return {
        c.name.split('/')[-1]: c
        for c in configs
        if c.name.endswith("my.cnf")
        or c.name.endswith("supervisor.conf")
    }


def loadTemplate():
    basepath = __file__.split("/")[:-1]
    path = "/".join(basepath + ["data", "mariadb_supervisord_conf.template"])
    with open(path, "r") as f:
        return Template(''.join(f.readlines()))


class SupervisordConfigUpdater(object):

    def __init__(self, template):
        self.__template = template

    def __call__(self, conf, dbname, servicename):
        conf.content = self.__template.substitute(
            DB_NAME=dbname, SERVICE_NAME=servicename,
        )


def updateMariadbConf(conf):
    conf.content = conf.content.replace(
        "log_error=/var/log", "log_error = /var/log",
    )


UpdateMariadbConfigForSupervisord()
