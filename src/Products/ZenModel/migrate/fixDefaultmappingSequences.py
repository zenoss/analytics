##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
This migration script fixes a specific conflict in the base database between sequence numbers for the defaultmapping EventClass instance.
''' 

__version__ = "$Revision$"[11:-2]

import logging
log = logging.getLogger("zen.migrate")
import Migrate


# Checks a list of items sorted by sequence for duplicate sequence numbers
def hasSequenceConflict(items):
    if len(items) > 1:
        lastSequence = items[0].sequence
        for item in items[1:]:
            if item.sequence == lastSequence:
                return True
            lastSequence = item.sequence
    return False

# Re-sequences a sorted list of items, returns the number of items changed
def resequence(items):
    changed = 0
    for i, item in enumerate(items):
            if item.sequence != i:
                item.sequence = i
                changed = changed + 1
    return changed

class FixDefaultmappingSequences(Migrate.Step):

    version = Migrate.Version(107,0,0)

    def cutover(self, dmd):
        changed = 0
        log.info("Fixing default EventClass instance sequence conflict")

        # This will give us all EventClassInstances that have eventclasskey "defaultmapping", sorted by sequence:
        defaultmappings = dmd.Events.find('defaultmapping')

        if(hasSequenceConflict(defaultmappings)):
            changed = resequence(defaultmappings)


        log.info("Updated sequence numbers for %d Event class instances" % changed)



FixDefaultmappingSequences()
