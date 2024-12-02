##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__="""GraphPoint

Defines attributes for how a data source will be graphed
and builds the nessesary rrd commands.
"""

from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
from Products.ZenModel.ZenossSecurity import *
from Products.ZenRelations.RelSchema import *
from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable
from Products.ZenWidgets import messaging
from Products.ZenUtils.deprecated import deprecated
from zope.interface import implements
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable

@deprecated
def manage_addGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = GraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class GraphPoint(ZenModelRM, ZenPackable):
    '''
    '''
    implements(IGloballyIdentifiable)
    isThreshold = False

    DEFAULT_FORMAT = '%5.2lf%s'
    DEFAULT_LEGEND = '${graphPoint/id}'
    DEFAULT_MULTIGRAPH_LEGEND = '${here/name | here/id} ${graphPoint/id}'

    sequence = 0
    _properties = (
        {'id':'sequence', 'type':'long', 'mode':'w'},
        )

    _relations = ZenPackable._relations + (
        ("graphDef", ToOne(ToManyCont,"Products.ZenModel.GraphDefinition","graphPoints")),
        )

    factory_type_information = (
        {
            'immediate_view' : 'editGraphPoint',
            'actions'        :
            (
                { 'id'            : 'edit'
                , 'name'          : 'Graph Point'
                , 'action'        : 'editGraphPoint'
                , 'permissions'   : ( Permissions.view, )
                },
            )
        },
    )

    # category 20 colors from d3
    # see https://github.com/mbostock/d3/wiki/Ordinal-Scales#wiki-category20
    colors = ["#1f77b4", "#aec7e8", "#98df8a", "#ff7f0e", "#ffbb78", "#2ca02c",
              "#d62728", "#ff9896", "#9467bd", "#c5b0d5", "#8c564b",
              "#c49c94", "#e377c2", "#f7b6d2", "#7f7f7f", "#c7c7c7", "#bcbd22",
              "#dbdb8d", "#17becf", "#9edae5"];


    security = ClassSecurityInfo()

    ## Interface


    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        if self.graphDef.rrdTemplate():
            from RRDTemplate import crumbspath
            crumbs = super(GraphPoint, self).breadCrumbs(terminator)
            return crumbspath(self.graphDef(), crumbs, -3)
        return ZenModelRM.breadCrumbs(self, terminator)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_editProperties')
    def manage_editProperties(self, REQUEST):
        '''
        Process a save request from a GraphPoint edit screen.  Perform
        validation on fields and either return error message or save
        results.
        '''

        lineType = REQUEST.get('lineType', '').strip().lower()
        stacked = str(REQUEST.get('stacked', '')).strip().lower()
        stackedLine = lineType == 'line' and stacked == 'true'
        if stackedLine:
            messaging.IMessageSender(self).sendToBrowser(
                'Invalid definition',
                'Only Area graphs may be stacked. ',
                priority=messaging.WARNING
            )

        def IsHex(s):
            try:
                _ = long(color, 16)
            except ValueError:
                return False
            return True

        color = REQUEST.get('color', '').strip().lstrip('#').upper()
        if color:
            if len(color) in (6, 8) and IsHex(color):
                REQUEST.form['color'] = color
            else:
                messaging.IMessageSender(self).sendToBrowser(
                    'Invalid Color',
                    'Color must be a 6 or 8-digit hexadecimal value.',
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
        return self.zmanage_editProperties(REQUEST)


    def getDescription(self):
        ''' Return a description
        '''
        return self.id


    def getTalesContext(self, thing=None, **kw):
        '''
        Standard stuff to add to context for tales expressions
        '''
        context = {
            'graphDef': self.graphDef(),
            'graphPoint': self,
            }
        if thing:
            thing.getRRDContextData(context)
        for key, value in kw.items():
            context[key] = value
        return context


    def talesEval(self, str, context, **kw):
        '''
        return a tales evaluation of str
        '''
        from Products.ZenUtils.ZenTales import talesEvalStr
        extraContext = self.getTalesContext(thing=context, **kw)
        try:
            result = talesEvalStr(str, context, extraContext)
        except Exception:
            result = '(Tales expression error)'
        return result


    ## Graphing Support

    def getColor(self, index):
        """
        Return a string apprpriate for use as the color part of an
        rrd graph command.  The color either comes from the attribute on
        this object or from an offset into the self.colors list.
        """
        color = None
        if self.color:
            color = self.color
            try:
                _ = long(color.replace("#", ""), 16)
            except ValueError:
                color = None
        if not color:
            index %= len(self.colors)
            color = self.colors[index]
        color = '#%s' % color.lstrip('#')

        return color


    def getThresholdColor(self, index):
        index %= len(self.colors)
        color = self.color or self.colors[-1 * (index+1)]
        color = '#%s' % color.lstrip('#')
        return color


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx,
                    multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        from Products.ZenUtils.Utils import unused
        unused(multiid, prefix, rrdDir)
        return cmds


    def getDsName(self, base, multiid=-1, prefix=''):
        name = self.addPrefix(prefix, base)
        if multiid > -1:
            name = '%s_%s' % (name, multiid)
        return name


    def addPrefix(self, prefix, base):
        ''' If not base then return ''
        elif prefix then return prefix_base
        else return base
        The result is rrd scrubbed
        '''
        s = base or ''
        if s and prefix:
            s = '_'.join((prefix, base))
        s = self.scrubForRRD(s)
        return s


    def scrubForRRD(self, value, namespace=None):
        ''' scrub value so it is a valid rrd variable name.  If namespace
        is provided then massage value as needed to avoid name conflicts
        with items in namespace.
        '''
        import string
        import itertools
        validRRDchars=set(string.ascii_letters + string.digits + '_-')
        value = ''.join(c if c in validRRDchars else '_' for c in value)
        if namespace:
            postfixIter = itertools.count(2)
            candidate = value
            while candidate in namespace:
                candidate = value + str(postfixIter.next())
            value = candidate
        return value


    def escapeForRRD(self, value):
        '''
        Escapes characters like colon ':' for use by RRDTool which would
        '''
        value = value.replace(":", "\:")[:198]
        return value


InitializeClass(GraphPoint)
