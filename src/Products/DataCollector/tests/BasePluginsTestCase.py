##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009-2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

import logging
import os

from Products.DataCollector.plugins.DataMaps import (
    MultiArgs,
    ObjectMap,
    RelationshipMap,
)
from Products.ZenRRD.tests.BaseParsersTestCase import Object, filenames
from Products.ZenTestCase.BaseTestCase import BaseTestCase

log = logging.getLogger("zen.BasePluginsTestCase")


class BasePluginsTestCase(BaseTestCase):
    def _testDataFiles(self, datadir, Plugins, device=None):
        """
        Run tests for all of the data files in the data directory.
        """
        counter = 0

        for filename in filenames(datadir):
            try:
                counter += self._testDataFile(filename, Plugins, device)
            except Exception as e:
                format = "%s/%s caught %s: %s"
                host, parser = filename.split(os.path.sep)[-2:]
                args = (host, parser, e.__class__.__name__, str(e))
                log.error(format % args)
                raise

        if counter:
            print(self.__class__.__name__, "made", counter, "assertions.")
        else:
            print(
                self.__class__.__name__, "had no counters or failed to parse."
            )

    def __parseCommandAndOutput(self, filename, singleLine=True):
        """
        Parse out the command that was used to generate the output included
        in the file.
        """
        datafile = open(filename)
        line = datafile.readline()
        command = ""
        if not singleLine:
            log.debug(
                "failed to find plugin on first go around, trying 2nd time"
            )
            while line != "___HOST_OUTPUT___\n" and line != "":
                command += line
                line = datafile.readline()
        else:
            command = line
        command = command.rstrip("\n")
        output = "".join(datafile.readlines())
        datafile.close()
        return command, output

    def _testDataFile(self, filename, Plugins, device=None):
        """
        Test a data file.
        """
        command, output = self.__parseCommandAndOutput(filename)

        # read the file containing the expected values
        expectedfile = open("%s.py" % (filename,))
        expected = eval("".join(expectedfile.readlines()))
        expectedfile.close()

        def cleaner(command):
            return " ".join(command.split())

        command = cleaner(command)
        plugins = [
            P()
            for P in Plugins
            if cleaner(P.command) == command and P.__name__ in expected
        ]

        if not plugins:
            # If we fail to find a plugin the first time we might be dealing
            # with a multiline command, let's try to re-parse the datafile
            # once more.
            command, output = self.__parseCommandAndOutput(
                filename, singleLine=False
            )
            command = cleaner(command)
            plugins = [
                P()
                for P in Plugins
                if cleaner(P.command) == command and P.__name__ in expected
            ]
        if not plugins:
            self.fail("No plugins for %s" % command)

        device = device or Object()
        device.id = filename.split(os.path.sep)[-2]

        expecteds = [expected[p.__class__.__name__] for p in plugins]
        dataMaps = [p.process(device, output, logging) or [] for p in plugins]
        return self._testDataMaps(zip(expecteds, dataMaps), filename)

    def _testDataMaps(self, expectedActuals, filename):
        """
        Test the DataMaps contained in the expectedActuals list.
        """

        counter = 0
        for expected, actual in expectedActuals:

            if isinstance(expected, list):

                for exp, act in zip(expected, actual):
                    counter += self._testDataMap(exp, act, filename)

            else:

                counter += self._testDataMap(expected, actual, filename)

        return counter

    def _testDataMap(self, expected, actual, filename):
        """
        Test the DataMap returned by a plugin.
        """

        counter = 0

        if isinstance(actual, RelationshipMap):
            counter += self._testRelationshipMap(expected, actual, filename)
        elif isinstance(actual, ObjectMap):
            counter += self._testObjectMap(expected, actual, filename)
        elif isinstance(actual, list):
            for exp, act in zip(expected, actual):
                counter += self._testDataMap(exp, act, filename)
        else:
            self.fail("Data map type %s not supported." % (type(actual),))

        return counter

    def _testRelationshipMap(self, expected, relationshipMap, filename):
        """
        Check all of the objectMaps found in the provided relationshipMaps
        maps attribute.
        """
        counter = 0

        # all ObjectMaps have an id except for OSProcess which uses procName
        objectMapDct = {}
        for objectMap in relationshipMap.maps:
            if objectMap.modname == "Products.ZenModel.OSProcess":
                keyName = "procName"
            else:
                keyName = "id"
            objectMapDct[getattr(objectMap, keyName)] = objectMap

        for id in expected:
            if id in objectMapDct:
                counter += self._testObjectMap(
                    expected[id], objectMapDct[id], filename
                )
            else:
                plugin = os.path.sep.join(filename.split(os.path.sep)[-3:])
                self.fail(
                    "No ObjectMap with id=%s in the RelationshipMap "
                    "returned by the plugin (%s).\n%s"
                    % (id, plugin, relationshipMap)
                )

        return counter

    def _testObjectMap(self, expectedDct, actualObjMap, filename):
        """
        Check the expected values against those in the actual ObjectMap that
        was returned by the plugin.
        """
        counter = 0
        for key in expectedDct:

            if hasattr(actualObjMap, key):

                actual = getattr(actualObjMap, key)

                if isinstance(actual, MultiArgs):
                    actual = actual.args

                if isinstance(actual, str):
                    format = "'%s' != '%s' in %s"
                else:
                    format = "%s != %s in %s"

                testPath = os.path.join(*filename.split(os.path.sep)[-2:])
                msg = format % (expectedDct[key], actual, testPath)
                self.assertEqual(expectedDct[key], actual, msg)
                counter += 1

            else:

                self.fail(
                    "ObjectMap %s does not have a %s attribute."
                    % (actualObjMap, key)
                )

        return counter
