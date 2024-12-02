## Script (Python) "getSortedTableState"
##parameters=tableName,key
##bind context=context
##title=Return a value from a tables current session informtion
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


request=context.REQUEST
session=request.SESSION
if session.has_key(tableName):
    sortedTableState = session[tableName]
    if sortedTableState.has_key(key):
        return sortedTableState[key]
