##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
Add zenossdbpack command if it is missing
"""
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm

sm.require("1.0.0")


class AddZenossdbpackCmd(Migrate.Step):

    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Update the zope service commands.
        changed = False
        zopes = filter(lambda s: s.name == "Zope", ctx.services)
        log.info("Found %i services named 'Zope'." % len(zopes))
        if len(zopes) == 1:
            temp = commandListDict(zopes[0].commands)
            if not temp.has_key('zenossdbpack'):
                temp.update(zenossdbpackCommand)
                changed = True
            zopes[0].commands = commandDictList(temp)
            log.info("Updated Zope command list.")
        # Commit our changes.
        if changed:
            ctx.commit()


AddZenossdbpackCmd()

zenossdbpackCommand = {
    'zenossdbpack': {'Command': '${ZENHOME:-/opt/zenoss}/bin/zenrun zenossdbpack',
    'CommitOnSuccess': False,
    'Description': 'Run ZODB storage packing tool'}
}

def commandListDict(commandList):
    commandDict = {}
    for command in commandList:
        commandDict[command.name] = {
            "Command": command.command,
            "CommitOnSuccess": command.commitOnSuccess,
            "Description": command.description
        }
    return commandDict


def commandDictList(commandDict):
    commandList = []
    for k, v in commandDict.iteritems():
        commandList.append(sm.Command(k, command=v["Command"],
                                      commitOnSuccess=v["CommitOnSuccess"],
                                      description=v["Description"]))
    return commandList

