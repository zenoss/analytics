##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
Announces messages so they can be tracked or handled.

Messages have a category hierarchy, an object/uid, and various passed data.
If an object is passed it will attempt to determine its current name and uid.
Values that evaluate to False are never shown, so pass str(value) if needed.

Examples:
    from Products.ZenMessaging.audit import audit

    audit('UI.Widget.Add',                     #category string or list
          widgetObjectOrUid,                   #object or UID
          color='Red', numUses=10, ...)        #pass data via kwargs

    audit('UI.Widget.Edit',                    #Source.Kind.Action
          widget,                              #object
          numUses=25, ...                      #pass data via kwargs (X=Y)
          data_={dynamicName: value},          #pass data dynamically {X:Y}
          oldData_={'x': oldX, 'numUses': 10}, #old values for comparison
          skipFields_=('Referrer','REQUEST'),  #ignore these keys if found
          maskFields_=('passwd','Password'))   #hide the values of these keys

If old values are passed it shows the new/changed/deleted values.
If old values are passed and nothing changed at all, there's no announcement.

Example:
    # 'Up' was edited, 'Uppp' and 'Away' are new, and 'Down' was deleted.
    # 'Same' will not be shown since its value didn't change.
    category = [auditSource, objectKind, theAction]
    data    = {'Up': 123, 'Uppp': 456, 'Away': 999, 'Same': 50}
    oldData = {'Up': 100, 'Down': 'x', 'Same': 50}
    audit(category, uid, data_=data, oldData_=oldData)

    # Sample output
    user=zenoss action=Add kind=Widget widget=/Widgets/xyz
        away=999 old_down=x up=123 old_up=100 uppp=456
"""

from zope.component import queryUtility

from .interfaces import IAuditManager


def getAuditManager():
    """Convenience method."""
    return queryUtility(IAuditManager)


def audit(*args, **kwargs):
    """Convenience method."""
    util = getAuditManager()
    if util:
        util.audit(*args, **kwargs)


def auditComment(comment, **kwargs):
    """Convenience method for scripts and zendmd. Don't call from the UI."""
    audit("Shell.Comment.Log", comment, **kwargs)
