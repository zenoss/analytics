##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

from zope.interface import Interface, Attribute

class IPreBackupEvent(Interface):
    """ 
    ZenBackup's ZODB backup event
    """
    zen_backup_object = Attribute("Reference to process that is running the zenbackup.")

class IPostBackupEvent(Interface):
    """ 
    ZenBackup's unlock zodb event
    """
    zen_backup_object = Attribute("Reference to process that is running the zenbackup.")
    
