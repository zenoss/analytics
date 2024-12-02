##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import re

from pprint import pformat

from Products.ZenUtils.Utils import prepId as globalPrepId

from .CommandParser import CommandParser

log = logging.getLogger("zen.ComponentCommandParser")

# A 'dp' proxy object from the COMMAND zenhub service CommandPerformanceConfig
# contains:
#
# id                   - name of the datapoint
# component            - name of the component
# rrdPath              - path to filename
# rrdType              - eg GAUGE, DERIVE
# rrdCreateCommand     - how to create the RRD file if there isn't one
# rrdMin               - min value
# rrdMax               - max value
# data                 - result of parser.dataForParser(comp, dp)


class ComponentCommandParser(CommandParser):

    # This default equates a 'part' of the output as being a line.
    # In other words, assume one line has data about one component.
    componentSplit = "\n"

    # This item helps to find the component name in a 'part' (ie a line)
    # This MUST contain a regex which has a regex item called 'component'.
    #
    # eg     componentScanner = '% (?P<component>/.*)'
    #
    # The above says that a component entry starts with a '%'
    componentScanner = ""

    # Once we've found a part that contains component data, a scanner
    # regex is used to match the part and return the name of the datapoint
    # to which the value should be stored.
    #
    # Scanners are regexes with regex search matches. eg
    #   r' (?P<totalBlocks>\d+) +(?P<usedBlocks>\d+) '
    scanners = ()

    # What is the attribute of the component that matches the name from the
    # command? This will be used in the zenhub service to grab the attribute
    # value.
    #
    # If this is 'id', then run prepId on the command output to match the
    # name in ZODB. Otherwise, the component name is assumed to not require
    # cleaning. Components with non-HTML friendly bits in them (eg ':?%/')
    # will need to be cleaned.  Examples are things like filesystems.
    componentScanValue = "id"

    def prepId(self, id, subchar="_"):
        return globalPrepId(id, subchar)

    def dataForParser(self, context, dp):
        # This runs in the zenhub service,
        # so it has access to the actual ZODB object.
        return dict(
            componentScanValue=getattr(context, self.componentScanValue)
        )

    def processResults(self, cmd, result):

        # Use the data from our proxy object to create a mapping from
        # the component name to datapoints.
        ifs = {}
        for dp in cmd.points:
            dp.component = dp.data["componentScanValue"]
            points = ifs.setdefault(dp.component, {})
            points[dp.id] = dp

        # Split command output into parts (typically lines)
        parts = cmd.result.output.split(self.componentSplit)

        for part in parts:
            # Does this part (eg line) contain a component or not?
            match = re.search(self.componentScanner, part)
            if not match:
                continue

            # Search for the componentScanner regex 'component' item
            component = match.groupdict()["component"].strip()
            if self.componentScanValue == "id":
                component = self.prepId(component)

            points = ifs.get(component, None)
            if not points:
                continue

            self.getMetrics(result, points, part)

        log.debug(pformat(result))
        return result

    def getMetrics(self, result, points, part):
        # Use the scanners to search for datapoints
        for search in self.scanners:
            match = re.search(search, part)
            if match:
                for name, value in match.groupdict().items():
                    dp = points.get(name, None)
                    if dp is not None:
                        if value in ("-", ""):
                            value = 0
                        result.values.append((dp, float(value)))
