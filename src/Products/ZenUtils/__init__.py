##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

from Products.CMFCore.DirectoryView import registerDirectory
registerDirectory('js', globals())

# import any monkey patches that may be necessary
from patches import pasmonkey
from patches import dirviewmonkey
from patches import mysqladaptermonkey
from patches import signalsmonkey
from patches import advancedquerymonkey
from patches import xmlmonkey
from patches import ofsmonkey
from Products.ZenUtils import pbkdf2  # Register PBKDF2 for password hashing
from Products.ZenUtils.Utils import unused
unused(pasmonkey, dirviewmonkey, advancedquerymonkey, mysqladaptermonkey, signalsmonkey, xmlmonkey, pbkdf2, ofsmonkey)

from Products.ZenUtils.MultiPathIndex import MultiPathIndex , \
                                             manage_addMultiPathIndex, \
                                             manage_addMultiPathIndexForm

from Products.PluggableAuthService import registerMultiPlugin
from AccessControl.Permissions import add_user_folders
from AccountLocker.AccountLocker import AccountLocker
from AccountLocker.AccountLocker import manage_addAccountLocker
from AccountLocker.AccountLocker import manage_addAccountLockerForm

def initialize(context):
    context.registerClass(
        MultiPathIndex,
        permission='Add Pluggable Index',
        constructors=(manage_addMultiPathIndexForm, manage_addMultiPathIndex),
        #icon="www/index.gif",
        visibility=None)


    registerMultiPlugin(AccountLocker.meta_type)

    context.registerClass(AccountLocker,
                        permission=add_user_folders,
                        constructors=(manage_addAccountLockerForm, manage_addAccountLocker),
                        visibility=None,
                        )


def safeTuple(arg):
    """
    >>> safeTuple(["foo", "blam"])
    ('foo', 'blam')
    >>> safeTuple([])
    ()
    >>> safeTuple(None)
    ()
    >>> safeTuple("foo")
    ('foo',)
    """
    if arg is not None:
        return tuple(arg) if hasattr(arg, '__iter__') else (arg,)
    else:
        return ()
