##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
log = logging.getLogger("zen.Events")

from AccessControl.class_init import InitializeClass
from App.special_dtml import DTMLFile
from AccessControl import ClassSecurityInfo

from EventManagerBase import EventManagerBase
from MySqlSendEvent import MySqlSendEventMixin

def manage_addMySqlEventManager(context, id=None, evthost="localhost",
                                evtuser="root", evtpass="", evtdb="events",
                                evtport=3306,
                                history=False, REQUEST=None):
    '''make an MySqlEventManager'''
    if not id:
        id = "ZenEventManager"
        if history: id = "ZenEventHistory"
    evtmgr = MySqlEventManager(id, hostname=evthost, username=evtuser,
                               password=evtpass, database=evtdb,
                               port=evtport)
    context._setObject(id, evtmgr)
    evtmgr = context._getOb(id)
    evtmgr.buildRelations()
    if history:
        evtmgr.defaultOrderby="%s desc" % evtmgr.lastTimeField
        evtmgr.timeout = 300
        evtmgr.statusTable = "history"
    evtmgr.installIntoPortal()
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()+'/manage_main')


class MySqlEventManager(MySqlSendEventMixin, EventManagerBase):

    portal_type = meta_type = 'MySqlEventManager'

    backend = "mysql"

    security = ClassSecurityInfo()

InitializeClass(MySqlEventManager)
