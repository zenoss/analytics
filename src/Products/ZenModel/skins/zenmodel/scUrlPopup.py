##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


## Script (Python) "sortedTableNavigation"
##parameters=tableName,selectname,sessionname,contents,url=None
##bind context=context
##title=build a popup from an array of tuples in the form (name, value)

sesskey = sessionname.split(':')[0]
currentvalue = context.ZenTableManager.getTableState(tableName, sesskey)
select = "<select class='tableheader' name='%s'\n" % (
                                            selectname)
select +=" onchange='document.location.href=this[this.selectedIndex].value'"
select += ">\n"
if not url: url = context.absolute_url_path()
for selname, selval in contents:
    select += "<option value='%s?tableName=%s&%s=%d'" % (
                url, tableName, sessionname, selval)
    if currentvalue == selval:
        select += " selected"
    select += ">%s</options>\n" % selname
select += "</select>"
return select
