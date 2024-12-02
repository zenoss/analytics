##############################################################################
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenUtils.GlobalConfig import globalConfToDict
from ZODB.transact import transact

@transact
def setPassword(event):
    """
    Handler for IZopeApplicationOpenedEvent which sets zauth-user password based
      on the settings in global.conf.
    """
    zport = getattr(event.app, 'zport', None)
    # zport may not exist if we are using zenbuild to initialize the database
    if not zport:
        return

    globalConf = globalConfToDict()
    user = globalConf.get('zauth-username', 'zenoss_system')
    password = globalConf.get('zauth-password', "MY_PASSWORD")

    try:
        zport.acl_users.userManager.getUserInfo(user)
    except KeyError:
        zport.dmd.ZenUsers.manage_addUser(user, password=password, roles=('Manager',))
        return

    if not zport.acl_users.userManager.authenticateCredentials({'login':user, 'password':password} ):
        zport.acl_users.userManager.updateUserPassword(user, password)

