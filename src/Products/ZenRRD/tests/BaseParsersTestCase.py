##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

import os

from pprint import pformat

from Products.ZenRRD.CommandParser import ParsedResults
from Products.ZenTestCase.BaseTestCase import BaseTestCase


class Object(object):
    def __repr__(self):
        return pformat(
            dict(
                [
                    (attr, getattr(self, attr))
                    for attr in dir(self)
                    if not attr.startswith("__")
                ]
            )
        )


def createSimplePoints(expected):
    """
    Create data points for a CommandParser from a mapping of expected
    values.  These points are simple datapoints on the device,
    not a subcomponent.
    """
    points = []

    for key, value in expected.items():
        point = Object()
        point.id = key
        point.expected = value
        points.append(point)
    return points


class Context(object):
    """
    A fake context object for CommandParser.dataForParser() calls.  Pass in a
    key to the initializer and access to any attribute on this object will
    return that key.
    """

    def __init__(self, key):
        self.key = key

    def __getattr__(self, name):
        return self.key


def createPoints(expected, parser):
    """
    Create data points for a ComponentCommandParser from a mapping of expected
    values.
    """
    if not isinstance(expected.values()[0], dict):
        return createSimplePoints(expected)

    points = []

    for key in expected:

        for id in expected[key]:
            point = Object()
            point.id = id
            point.data = parser.dataForParser(Context(key), None)
            point.expected = expected[key][id]
            points.append(point)

    return points


def filenames(datadir):
    """recursively find and yield data-file filenames starting at datadir"""

    for root, subFolders, files in os.walk(datadir):

        if root.find(".svn") == -1:

            for entry in files:

                if (
                    not entry.startswith(".")
                    and not entry.endswith(".py")
                    and not entry.endswith(".pyc")
                    and entry.find("~") == -1
                    and entry.find("#") == -1
                ):

                    yield os.path.join(root, entry)


class BaseParsersTestCase(BaseTestCase):
    def _testParser(self, parserMap, filename):

        # read the data file
        datafile = open(filename)
        command = datafile.readline().rstrip("\n")
        output = "".join(datafile.readlines())
        datafile.close()

        # read the file containing the expected values
        expectedfile = open("%s.py" % (filename,))
        expected = eval("".join(expectedfile.readlines()))
        expectedfile.close()

        results = ParsedResults()
        Parser = parserMap.get(command)

        if Parser:
            parser = Parser()
        else:
            self.fail("No parser for %s" % command)

        cmd = Object()
        cmd.points = createPoints(expected, parser)
        cmd.result = Object()
        cmd.result.output = output

        parser.processResults(cmd, results)

        self.assertEqual(
            len(cmd.points),
            len(results.values),
            "%s expected %s values, actual %s"
            % (filename, len(cmd.points), len(results.values)),
        )

        counter = 0

        for expected, actual in results.values:
            expectedValue = expected.expected
            msg = "%s: %s expected %s but parsed out %s" % (
                filename,
                expected.id,
                expectedValue,
                actual,
            )
            self.assertEqual(expectedValue, actual, msg)
            counter += 1

        return counter

    def _testParsers(self, datadir, parserMap):
        """
        Test all of the parsers that have test data files in the data
        directory.
        """
        counter = 0

        for filename in filenames(datadir):
            counter += self._testParser(parserMap, filename)

        self.assert_(counter > 0, counter)
        print("testParsers made", counter, "assertions.")
