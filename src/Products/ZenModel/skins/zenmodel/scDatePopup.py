##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


## Script (Python) "datePopup"
##parameters=tagname, currentValue
##bind context=context
##title=Generate a date popup selection box

import DateTime
if not currentValue:
    currentValue=DateTime.DateTime()

months   = ('','Jan','Feb','Mar','Apr','May','Jun','Jul',
                'Aug','Sep','Oct','Nov','Dec')

if hasattr(context, 'previousYearRange'):
    previousYearRange = context.previousYearRange
else:
    previousYearRange = 2

if hasattr(context, 'futureYearRange'):
    futureYearRange = context.futureYearRange
else:
    futureYearRange = 2

value_yr = currentValue.year()
value_mo = currentValue.month()
value_dd = currentValue.day()

retdata   = ''

# Month
retdata = retdata + "<select name=\"%s_mo:int\">\n" % tagname
for month in range(1,13):
    if (month==value_mo):
        retdata = (retdata + 
                "  <option value=\"%d\" selected>%s</option>\n" 
                % (month, months[month]))
    else:
        retdata = (retdata + 
                "  <option value=\"%d\">%s</option>\n" 
                %  (month, months[month]))
retdata = retdata + "</select> \n\n"

# Day
retdata = retdata + "<select name=\"%s_dd:int\">\n" % tagname
for day in range(1,32):
    if (day==value_dd):
        retdata = (retdata + 
                "  <option value=\"%d\" selected>%d</option>\n" 
                % (day, day))
    else:
        retdata = (retdata + 
            "  <option value=\"%d\">%d</option>\n" % (day, day))
retdata = retdata + "</select>, \n\n"

# Year
retdata = retdata + "<select name=\"%s_yr:int\">\n" % tagname
for year in range(value_yr-previousYearRange, 
                    value_yr+futureYearRange):
    if (year==value_yr):
        retdata = (retdata + 
                "  <option value=\"%d\" selected>%d</option>\n" 
                % (year, year))
    else:
        retdata = (retdata + 
            "  <option value=\"%d\">%d</option>\n" % (year, year))
retdata = retdata + "</select>\n"
return retdata
