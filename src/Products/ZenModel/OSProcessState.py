##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

def determineProcessState(beforeProcessSetPIDs, afterProcessSetPIDs):
    deadPids = set()
    restartedPids = set()
    newPids = set()

    # if beforeProcessSetPIDs is empty, do nothing (beforeProcessSetPIDs is empty on the first run)
    if not beforeProcessSetPIDs:
        return (deadPids, restartedPids, newPids)

    beforeProcessSets = set(beforeProcessSetPIDs.keys())
    afterProcessSets = set(afterProcessSetPIDs.keys())

    beforeOnlyProcessSets = beforeProcessSets - afterProcessSets
    afterOnlyProcessSets = afterProcessSets - beforeProcessSets

    beforeAndAfterProcessSets = beforeProcessSets.intersection(afterProcessSets)

    for processSet in beforeOnlyProcessSets:
        deadPids.update(beforeProcessSetPIDs[processSet])

    for processSet in afterOnlyProcessSets:
        newPids.update(afterProcessSetPIDs[processSet])

    for processSet in beforeAndAfterProcessSets:
        beforePids = set(beforeProcessSetPIDs[processSet])
        afterPids = set(afterProcessSetPIDs[processSet])

        oldUniquePids = beforePids - afterPids
        newUniquePids = afterPids - beforePids

        if len(afterPids) <= len(beforePids):
            oldUniquePidsList = list(oldUniquePids)

            # the difference of beforePids and afterPids is the number of deadPids
            numDead = len(beforePids) - len(afterPids)
            deadPids.update(oldUniquePidsList[0:numDead])
            
            # all of the new unique pids are categorized as restarts
            restartedPids.update(newUniquePids)

        elif len(afterPids) > len(beforePids):
            newUniquePidsList = list(newUniquePids)

            # the difference of afterPids and beforePids is the number of newPids
            numNew = len(afterPids) - len(beforePids)
            newPids.update(newUniquePidsList[0:numNew])

             # the remaining unique new pids are categorized as restarts
            restartedPids.update(newUniquePidsList[numNew:])

    return (deadPids, restartedPids, newPids)
