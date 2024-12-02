##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
Update all Runs to new 5.1 Commands
"""
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class ConvertRunsToCommands(Migrate.Step):

    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Update the zope service commands.
        zopes = filter(lambda s: s.name == "Zope", ctx.services)
        log.info("Found %i services named 'Zope'." % len(zopes))
        if len(zopes) == 1:
            temp = commandListDict(zopes[0].commands)
            temp.update(zopeCommands)
            zopes[0].commands = commandDictList(temp)
            log.info("Updated Zope command list.")
        mariadbModels = filter(lambda s: s.name == "mariadb-model", ctx.services)
        log.info("Found %i services named 'mariadb-model'." % len(mariadbModels))
        if len(mariadbModels) == 1:
            temp = commandListDict(mariadbModels[0].commands)
            temp.update(mariadbModelCommands)
            mariadbModels[0].commands = commandDictList(temp)
            log.info("Updated mariadb-model command list.")
        mariadbs = filter(lambda s: s.name == "mariadb", ctx.services)
        log.info("Found %i services named 'mariadb'." % len(mariadbs))
        if len(mariadbs) == 1:
            temp = commandListDict(mariadbs[0].commands)
            temp.update(mariadbCommands)
            mariadbs[0].commands = commandDictList(temp)
            log.info("Updated mariadb command list.")
        # Commit our changes.
        ctx.commit()


ConvertRunsToCommands()


def commandListDict(commandList):
    commandDict = {}
    for command in commandList:
        commandDict[command.name] = {
            "Command": command.command,
            "CommitOnSuccess": command.commitOnSuccess
        }
    return commandDict


def commandDictList(commandDict):
    commandList = []
    for k, v in commandDict.iteritems():
        commandList.append(sm.Command(k, command=v["Command"],
                                      commitOnSuccess=v["CommitOnSuccess"]))
    return commandList


zopeCommands = {
    "zendmd": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun zendmd",
        "CommitOnSuccess": False
    },
    "upgrade": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun upgrade.sh doUpgrade",
        "CommitOnSuccess": False
    },
    "apply-custom-patches": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun patch.sh applyPatches",
        "CommitOnSuccess": True
    },
    "reportmail": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun reportmail.sh",
        "CommitOnSuccess": False
    },
    "help": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun help.sh",
        "CommitOnSuccess": False
    },
    "zenpack-manager": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun zenpack-manager.sh --service-id={{.ID}}",
        "CommitOnSuccess": True
    },
    "zenpack": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun zenpack.sh --service-id={{.ID}}",
        "CommitOnSuccess": False
    },
    "install-percona": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun percona.sh install",
        "CommitOnSuccess": True
    },
    "zenmib": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun zenmib.sh",
        "CommitOnSuccess": True
    }
}


mariadbCommands = {
    "rebuild_zodb_session": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun mysql.sh rebuild_zodb_session",
        "CommitOnSuccess": False
    }
}


mariadbModelCommands = {
    "rebuild_zodb_session": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun mysql.sh rebuild_zodb_session",
        "CommitOnSuccess": False
    }
}
