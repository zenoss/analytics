##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''DeviceReportClass

DeviceReportClass contain DeviceReports.
'''

from AccessControl import ClassSecurityInfo
from App.special_dtml import DTMLFile
from ReportClass import ReportClass
from AccessControl.class_init import InitializeClass
from Products.ZenWidgets import messaging
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.deprecated import deprecated
from Products.ZenUtils.Utils import getDisplayType

@deprecated
def manage_addDeviceReportClass(context, id, title = None, REQUEST = None):
    """
    Construct a new DeviceReportclass
    """
    frc = DeviceReportClass(id, title)
    context._setObject(id, frc)
    if REQUEST is not None:
        audit('UI.ReportClass.Add', frc.id, title=title, organizer=context)
        messaging.IMessageSender(context).sendToBrowser(
            'Organizer Created',
            'Device report organizer %s was created.' % id
        )
        return REQUEST['RESPONSE'].redirect(
            context.absolute_url_path() + '/manage_main')

addDeviceReportClass = DTMLFile('dtml/addDeviceReportClass',globals())


class DeviceReportClass(ReportClass):

    portal_type = meta_type = "DeviceReportClass"

    security = ClassSecurityInfo()

    def getReportClass(self):
        ''' Return the class to instantiate for new report classes
        '''
        return DeviceReportClass


    security.declareProtected('Manage DMD', 'manage_addDeviceReport')
    @deprecated
    def manage_addDeviceReport(self, id, REQUEST=None):
        """Add a report to this object.
        """
        from Products.ZenModel.DeviceReport import DeviceReport
        fr = DeviceReport(id)
        self._setObject(id, fr)
        fr = self._getOb(id)
        if REQUEST:
            audit('UI.Report.Add', fr.id, reportType=getDisplayType(fr))
            url = '%s/%s/editDeviceReport' % (self.getPrimaryUrlPath(), id)
            return REQUEST['RESPONSE'].redirect(url)
        return fr


InitializeClass(DeviceReportClass)
