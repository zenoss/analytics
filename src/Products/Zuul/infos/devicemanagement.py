##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.Zuul.infos import InfoBase, ProxyProperty

class MaintenanceWindowInfo(InfoBase):
    name = ProxyProperty('name')
    start = ProxyProperty('start')
    started = ProxyProperty('started')
    enabled = ProxyProperty('enabled')
    #duration = ProxyProperty('duration')
    repeat = ProxyProperty('repeat')
    skip = ProxyProperty('skip')
    days = ProxyProperty('days')
    occurrence = ProxyProperty('occurrence')
    startState = ProxyProperty('startProductionState')
    timezone = ProxyProperty('timezone')

    @property
    def startProdState(self):
        return self._object.niceStartProductionState()

    @property
    def niceRepeat(self):
        return self._object.niceRepeat()

    @property
    def duration(self):
        return self._object.niceDuration()

    @property
    def startTime(self):
        return self._object.niceStartDateTime()

    def updateWindow(self, p):
        self._object.manage_editMaintenanceWindow( 
                                     startDateTime=p.get('startDateTime', None),
                                     startDate=p.get('startDate', None),
                                     startHours=p.get('startHours', None),
                                     startMinutes=p.get('startMinutes', None),
                                     durationDays=p['durationDays'],
                                     durationHours=p['durationHours'],
                                     durationMinutes=p['durationMinutes'],
                                     repeat=p['repeat'],
                                     days=p.get('days', 'Sunday'),
                                     occurrence=p.get('occurrence', '1st'),
                                     startProductionState=p['startProductionState'],
                                     enabled=p['enabled'],
                                     timezone=p.get('timezone', None),
                                )

class UserCommandManagementInfo(InfoBase):
    id = ProxyProperty('id')
    command = ProxyProperty('command')
    description = ProxyProperty('description')

    def updateUserCommand(self, params):
        self._object.updateUserCommand(params)

class AdminRoleManagementInfo(InfoBase):
    id = ProxyProperty('id')
    description = ProxyProperty('description')
    role = ProxyProperty('role')

    @property
    def email(self):
        return self._object.email()

    @property
    def pager(self):
        return self._object.pager()

