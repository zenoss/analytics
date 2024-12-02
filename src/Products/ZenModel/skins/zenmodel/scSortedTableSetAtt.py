##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


## Script (Python) "scSortedTableSetAtt"
##parameters=tableName,attrib,value=None
##bind context=context
##title=Return a value from a tables current session informtion

request=context.REQUEST
session=request.SESSION
if session.has_key(tableName):
    sortedTableState = session[tableName]
else:
    sortedTableState = {
        'sortedSence' : 'asc',
        'start' : 0,
        'url' : request.URL,
        'sortedHeader' : 'primarySortKey',
        'sortRule' : 'cmp',
        'batchSize' : 20,
        }

if not sortedTableState.has_key(attrib):
    sortedTableState[attrib] = value
if request.has_key(attrib):
    sortedTableState[attrib] = request[attrib]
session[tableName] = sortedTableState

return sortedTableState[attrib]
