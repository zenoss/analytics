##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenRRD.CommandParser import CommandParser, ParsedResults
from Products.ZenRRD.parsers.Cacti import Cacti
from Products.ZenRRD.parsers.Nagios import Nagios


class Auto(CommandParser):
    def processResults(self, cmd, result):

        # best effort.  Try Nagios first, if that doesn't return data values
        # try Cacti. If cacti doesn't return value use results from nagios
        # since it is more likely to have been an error parsing nagios data
        # and the nagios parser puts more data in the event.  Both parsers
        # have the same logic for event severity based on exit code

        cactiResult = None
        nagiosResult = ParsedResults()

        nagiosParser = Nagios()
        nagiosParser.processResults(cmd, nagiosResult)

        if not nagiosResult.values:
            cactiParser = Cacti()
            cactiResult = ParsedResults()
            cactiParser.processResults(cmd, cactiResult)

        if cactiResult and cactiResult.values:
            # use cacti results
            parserResult = cactiResult
        else:
            parserResult = nagiosResult

        result.events.extend(parserResult.events)
        result.values.extend(parserResult.values)
