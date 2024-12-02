##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


## Script (Python) "scSortedTableHeader"
##parameters=tableName,fieldName,fieldTitle,sortRule='cmp',style='tableheader',attributes=None
##bind context=context
##title=Make a tag for a table header that allows sorting

request = context.REQUEST
session = request.SESSION

if session.has_key(tableName):
    sortedTableState = session[tableName]
    sortedHeader = sortedTableState['sortedHeader']
    sortedSence = sortedTableState['sortedSence']
    if sortedHeader == fieldName:
        style = style + "selected"
        #if not sortedSence:
        #    sortedSence = 'asc'
        if sortedSence == 'asc':
            sortedSence = 'desc'
        elif sortedSence == 'desc':
            fieldName = ''
            sortedSence = ''
    else:
        sortedSence = 'asc'

    tag = """<th class="%s" %s> <a class="%s" href="%s""" % (
                            style,attributes,style,request.URL)
    tag += ("?tableName=%s&sortedHeader=%s&sortedSence=%s&sortRule=%s\">" 
                % (tableName, fieldName, sortedSence, sortRule))
    tag += fieldTitle + "</a></th>\n"
    return tag
else:
    raise "SortedTableSessionError", \
            "Can't find %s tableinfo in session" % tableName
