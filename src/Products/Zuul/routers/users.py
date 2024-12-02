##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


"""
Operations for Users
"""

import logging
from Products.ZenUtils.Ext import DirectRouter, DirectResponse
from Products.Zuul.decorators import require
from Products import Zuul
from Products.ZenMessaging.audit import audit

log = logging.getLogger('zen.UserRouter')


class UsersRouter(DirectRouter):
    """
    A JSON/ExtDirect interface to operations on Users
    """

    def __init__(self, context, request):
        self.facade = Zuul.getFacade('user', context)
        self.context = context
        self.request = request
        super(UsersRouter, self).__init__(context, request)

    def _getFacade(self):
        return self.facade

    @require('Manage DMD')
    def setAdminPassword(self, newPassword):
        audit('UI.Users.UpdateAdminPassword')
        self.facade.setAdminPassword(newPassword)
        return DirectResponse.succeed()

    def deleteUsers(self, userIds):
        """
        Removes all the users with the given user ids. Will continue
        upon removing users if an invalid id is specified.
        @type  userIds: List of Strings
        @param userIds: (optional) list of ids to remove.
        """
        facade = self._getFacade()
        facade.removeUsers(userIds)
        audit('UI.Users.RemoveUsers', userIds=userIds)
        return DirectResponse.succeed()

    def getUsers(self, keys=None, start=0, limit=50, page=0,
                    sort='name', dir='ASC', name=None):
        """
        Retrieves a list of users. This method supports pagination.
        @type  start: integer
        @param start: (optional) Offset to return the results from; used in
                      pagination (default: 0)
        @type  name: string
        @param name: (optional) filter to be applied to users returned (default: None)
        @type  limit: integer
        @param limit: (optional) Number of items to return; used in pagination
                      (default: 50)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return results (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: (list) Dictionaries of user properties
             - totalCount: (integer) Number of devices returned
        """
        facade = self._getFacade()
        users = facade.getUsers(start=start, limit=limit, sort=sort,
                                dir=dir, name=name)
        total = users.total
        data = Zuul.marshal(users, keys)
        return DirectResponse.succeed(data=data, totalCount=total)

    @require('Manage DMD')
    def addUser(self, id, password, email, roles=('ZenUser',)):
        """
        Adds a new user to the system.
        @type  id: string
        @param id: The unique identifier of the user, same as their login
        @type  password: string
        @param password: the password of the new user
        @type  roles: list of strings
        @param roles: (optional) roles to be applied to the new user
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: properties of the new users
        """
        facade = self._getFacade()
        newUser = facade.addUser(id, password, email, roles)
        audit('UI.Users.Add', id, email=email, roles=roles)
        return DirectResponse.succeed(data=Zuul.marshal(newUser))

    @require('Manage DMD')
    def markWizardAsFinished(self):        
        facade = self._getFacade()
        facade.markWizardAsFinished()
        audit('UI.Wizard.Complete')
        return DirectResponse.succeed()
        
