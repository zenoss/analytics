##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""RRDDataPoint

Defines attributes for how a datasource will be graphed
and builds the nessesary DEF and CDEF statements for it.

"""

import logging
log = logging.getLogger('zen.RRDDatapoint')

from AccessControl import ClassSecurityInfo, Permissions
from Products.ZenModel.ZenossSecurity import ZEN_VIEW, ZEN_MANAGE_DMD
from Products.ZenRelations.RelSchema import *
from Products.ZenWidgets import messaging

from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable

from Products.ZenUtils.Utils import unused, getDisplayType
from Products.ZenUtils.deprecated import deprecated
from Products.ZenModel.RRDDataPointAlias import manage_addDataPointAlias

@deprecated
def manage_addRRDDataPoint(context, id, REQUEST = None):
    """make a RRDDataPoint"""
    dp = RRDDataPoint(id)
    context._setObject(dp.id, dp)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()+'/manage_main')

def getDataPointsByAliases( context, aliases ):
    """
    Retrieve the datapoint/alias pairs for the passed aliases.
    """
    if not aliases: return
    for brains in context.dmd.searchRRDTemplates():
        template = brains.getObject()
        for datasource in template.datasources():
            if not hasattr(datasource, 'datapoints'):
                log.error('The datasource %s on template %s is broken -- skipping',
                          datasource, template.getPrimaryUrlPath())
                continue
            for datapoint in datasource.datapoints():
                thisDatapointsAliases = dict((dpAlias.id, dpAlias)
                                                for dpAlias in datapoint.aliases())
                for alias in aliases:
                    if alias in thisDatapointsAliases:
                        yield thisDatapointsAliases[alias], datapoint
                    if alias == datapoint.id:
                        yield None, datapoint

def getDataPointsByAlias( context, alias ):
    """
    Retrieve the datapoint/alias pairs for the passed alias.
    """
    return getDataPointsByAliases( context, [alias] )


#addRRDDataPoint = DTMLFile('dtml/addRRDDataPoint',globals())

SEPARATOR = '_'

def convertMethodParameter(value, type):
    __pychecker__='no-returnvalues'
    if type == "integer":
        return int(value)
    elif type == "string":
        return str(value)
    elif type == "float":
        return float(value)
    else:
        raise TypeError('Unsupported method parameter type: %s' % type)

class RRDDataPointError(Exception): pass

class RRDDataPoint(ZenModelRM, ZenPackable):

    meta_type = 'RRDDataPoint'

    rrdtypes = ('COUNTER', 'GAUGE', 'DERIVE', 'ABSOLUTE')

    createCmd = ""
    rrdtype = 'GAUGE'
    isrow = True
    rrdmin = None
    rrdmax = None

    ## These attributes can be removed post 2.1
    ## They should remain in 2.1 so the migrate script works correctly
    linetypes = ('', 'AREA', 'LINE')
    rpn = ""
    color = ""
    linetype = ''
    limit = -1
    format = '%5.2lf%s'


    _properties = (
        {'id':'rrdtype', 'type':'selection',
        'select_variable' : 'rrdtypes', 'mode':'w'},
        {'id':'createCmd', 'type':'text', 'mode':'w'},
        {'id':'isrow', 'type':'boolean', 'mode':'w'},
        {'id':'rrdmin', 'type':'string', 'mode':'w'},
        {'id':'rrdmax', 'type':'string', 'mode':'w'},
        {'id':'description', 'type':'string', 'mode':'w'},
        )


    _relations = ZenPackable._relations + (
        ("datasource", ToOne(ToManyCont,"Products.ZenModel.RRDDataSource","datapoints")),
        ("aliases", ToManyCont(ToOne, "Products.ZenModel.RRDDataPointAlias","datapoint"))
        )

    # Screen action bindings (and tab definitions)
    factory_type_information = (
    {
        'immediate_view' : 'editRRDDataPoint',
        'actions'        :
        (
            { 'id'            : 'edit'
            , 'name'          : 'Data Point'
            , 'action'        : 'editRRDDataPoint'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )

    security = ClassSecurityInfo()


    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        from RRDTemplate import crumbspath
        crumbs = super(RRDDataPoint, self).breadCrumbs(terminator)
        return crumbspath(self.rrdTemplate(), crumbs, -3)


    def name(self):
        """Include the data source name in our name,
        useful for lists of DataPoints"""
        return '%s%c%s' % (self.datasource().id, SEPARATOR, self.id)


    def getRRDCreateCommand(self, performanceConf):
        """Get the create command.
        Return '' for the default from performanceConf"""
        unused(performanceConf)
        if self.createCmd:
            return self.createCmd
        return ''


    def addAlias(self, id, formula=None):
        """
        Add a new alias to this datapoint
        """
        manage_addDataPointAlias( self, id, formula )


    def hasAlias(self, aliasId):
        """
        Whether this datapoint has an alias of this id
        """
        return hasattr( self.aliases, aliasId )


    def removeAlias(self, aliasId):
        """
        Remove any alias with the given id
        """
        if self.hasAlias( aliasId ):
            self.aliases._delObject( aliasId )


    def getAliasNames(self):
        """
        Return all the ids of this datapoint's aliases
        """
        return [ alias.id for alias in self.aliases() ]

    def isRate(self):
        return self.rrdtype in ('COUNTER', 'DERIVE')

    def isCounter(self):
        # rrdmin is defined as a string above
        return self.rrdtype == 'COUNTER' or (self.rrdtype =='DERIVE' and str(self.rrdmin) == '0')

    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addDataPointAlias')
    def manage_addDataPointAlias(self, id, formula, REQUEST=None ):
        """
        Add an alias to this datapoint
        """
        alias = manage_addDataPointAlias( self, id, formula )
        if REQUEST:
            return self.callZenScreen(REQUEST)
        return alias


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_removeDataPointAliases')
    def manage_removeDataPointAliases(self, ids=(), REQUEST=None ):
        """
        Remove aliases from this datapoint
        """
        for id in ids:
            self.removeAlias( id )
        if REQUEST:
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'zmanage_editProperties')
    def zmanage_editProperties(self, REQUEST=None, redirect=False):
        """Edit a ZenModel object and return its proper page template
        """
        unused(redirect)
        if REQUEST:
            msgs = []
            for optional in 'rrdmin', 'rrdmax':
                v = REQUEST.form.get(optional, None)
                if v:
                    try:
                        REQUEST.form[optional] = long(v)
                    except ValueError:
                        msgs.append('Unable to convert "%s" to a number' % v)
            msgs = ', '.join(msgs)
            if msgs:
                messaging.IMessageSender(self).sendToBrowser(
                    'Properties Saved',
                    msgs[0].capitalize() + msgs[1:]
                )
                return self.callZenScreen(REQUEST, False)

        return ZenModelRM.zmanage_editProperties(self, REQUEST)
