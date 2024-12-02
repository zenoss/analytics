##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""AliasPlugin

In order to more easily create reports, there is now a base class (AliasPlugin)
that plugins can subclass and provide minimal information.  The plugin is
meant to be run from an rpt file.
"""

import logging

import transaction

from Products.ZenModel.RRDDataPoint import getDataPointsByAliases
from Products.ZenReports import Utils, Utilization
from Products.ZenUtils.ZenTales import talesEval, InvalidTalesException

log = logging.getLogger("zen.reports")


class Column(object):
    """
    Represents a column in a report row.  Returns a value when given the
    context represented by the row.  For example, a brain-dead report
    might list the paths of all the devices in the system.  A Column object
    that represents the path column would know how to return the path given
    the device.
    """

    def __init__(self, columnName, columnHandler=None):
        """
        @param columnName: the name of the column
        @param columnHandler: optional object or method that knows
                              how to take the row context and return
                              the column value
        """
        self._columnName = columnName
        self._columnHandler = columnHandler

    def getColumnName(self):
        return self._columnName

    def getValue(self, device, component=None, extra=None):
        """
        @param device: the device represented by this row
        @param component: the component represented by this row (if present)
        @param extra: extra context passed to the columnHandler that will
                      generate the column value
        """
        value = None
        if self._columnHandler is not None:
            value = self._columnHandler(device, component, extra)
        return value

    def getAliasName(self):
        """
        @return the alias that this column uses (if any)
        """
        # This ugly type-check is needed for performance.  We
        # gather up aliases so we can get all the necessary datapoints
        # at one time.
        return getattr(self._columnHandler, "aliasName", None)


def _fetchValueWithAlias(entity, datapoint, alias, summary):
    """
    Generates the alias RPN formula with the entity as the context, then
    retrieves the RRD value of the datapoint with the RPN formula
    """
    if alias:
        summary["extraRpn"] = alias.evaluate(entity)
    return entity.getRRDValue(datapoint.id, **summary)


class RRDColumnHandler(object):
    """
    A handler that return RRD data for the value given the row context.
    """

    def __init__(self, aliasName):
        """
        @param aliasName: the alias or datapoint name to fetch
        @param columnHandler: optional columnHandler method or object for
            post-processing of the RRD data
        """
        self.aliasName = aliasName

    def __call__(self, device, component=None, extra=None):
        """
        @param device: the device represented by this row
        @param component: the component represented by this row (if present)
        @param extra: extra context passed to the columnHandler that will
            generate the column value
        """
        # The summary dict has the request key/values
        summary = extra["summary"]

        # The aliasDatapointPairs are the datapoints that
        # have the desired values along with the aliases
        # that may have formulas for transforming them
        aliasDatapointPairs = extra["aliasDatapointPairs"]
        if aliasDatapointPairs is None or len(aliasDatapointPairs) == 0:
            return None

        value = None
        # determine the row context-- device or device and component
        perfObject = component or device
        deviceTemplates = perfObject.getRRDTemplates()
        for alias, datapoint in aliasDatapointPairs:
            template = datapoint.datasource().rrdTemplate()

            # Only fetch the value if the template is bound
            # to this device or component
            if template in deviceTemplates:
                value = _fetchValueWithAlias(
                    perfObject, datapoint, alias, summary
                )

            # Return the first value we find
            if value is not None:
                break

        return value


class PythonColumnHandler(object):
    """
    A column handler accepts row context (like a device, component, or extra
    information) and returns the column value.  This class specifically
    executes a python expression that can use the row context.

    The row context includes the device object ('device') and, if available,
    the component object ('component').  It also includes report information
    such as the start date ('start') and end date ('end') of the report.
    """

    def __init__(self, talesExpression, extraContext={}):
        """
        @param talesExpression: A python expression that can use the context
        """
        self._talesExpression = "python:%s" % talesExpression
        self._extraContext = extraContext

    def __call__(self, device, component=None, extra=None, value=None):
        kw = dict(device=device, component=component, value=value)
        kw.update(self._extraContext)
        if extra is not None:
            kw.update(extra)
        value = None
        try:
            value = talesEval(self._talesExpression, device, kw)
        except InvalidTalesException as e:
            log.info(e)
        return value


class AliasPlugin(object):
    """
    A base class for performance report plugins that use aliases to
    choose datapoints
    """

    def _getComponents(self, device, componentPath):
        componentPath = "here/%s" % componentPath
        try:
            return talesEval(componentPath, device)
        except AttributeError:
            return []

    def getColumns(self):
        """
        Return the mapping of aliases to column names.  This should be one
        to one.  This is unimplemented in the base class.

        This is meant to be overridden.
        """
        raise Exception(
            "Unimplemented: Only subclasses of AliasPlugin "
            "should be instantiated directly"
        )

    def getCompositeColumns(self):
        """
        Return columns that will be evaluated in order and have access to
        the previous column values.  TalesColumnHandlers will have the previous
        column values for this row in their context.

        For example, if one column named 'cpuIdle' evaluates to .36,
        a composite column named 'cpuUtilized' can be created with
        a TalesColumnHandler with the expression '1 - cpuIdle'.

        NOTE: These cannot be RRD columns (or rather, RRD columns will fail
              because no datapoints will be passed to them)

        This is meant to be overridden (if needed).
        """
        return []

    def getComponentPath(self):
        """
        If the rows in the report represent components, this is how to
        get from a device to the appropriate components.

        This is meant to be overridden for component reports.
        """
        return None

    def _createRecord(
        self,
        device,
        component=None,
        columnDatapointsMap={},
        summary={},
        templateArgs=None,
    ):
        """
        Creates a record for the given row context
        (that is, the device and/or component)

        @param device: the device for this row
        @param component: the (optional) component for this row
        @param columnDatapointsMap: a dict of Column objects to
                                    alias-datapoint pairs.  The first
                                    datapoint that gives a value for
                                    the context will be used.
        @param summary: a dict of report parameters like start date,
                        end date, and rrd summary function
        @param templateArgs the template tags from the ui

        @rtype L{Utils.Record}
        """

        def localGetValue(device, component, extra):
            try:
                return column.getValue(device, component, extra=extra)
            except (TypeError, NameError):
                return None

        columnValueMap = {}
        for column, aliasDatapointPairs in columnDatapointsMap.iteritems():
            columnName = column.getColumnName()
            extra = dict(
                aliasDatapointPairs=aliasDatapointPairs,
                summary=summary,
                templateArgs=templateArgs,
            )
            value = localGetValue(device, component, extra)
            columnValueMap[columnName] = value

        # The composite columns cannot be RRD columns, because we do
        # not pass datapoints.
        extra = dict(summary=summary)
        extra.update(columnValueMap)
        for column in self.getCompositeColumns():
            columnName = column.getColumnName()
            value = localGetValue(device, component, extra)
            columnValueMap[columnName] = value
            extra.update({columnName: value})

        return Utils.Record(
            device=device, component=component, **columnValueMap
        )

    def _mapColumnsToDatapoints(self, dmd):
        """
        Create a map of columns->alias/datapoint pairs.  For each
        column we need both the datapoint/alias-- the datapoint to
        retrieve the rrd data and the alias to execute the alias
        formula to transform that data (to get the correct units).

        Non-perf columns will be mapped to None
        """

        def getAliasName(column):
            return column.getAliasName()

        # First, split the columns into perf and non-perf columns
        columns = self.getColumns()
        aliasColumns = filter(lambda x: getAliasName(x) is not None, columns)

        columnDatapointsMap = {}

        # Map columns to empty list to ensure that there are placeholders
        # for all columns even if there are not aliased datapoints.
        for column in columns:
            columnDatapointsMap[column] = []

        # Fourth, match up the columns with the corresponding alias/datapoint
        # pairs
        for column in aliasColumns:
            columnDatapointsMap[column] = list(
                getDataPointsByAliases(dmd, [column.getAliasName()])
            )

        return columnDatapointsMap

    def run(self, dmd, args, templateArgs=None):
        """
        Generate the report using the columns and aliases

        @param dmd the dmd context to access the context objects
        @param args the report args from the ui
        @param templateArgs the template tags from the ui

        @rtype a list of L{Utils.Record}s
        """
        i = 0
        # Get the summary arguments from the request args
        summary = Utilization.getSummaryArgs(dmd, args)

        # Create a dict of column to the datapoint/alias pairs
        # that return a value for the column
        columnDatapointsMap = self._mapColumnsToDatapoints(dmd)

        # Don't run against all devices, which kills large systems
        if not args.get("generate") or args.get("deviceClass", "/") == "/":
            return []

        # Filter the device list down according to the
        # values from the filter widget
        componentPath = self.getComponentPath()
        report = []
        for device in Utilization.filteredDevices(dmd, args):
            i += 1
            if i % 100 == 0:
                transaction.abort()
            if componentPath is None:
                record = self._createRecord(
                    device, None, columnDatapointsMap, summary, templateArgs
                )
                report.append(record)
            else:
                components = self._getComponents(device, componentPath)
                for component in components:
                    i += 1
                    if i % 100 == 0:
                        transaction.abort()
                    record = self._createRecord(
                        device,
                        component,
                        columnDatapointsMap,
                        summary,
                        templateArgs,
                    )
                    report.append(record)
        return report
