##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""ReportClass

ReportClass groups different types of reports together

$Id: ReportClass.py,v 1.3 2004/04/22 15:33:44 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from App.special_dtml import DTMLFile

from Organizer import Organizer
from ZenPackable import ZenPackable
from ZenossSecurity import ZEN_COMMON, ZEN_MANAGE_DMD
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Utils import unused, getDisplayType
from Products.ZenWidgets import messaging
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.deprecated import deprecated

@deprecated
def manage_addReportClass(context, id, title = None, REQUEST = None):
    """make a report class"""
    dc = ReportClass(id, title)
    context._setObject(id, dc)

    if REQUEST is not None:
        audit('UI.Organizer.Add', dc.id, title=title, organizer=context)
        messaging.IMessageSender(context).sendToBrowser(
            'Report Organizer Created',
            'Report organizer %s was created.' % id
        )
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() + '/manage_main') 

addReportClass = DTMLFile('dtml/addReportClass',globals())

class ReportClass(Organizer, ZenPackable):
    dmdRootName = "Reports"
    portal_type = meta_type = "ReportClass"

    #sub_meta_types = ("ReportClass", "Report", 'DeviceReport', 'GraphReport', 
    #                'MultiGraphReportClass')

    _relations = Organizer._relations + ZenPackable._relations
    
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'immediate_view' : 'viewReportClass',
            'actions'        :
            ( 
                { 'id'            : 'view'
                , 'name'          : 'Status'
                , 'action'        : 'viewReportClass'
                , 'permissions'   : ( "View",)
                , 'visible'       : 1
                },
            )
          },
        )
    
    security = ClassSecurityInfo()

    security.declareProtected(ZEN_COMMON, "children")
    def children(self, sort=False, checkPerm=True, spec=None):
        ''' Return all objects that are instances of ReportClass
        '''
        unused(spec)
        kids = [o for o in self.objectValues() if isinstance(o, ReportClass)]
        if checkPerm:
            kids = [kid for kid in kids if self.checkRemotePerm("View", kid)]
        if sort: 
            kids.sort(key=lambda x: x.primarySortKey())
        return kids


    def childIds(self, spec=None):
        """Return Ids of children within our organizer."""
        unused(spec)
        return [k.id for k in self.children()]


    security.declareProtected(ZEN_COMMON, "countChildren")
    def countChildren(self, spec=None):
        """Return a count of all our contained children."""
        unused(spec)
        count = len(self.children())
        count += sum(child.countChildren() for child in self.children())
        return count


    def getReportClass(self):
        ''' Return the class to instantiate for new report classes
        '''
        return ReportClass


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addReportClass')
    def manage_addReportClass(self, id, title = None, REQUEST = None):
        """make a report class"""
        rClass = self.getReportClass()
        dc = rClass(id, title)
        self._setObject(id, dc)
        if REQUEST:
            audit('UI.Organizer.Add', dc.id, title=title)
            messaging.IMessageSender(self).sendToBrowser(
                'Report Organizer Created',
                'Report organizer %s was created.' % id
            )
            return self.callZenScreen(REQUEST)


    def reports(self):
        """Return list of report instances.
        """
        reportspec = ('Report','DeviceReport','GraphReport','MultiGraphReport')
        return [r for r in self.objectValues(spec=reportspec)
                    if self.checkRemotePerm('View', r)]


    def countReports(self):
        """Return a count of all our contained children."""
        count = len(self.reports())
        count += sum(child.countReports() for child in self.children())
        return count


    security.declareProtected('Manage DMD', 'manage_addGraphReport')
    @deprecated
    def manage_addGraphReport(self, id, REQUEST=None):
        """Add an graph report to this object.
        """
        if id:
            from Products.ZenModel.GraphReport import GraphReport
            gr = GraphReport(id)
            self._setObject(id, gr)
            if REQUEST:
                audit('UI.Report.Add', gr.id, reportType=getDisplayType(gr))
                messaging.IMessageSender(self).sendToBrowser(
                    'Report Created',
                    'Graph report %s was created.' % id
                )
                return self.callZenScreen(REQUEST)

    @deprecated
    def moveReports(self, moveTarget, ids=None, REQUEST=None):
        """Move a report from here organizer to moveTarget.
        """
        if not moveTarget or not ids: return self()
        if isinstance(ids, basestring): ids = (ids,)
        target = self.getOrganizer(moveTarget)
        for rptname in ids:
            rpt = self._getOb(rptname)
            rpt._operation = 1 # moving object state
            self._delObject(rptname)
            target._setObject(rptname, rpt)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Reports Moved',
                'Reports %s were moved to %s.' % (', '.join(ids), moveTarget)
            )
            REQUEST['RESPONSE'].redirect(target.getPrimaryUrlPath())


    def exportXmlHook(self, ofile, ignorerels):
        """patch to export all device components
        """
        from Acquisition import aq_base
        for o in self.reports():
            if hasattr(aq_base(o), 'exportXml'):
                o.exportXml(ofile, ignorerels)



InitializeClass(ReportClass)
