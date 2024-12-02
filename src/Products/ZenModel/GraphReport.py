##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.deprecated import deprecated
from Products.ZenModel.BaseReport import BaseReport
from Products.ZenRelations.RelSchema import ToManyCont, ToOne
from GraphReportElement import GraphReportElement
from Products.ZenUtils.Utils import getObjByPath, getDisplayType
from Products.ZenUtils.ZenTales import talesCompile, getEngine
from Products.ZenWidgets import messaging
from DateTime import DateTime

@deprecated
def manage_addGraphReport(context, id, REQUEST = None):
    """
    Create a new GraphReport
    """
    gr = GraphReport(id)
    context._setObject(gr.id, gr)
    if REQUEST is not None:
        audit('UI.Report.Add', gr.id, reportType=getDisplayType(gr), organizer=context)
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()+'/manage_main')


class GraphReport(BaseReport):

    meta_type = "GraphReport"
    
    numColumns = 1
    numColumnsOptions = (1, 2, 3)
    comments = (
        '<div style="float: right;"><img src="img/onwhitelogo.png"></div>\n'
        '<div style="font-size: 16pt;">${report/id}</div>\n'
        '<div style="font-size:12pt;">${now/aDay} ${now/aMonth} ${now/day},'
        ' ${now/year}<br />\n'
        '${now/AMPMMinutes}\n'
        '</div>\n'
        '<div style="clear: both" />')

    _properties = BaseReport._properties + (
        {'id':'comments', 'type':'text', 'mode':'w'},
        {'id':'numColumns', 'type':'int', 
            'select_variable' : 'numColumnOptions', 'mode':'w'},
    )

    _relations =  (
        ("elements", 
            ToManyCont(ToOne,"Products.ZenModel.GraphReportElement", "report")),
        )

    factory_type_information = ( 
        { 
            'immediate_view' : '',
            'actions'        :
            ( 
                {'name'          : 'View Report',
                'action'        : '',
                'permissions'   : ("View",),
                },
                {'name'          : 'Edit Report',
                'action'        : 'editGraphReport',
                'permissions'   : ("Manage DMD",),
                },
            )
         },
        )

    security = ClassSecurityInfo()


    def getBreadCrumbUrlPath(self):
        """
        Return the url to be used in breadcrumbs for this object.
        """
        return self.getPrimaryUrlPath() + '/editGraphReport'

    def getThing(self, deviceId, componentPath):
        """
        Return either a device or a component, or None if not found
        """
        thing = self.dmd.Devices.findDevice(deviceId)
        if thing and componentPath:
            try:
                return getObjByPath(thing, componentPath)
            except KeyError:
                return None
        return thing


    security.declareProtected('Manage DMD', 'manage_addGraphElement')
    def manage_addGraphElement(self, deviceIds='', componentPaths='',
                            graphIds=(), REQUEST=None):
        """
        Add a new graph report element
        """
        def GetId(deviceId, componentPath, graphId):
            component = componentPath.split('/')[-1]
            parts = [p for p in (deviceId, component, graphId) if p]
            root = ' '.join(parts)
            candidate = self.prepId(root)
            i = 2
            while candidate in self.elements.objectIds():
                candidate = self.prepId('%s-%s' % (root, i))
                i += 1
            return candidate

        if isinstance(deviceIds, basestring):
            deviceIds = [deviceIds]
        if isinstance(componentPaths, basestring):
            componentPaths = [componentPaths]
        componentPaths = componentPaths or ('')
        for devId in deviceIds:
            dev = self.dmd.Devices.findDevice(devId)
            # NOTE: There is no much sense to use component, which missed on
            #       device, so we filred components to use only related to
            #       device ones.
            for cPath in filter(lambda path: dev.id in path, componentPaths) or ['']:
                try:
                    thing = getObjByPath(dev, cPath)
                except KeyError:
                    continue
                else:
                    for graphId in graphIds:
                        graph = thing.getGraphDef(graphId)
                        if graph:
                            newId = thing.name
                            if callable(newId):
                                newId = newId()

                            newId = GetId(devId, cPath, graphId)
                            ge = GraphReportElement(newId)
                            ge.deviceId = dev.titleOrId()
                            ge.componentPath = cPath
                            ge.graphId = graphId
                            ge.sequence = len(self.elements())
                            self.elements._setObject(ge.id, ge)
                            if REQUEST:
                                audit('UI.Report.AddGraphElement', self.id, graphelement=ge.id)
            
        if REQUEST:

            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_deleteGraphReportElements')
    def manage_deleteGraphReportElements(self, ids=(), REQUEST=None):
        """
        Delete elements from this report
        """
        for id in ids:
            self.elements._delObject(id)
        self.manage_resequenceGraphReportElements()
        if REQUEST:
            for id in ids:
                audit('UI.Report.DeleteGraphElement', self.id, graphelement=id)
            messaging.IMessageSender(self).sendToBrowser(
                'Graphs Deleted',
                '%s graph%s were deleted.' % (len(ids),
                                              len(ids)>1 and 's' or '')
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 
                                    'manage_resequenceGraphReportElements')
    def manage_resequenceGraphReportElements(self, seqmap=(), origseq=(),
                                    REQUEST=None):
        """Reorder the sequecne of the graphs.
        """
        from Products.ZenUtils.Utils import resequence
        retval = resequence(self, self.elements(), seqmap, origseq, REQUEST)
        if REQUEST:
            audit('UI.Report.ResequenceGraphElements', self.id, sequence=seqmap, oldData_={'sequence':origseq})
        return retval
    

    security.declareProtected('View', 'getComments')
    def getComments(self):
        """
        Returns tales-evaluated comments
        """
        compiled = talesCompile('string:' + self.comments)
        e = {'rpt': self, 'report': self, 'now':DateTime()}
        result = compiled(getEngine().getContext(e))
        if isinstance(result, Exception):
            result = 'Error: %s' % str(result)
        return result


    def getElements(self):
        """
        get the ordered elements
        """
        return sorted(self.elements(), key=lambda a: a.sequence)


InitializeClass(GraphReport)
