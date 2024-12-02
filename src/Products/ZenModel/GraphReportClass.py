##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""GraphReportClass

GraphReportClass contain GraphReports.
"""

from AccessControl import ClassSecurityInfo
from App.special_dtml import DTMLFile
from ReportClass import ReportClass
from AccessControl.class_init import InitializeClass
from Products.ZenWidgets import messaging
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.Utils import getDisplayType
from Products.ZenUtils.deprecated import deprecated
from Products.ZenModel.GraphReport import GraphReport

@deprecated
def manage_addGraphReportClass(context, id, title = None, REQUEST = None):
    """ Construct a new GraphReportclass
    """
    rc = GraphReportClass(id, title)
    context._setObject(rc.id, rc)
    if REQUEST is not None:
        audit('UI.ReportClass.Add', rc.id, title=title, organizer=context)
        messaging.IMessageSender(context).sendToBrowser(
            'Report Organizer Created',
            'Report organizer %s was created.' % id
        )
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() + '/manage_main')

addGraphReportClass = DTMLFile('dtml/addGraphReportClass',globals())

class GraphReportClass(ReportClass):

    portal_type = meta_type = "GraphReportClass"

    security = ClassSecurityInfo()

    def getReportClass(self):
        """ Return the class to instantiate for new report classes
        """
        return GraphReportClass


    security.declareProtected('Manage DMD', 'manage_addGraphReport')
    def manage_addGraphReport(self, id, REQUEST=None):
        """Add a graph report to this object.
        """
        fr = GraphReport(id)
        self._setObject(id, fr)
        fr = self._getOb(id)
        if REQUEST:
            audit('UI.Report.Add', fr.id, reportType=getDisplayType(fr))
            url = '%s/%s/editGraphReport' % (self.getPrimaryUrlPath(),id)
            return REQUEST['RESPONSE'].redirect(url)
        return fr


InitializeClass(GraphReportClass)
