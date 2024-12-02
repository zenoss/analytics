##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.Zuul.infos import InfoBase

class UserCommandInfo(InfoBase):

    def getCommand(self):
        return self._object.command

    def setCommand(self, command):
        self._object.command = command

    command = property(getCommand, setCommand)
