##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


## Script (Python) "scSortedTableHref"
##parameters=tableName,fieldName,sortRule='cmp',params=None
##bind context=context
##title=Make a tag for a table header that allows sorting

request = context.REQUEST
session = request.SESSION

if session.has_key(tableName):
    sortedTableState = session[tableName]
    sortedHeader = sortedTableState['sortedHeader']
    sortedSence = sortedTableState['sortedSence']
    if sortedHeader == fieldName:
        if sortedSence == 'asc':
            sortedSence = 'desc'
        elif sortedSence == 'desc':
            fieldName = ''
            sortedSence = ''
    else:
        sortedSence = 'asc'

    tag = ("%s?tableName=%s&sortedHeader=%s&sortedSence=%s&sortRule=%s%s" 
            % (request.URL,tableName, fieldName, sortedSence, sortRule,params))
    return tag
else:
    raise "SortedTableSessionError", \
            "Can't find %s tableinfo in session" % tableName
