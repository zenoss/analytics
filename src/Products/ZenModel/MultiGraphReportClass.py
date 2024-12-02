##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""MultiGraphReportClass

MultiGraphReportClass contain MultiGraphReports.
"""

from AccessControl import ClassSecurityInfo
from App.special_dtml import DTMLFile
from ReportClass import ReportClass
from Products.ZenRelations.RelSchema import *
from AccessControl.class_init import InitializeClass
from Products.ZenWidgets import messaging
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.Utils import getDisplayType
from Products.ZenUtils.deprecated import deprecated
from Products.ZenModel.MultiGraphReport import MultiGraphReport

@deprecated
def manage_addMultiGraphReportClass(context, id, title = None, REQUEST = None):
    """ Construct a new MultiGraphreportclass
    """
    frc = MultiGraphReportClass(id, title)
    context._setObject(id, frc)
    if REQUEST is not None:
        audit('UI.ReportClass.Add', frc.id, title=title, organizer=context)
        messaging.IMessageSender(self).sendToBrowser(
            'Organizer Created',
            'Report organizer %s was created.' % id
        )
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() + '/manage_main') 

addMultiGraphReportClass = DTMLFile('dtml/addMultiGraphReportClass',globals())

class MultiGraphReportClass(ReportClass):

    portal_type = meta_type = "MultiGraphReportClass"

    # Remove this relationship after version 2.1
    _relations = ReportClass._relations +  (
        ('graphDefs', 
            ToManyCont(ToOne, 'Products.ZenModel.GraphDefinition', 'reportClass')),
        )
    
    security = ClassSecurityInfo()
    
    def getReportClass(self):
        """ Return the class to instantiate for new report classes
        """
        return MultiGraphReportClass


    security.declareProtected('Manage DMD', 'manage_addMultiGraphReport')
    def manage_addMultiGraphReport(self, id, REQUEST=None):
        """Add a MultiGraph report to this object.
        """
        fr = MultiGraphReport(id)
        self._setObject(id, fr)
        if REQUEST:
            audit('UI.Report.Add', fr.id, reportType=getDisplayType(fr))
            url = '%s/%s/editMultiGraphReport' % (self.getPrimaryUrlPath(), id)
            return REQUEST['RESPONSE'].redirect(url)
        return self._getOb(id)


InitializeClass(MultiGraphReportClass)
