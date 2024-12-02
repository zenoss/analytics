##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from Products.Five.browser import BrowserView
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
from Products.ZenUtils.jsonutils import json
from Products.ZenUtils.Utils import formreq, unused, ipsortKey
from Products.AdvancedQuery import MatchRegexp, Or, Eq, In
from Products.ZenUtils.FakeRequest import FakeRequest
from Products.ZenWidgets import messaging
from Products.ZenWidgets.interfaces import IMessageSender
from Products.Zuul.catalog.interfaces import IModelCatalogTool

class AdvancedQueryDeviceList(object):
    """
    Adapter providing list of devices according to various criteria.
    """
    def __init__(self, context):
        self.context = context

    def __call__(self, *args, **kwargs):
        """
        Needs to be definition rather than simple reference due to possibility
        of monkeypatching the hook.
        """
        return self._getAdvancedQueryDeviceList(*args, **kwargs)

    def _getAdvancedQueryDeviceList(self, offset=0, count=50, filter='',
                                   orderby='name', orderdir='asc'):
        """
        Ask the catalog for devices matching the criteria specified.
        """
        context = self.context
        if not isinstance(context, DeviceOrganizer):
            context = self.context.dmd.Devices
        catalog = IModelCatalogTool(context).devices
        devfilter = '(?is).*%s.*' % filter
        filterquery = Or(
            MatchRegexp('id', devfilter),
            MatchRegexp('name', devfilter),
            MatchRegexp('text_ipAddress', devfilter),
            MatchRegexp('deviceClassPath', devfilter)
        )
        query = Eq('uid', context.absolute_url_path()
                    ) & filterquery
        objects = catalog.search(
            query=query,
            start=int(offset),
            limit=int(count),
            order_by=orderby,
            reverse=orderdir != 'asc'
        )
        objects = list(objects)
        totalCount = len(objects)
        return totalCount, objects


class DeviceList(BrowserView):
    """
    Populates the device list.
    """
    @formreq
    def __call__(self, *args, **kwargs):
        return self._getJSONDeviceInfo(*args, **kwargs)

    @json
    def _getJSONDeviceInfo(self, offset=0, count=50, filter='',
                           orderby='titleOrId', orderdir='asc'):
        """
        Get devices under self according to criteria and return results as
        JSON.

        @return: A JSON representation of a tuple containing a list of lists of
        device info, and the total number of matching devices
        @rtype: "([[a, b, c], [a, b, c]], 17)"
        """
        devList = AdvancedQueryDeviceList(self.context)
        totalCount, devicelist = devList(offset, count, filter, orderby,
                                         orderdir)
        obs = [x.getObject() for x in devicelist]
        if orderby=='getDeviceIp':
            obs.sort(key=lambda a:ipsortKey(a.getDeviceIp()),
                        reverse=(orderdir=='desc'))
        results = [ob.getDataForJSON(minSeverity=2) + ['odd'] for ob in obs]
        return results, totalCount


class DeviceBatch(BrowserView):
    """
    Given various criteria, figure out what devices are relevant and execute
    the action specified.
    """
    @formreq
    def __call__(self, *args, **kwargs):
        return self._setDeviceBatchProps(*args, **kwargs)

    @property
    def id(self):
        """
        This can appear in the acquisition chain, and ZenModelBase.getDmd needs
        an id attribute.
        """
        return self.context.id

    def _setDeviceBatchProps(self, method='', extraarg=None,
                             selectstatus='none', goodevids=[],
                             badevids=[], offset=0, count=50, filter='',
                             orderby='titleOrId', orderdir='asc', **kwargs):
        d = {'lockDevicesFromUpdates':'sendEventWhenBlocked',
             'lockDevicesFromDeletion':'sendEventWhenBlocked',
             'unlockDevices':'',
             'setGroups':'groupPaths',
             'setSystems':'systemPaths',
             'setLocation':'locationPath',
             'setPerformanceMonitor':'performanceMonitor',
             'moveDevices':'moveTarget',
             'removeDevices':('deleteStatus', 'deleteHistory', 'deletePerf'),
             'setProdState':'state',
             'setPriority':'priority'
            }
        if not method or not method in d:
            IMessageSender(self.request).sendToBrowser(
                'Unable to Perform Action',
                'An empty or invalid action was attempted.',
                priority=messaging.CRITICAL
            )
            return self()

        request = FakeRequest()
        argdict = dict(REQUEST=request)
        if d[method]:
            d_method = d[method]
            if isinstance(d_method, (tuple, list)):
                for argName in d_method:
                    argdict[argName] = self.request.get(argName, None)
            else:
                argdict[d_method] = extraarg
        action = getattr(self.context, method)
        argdict['deviceNames'] = self._getDeviceBatch(selectstatus,
                                  goodevids, badevids, offset, count,
                                  filter, orderby, orderdir)
        # This will call the method on the context, which will redirect to a
        # new (or the same) screen and set a message
        try:
            result = action(**argdict)
        except Exception:
            msgs = {'lockDevicesFromUpdates':'lock devices from updates',
                    'lockDevicesFromDeletion':'lock devices from deletion',
                    'unlockDevices':'unlock devices',
                    'setGroups':'change device groups',
                    'setSystems':'change device systems',
                    'setLocation':'set the location',
                    'setPerformanceMonitor':'set the performance monitor',
                    'moveDevices':'move devices',
                    'removeDevices':'delete devices',
                    'setProdState':'set production state',
                    'setPriority':'set priority'
                }
            IMessageSender(self.request).sendToBrowser(
                'Unable to Perform Action',
                'There was an error attempting to %s.' % msgs[method],
                priority=messaging.CRITICAL
            )
        else:
            return result

    def _getDeviceBatch(self, selectstatus='none', goodevids=[],
                       badevids=[], offset=0, count=50, filter='',
                       orderby='titleOrId', orderdir='asc'):
        unused(count, offset, orderby, orderdir)
        if not isinstance(goodevids, (list, tuple)):
            goodevids = [goodevids]
        if not isinstance(badevids, (list, tuple)):
            badevids = [badevids]
        if selectstatus == 'all':
            idquery = ~In('id', badevids)
        else:
            idquery = In('id', goodevids)
        devfilter = '(?is).*%s.*' % filter
        filterquery = Or(
            MatchRegexp('id', devfilter),
            MatchRegexp('name', devfilter),
            MatchRegexp('text_ipAddress', devfilter),
            MatchRegexp('deviceClassPath', devfilter)
        )
        query = Eq('uid', self.context.absolute_url_path()) & idquery
        query = query & filterquery
        catalog = IModelCatalogTool(self.context)
        objects = catalog.search(query=query)
        return [x['id'] for x in objects]
