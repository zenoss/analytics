##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


#
# Contained below are items used in selenium testing that don't fit elsewhere.
#
# Adam Modlin and Nate Avers
#

def getByValue (listName, value, formName="subdeviceForm"):
    """Handles checkbox selections"""
    return "dom=function fun (){var ha = document.forms.%s.elements['%s']; if (!ha.length)  ha=Array(ha); for (i = 0; i < ha.length; i++) {if (ha[i].value=='%s') return ha[i];}}; fun ()" %(formName, listName, value) 

class TimeoutError(Exception):
    """This will be thrown when an element is not found
        on a page and times out."""
    pass

def do_command_byname(selenium, command, name):
    """Runs specified command on all elements with the given name"""
    _flag = True
    i = 0
    while _flag:
       locator = "name=%s index=%s" % (name, i)
       try:
           selenium.do_command(command, [locator,])
           i += 1
       except Exception as data:
           if "ndex out of range" in data[0]: _flag = False
           else: raise Exception(data)
