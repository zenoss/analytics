##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.Zuul.interfaces import IFacade

class IZepFacade(IFacade):
#    def fields(context=None):
#        """
#        Get the result fields appropriate for the context.
#
#        @param context: An object that can have events. Defaults to dmd.Events.
#        @type context: Products.ZenModel.EventView.EventView
#        @return: List of strings identifying columns in SQL
#        @rtype: list
#        """

    def getEventSummaries(offset, limit, keys, sort, filter={}):
        """
        Query the events database for a set of events.

        @param limit: Integer denoting the maximum number of records to
                      return
        @type limit: int
        @param start: The index of the first record to return
        @type start: int
        @param sort: The column by which to sort the results
        @type sort: str
        @param dir: Direction to sort, either ASC or DESC
        @type dir: str
        @param filters: Values for which to create filters (e.g.,
                        {'device':'^loc.*$', 'severity':[4, 5]})
        @type filters: dict or JSON str representing dict

        @return A dictionary containing the total number of matching records
                and a list of L{Products.ZenEvents.ZEvent.ZEvent} objects
        @rtype dict
        """

    def getEventSummariesGenerator(filter={}, exclude={}, sort=None):
        """
        Query the events database for a set of events.
        """

#    def create(summary, severity, device=None, component=None, **kwargs):
#        """
#        Create an event.
#
#        @param summary: The summary of the event to be created. Required.
#        @type summary: str
#        @param severity: Severity of the event to be created. Required.
#        @type severity: int : -1 <= severity <= 5
#        @param device: Name of the device with which the event should be
#                       associated. Either device or component must be specified.
#        @type device: str
#        @param component: Name of the component with which the event should be
#                          associated. Either device or component must be
#                          specified.
#        @type component: str
#
#        Arbitrary keyword arguments will be added to the event as well; the
#        schema may change, so these parameters will not be defined explicitly.
#        @return: Dictionary containing success parameter and event ID of
#                 created event, if applicable
#        @rtype: dict
#        """
#
#    def acknowledge(filter={}):
#        """
#        Acknowledge one or more events matching filter.
#        """
#
#    def unacknowledge(evids=None, excludeIds=None, selectState=None, sort=None,
#                    dir=None, filters=None, asof=None, context=None,
#                    history=False):
#        """
#        Unacknowledge one or more events.
#
#        @param evids: Event IDs of events to unacknowledge. Either evids or
#                      ranges must be specified; if both are specified, matching
#                      event IDs in the ranges will be merged with evids.
#        @type evids: list
#        @param excludeIds: Ids of events that specifically should not be included
#        @type: list
#        @param selectState: state of events to Unacknowledge ("All", "New",
#        "Acknowledged", "Suppressed")
#        @type: string
#        @param sort: The column by which to sort the records
#        @type sort: str
#        @param dir: Direction to sort, either ASC or DESC
#        @type dir: str
#        @param filters: Values for which to create filters (e.g.,
#                        {'device':'^loc.*$', 'severity':[4, 5]})
#        @type filters: dict or JSON str representing dict
#        @param asof: Last time as of which ranges were accurate
#        @type asof: float
#        """
#
#    def reopen(evids=None, excludeIds=None, selectState=None, sort=None,
#                    dir=None, filters=None, asof=None, context=None,
#                    history=False):
#        """
#        Reopen one or more events.
#
#        @param evids: Event IDs of events to reopen. Either evids or ranges
#                      must be specified; if both are specified, matching event
#                      IDs in the ranges will be merged with evids.
#        @type evids: list
#        @param excludeIds: Ids of events that specifically should not be included
#        @type: list
#        @param selectState: state of events to reopen ("All", "New",
#        "Acknowledged", "Suppressed")
#        @type: string
#        @param sort: The column by which to sort the records
#        @type sort: str
#        @param dir: Direction to sort, either ASC or DESC
#        @type dir: str
#        @param filters: Values for which to create filters (e.g.,
#                        {'device':'^loc.*$', 'severity':[4, 5]})
#        @type filters: dict or JSON str representing dict
#        @param asof: Last time as of which ranges were accurate
#        @type asof: float
#        """
#
#    def close(evids=None, excludeIds=None, selectState=None, sort=None,
#                    dir=None, filters=None, asof=None, context=None,
#                    history=False):
#        """
#        Close one or more events.
#
#        @param evids: Event IDs of events to close. Either evids or ranges
#                      must be specified; if both are specified, matching event
#                      IDs in the ranges will be merged with evids.
#        @type evids: list
#        @param excludeIds: Ids of events that specifically should not be included
#        @type: list
#        @param selectState: state of events to close ("All", "New",
#        "Acknowledged", "Suppressed")
#        @type: string
#        @param sort: The column by which to sort the records
#        @type sort: str
#        @param dir: Direction to sort, either ASC or DESC
#        @type dir: str
#        @param filters: Values for which to create filters (e.g.,
#                        {'device':'^loc.*$', 'severity':[4, 5]})
#        @type filters: dict or JSON str representing dict
#        @param asof: Last time as of which ranges were accurate
#        @type asof: float
#        """
#
#    def detail(evid, history=False):
#        """
#        Get the event detail for an event.
#
#        @param evid: The event ID for which to fetch the detail
#        @type evid: str
#        @param history: Whether we should look on the history table
#        @type history: bool
#        """
#
#    def log(evid, message, history=False):
#        """
#        Add a log message to an event.
#
#        @param evid: The event ID for which to add a log message
#        @type evid: str
#        @param message: Body of the log message.
#        @type message: str
#        @param history: Whether we should look on the history table
#        @type history: bool
#        """
