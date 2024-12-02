##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import re

from Products import Zuul
from Products.Five.browser import BrowserView
from Products.ZenUtils.jsonutils import json
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
from zenoss.protocols.protobufs.zep_pb2 import (STATUS_NEW, STATUS_ACKNOWLEDGED, SEVERITY_CRITICAL,
                                                SEVERITY_ERROR, SEVERITY_WARNING, SEVERITY_INFO,
                                                SEVERITY_DEBUG)

class SinglePill(BrowserView):
    def __call__(self):
        """
        Gets event pill for worst severity.

        @return: HTML that will render the event pill.
        @rtype: str
        """
        pill = getEventPillME(self.context)
        if isinstance(pill, (list, tuple)) and len(pill)==1: return pill[0]
        return pill


class ObjectsEventSummary(BrowserView):
    """
    Return an HTML link and event pill for each object passed as a JSON
    object ready for inclusion in a YUI data table.

    @param objects: The objects for which to create links and pills.
    @type objects: list
    @return: A JSON-formatted string representation of the columns and rows
        of the table
    @rtype: string
    """
    @json
    def __call__(self):
        zem = self.context.dmd.ZenEventManager
        obs = self._getObs()
        return getDashboardObjectsEventSummary(zem, obs)

    def _getObs(self):
        raise NotImplementedError


class SubOrganizersEventSummary(ObjectsEventSummary):
    def _getObs(self):
        return self.context.children()


class SubDevicesEventSummary(ObjectsEventSummary):
    def _getObs(self):
        return self.context.devices()


class SingleObjectEventSummary(ObjectsEventSummary):
    def _getObs(self):
        return [self]


def _getPillSortKey(pill,
    _severities = ('critical', 'error', 'warning'),
    _getseverity = re.compile(r'<td class="severity-icon-small\s+(' +
                              r'critical|error|warning' +
                              r') "\s+title="(\d+) out of (\d+) acknowledged">', 
                           re.S|re.I|re.M).search
    ):
    """
    Internal method for converting pill class to an integer severity sort key.
    Use default arguments _getseverity and _severities to store runtime constants.
    """
    try:
        reMatch = _getseverity(pill.lower())
        if reMatch:
            sev, numacked, numtotal = reMatch.group(1, 2, 3)
            index = _severities.index(sev)
            index += 0.5 if numacked != '0' else 0
            return (index, -int(numtotal))
    except Exception:
        pass
        
    return (5,0)

def getObjectsEventSummary(zem, objects, prodState=None, REQUEST=None):
    """
    Return an HTML link and event pill for each object passed as a JSON
    object ready for inclusion in a YUI data table.

    @param objects: The objects for which to create links and pills.
    @type objects: list
    @return: dict containing 'columns' and 'data' entries
    @rtype: dict
    """
    ret = {'columns':['Object', 'Events'], 'data':[]}

    zep = Zuul.getFacade('zep')

    uuids = [ obj.getUUID() for obj in objects ]

    sevs = (SEVERITY_CRITICAL,SEVERITY_ERROR,SEVERITY_WARNING,SEVERITY_INFO,SEVERITY_DEBUG)
    all_severities = zep.getEventSeveritiesByUuids(uuids, severities=sevs)
    severities_per_uuid = {}
    for uuid, severities in all_severities.iteritems():
        severities_per_uuid[uuid] = dict((zep.getSeverityName(sev).lower(), counts) for (sev, counts) in severities.iteritems())

    # build list of device-pill-pillsortkey tuples
    devdata = []
    for obj in objects:
        alink = obj.getPrettyLink()
        uuid = obj.getUUID()
        obj_severities = severities_per_uuid[uuid]
        pill = getEventPillME(obj, showGreen=True, prodState=prodState, severities=obj_severities)
        if isinstance(pill, (list, tuple)): pill = pill[0]
        devdata.append((alink, pill, _getPillSortKey(pill)))
    devdata.sort(key=lambda x:x[-1])

    # save object-pill data to return dict
    ret['data'] = [{'Object':x[0],'Events':x[1]} for x in devdata]

    return ret


def getDashboardObjectsEventSummary(zem, objects, REQUEST=None):
    """
    Event summary that takes dashboard production state threshold into account.
    """
    thold = zem.dmd.prodStateDashboardThresh
    return getObjectsEventSummary(zem, objects, thold, REQUEST)


def _getPill(summary, url=None, number=3):
    iconTemplate = """
        <td class="severity-icon-small
            %(severity)s %(cssclass)s"
            title="%(upper_severity)s: %(acked)s out of %(total)s events acknowledged">
            %(total)s
        </td>
    """
    rainbowTemplate = """
    <table onclick="location.href='%(url)s';"
        class="eventrainbow eventrainbow_cols_%(number)s">
        <tr>%(cells)s</tr>
    </table>
    """
    stati = ('critical','error','warning','info','debug')
    summary = [summary[x] for x in stati]

    cells = []
    for i, counts in enumerate(summary[:number]):
        total = counts['count']
        acked = counts['acknowledged_count']
        cssclass = 'no-events' if not total else 'acked-events' if total==acked else ''
        cells.append(iconTemplate % {
            'cssclass': cssclass,
            'severity': stati[i],
            'upper_severity': stati[i].upper(),
            'total': total,
            'acked': acked
        })
    return rainbowTemplate % {
        'url': url,
        'cells': ''.join(cells),
        'number': number
    }

def getEventPillME(me, number=3, minSeverity=0, showGreen=True,
                   prodState=None, severities=None):
    """
    Get HTML code displaying the maximum event severity and the number of
    events of that severity on a particular L{ManagedEntity} in a pleasing
    pill-shaped container. Optionally return pills for lesser severities as
    well. Optionally return a green pill if there are no events (normally no
    events in a severity will not yield a result).

    @param me: The object regarding which event data should be queried.
    @type me: L{ManagedEntity}
    @param number: The number of pills to return
    @type number: int
    @param showGreen: Whether to return an empty green pill if all is well
    @type showGreen: bool
    @return: HTML strings ready for template inclusion
    @rtype: list
    @param severities: The severity counts that you can pass in if
    you do not want the getEventSeveritiesCount to be called. This is useful
    for batch pills queries
    @param type: dictionary
    """
    url = getEventsURL(me)
    sevs = severities
    if not severities:
        sevs = me.getEventSeveritiesCount()
    return _getPill(sevs, url, number)


organizerTypes = {
    'Devices': 'devices',
    'Groups': 'groups',
    'Locations': 'locs',
    'Systems': 'systemsTree'
}


def getEventsURL(me) :
    from Products.ZenModel.Device import Device
    if isinstance(me, DeviceOrganizer) :
        path = me.getPrimaryPath()
        url = ('/zport/dmd/itinfrastructure?filter=default#'
               '%s:%s:events_grid' % (
                   organizerTypes[path[3]], '.'.join(path)))
    elif isinstance(me, Device) :
        url = (me.getPrimaryUrlPath() +
               '/devicedetail?filter=default#'
               'deviceDetailNav:device_events')
    else:
        url = me.getPrimaryUrlPath()+'/viewEvents?filter=default'
    return url
