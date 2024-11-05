##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""FakeComponents

Create an arbitrary number of components via configuration file
($ZENHOME/etc/FakeComponent.conf)

File format
==============

[section1]
compname = os
relname = interfaces
modname = Products.ZenModel.IpInterface
count = 1000
idTemplate = eth%(counter)s
attributes = { }

Notes
=======
* The section names are ignored
* All fields are required except for compname and attributes
"""

from ConfigParser import RawConfigParser

from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.ZenUtils.path import zenPath


class MissingModelerPluginSectionArgument(Exception):
    pass


class FakeComponents(PythonPlugin):
    configFile = zenPath("etc/FakeComponent.conf")

    def collect(self, device, log):
        settings = RawConfigParser()
        settings.read(self.configFile)
        return settings

    def process(self, device, settings, log):
        log.info(
            "Modeler %s processing data for device %s", self.name(), device.id
        )
        rmList = []
        for section in settings.sections():
            try:
                rm = self.addComponentSection(settings, section, log)
                rmList.append(rm)
            except MissingModelerPluginSectionArgument as ex:
                log.warn(ex)
        return rmList

    def addComponentSection(self, settings, section, log):
        """
        Add components from a section of the modeler config file.

        Raises exception if arguments are missing.
        """
        self.hasRequiredArg(settings, section, "count")
        self.hasRequiredArg(settings, section, "idTemplate")
        self.hasRequiredArg(settings, section, "relname")
        self.hasRequiredArg(settings, section, "modname")

        count = settings.getint(section, "count")
        idTemplate = settings.get(section, "idTemplate")
        compname, relname, modname = self.getComponentTypeInfo(
            settings, section, log
        )

        rm = self.relMap()
        rm.compname = compname
        rm.relname = relname
        for i in xrange(count):
            attributes = self.getAttributes(i, settings, section, log)
            om = self.createComponent(
                i, idTemplate, settings, attributes, compname, modname
            )
            if om is not None:
                rm.append(om)

        return rm

    def hasRequiredArg(self, settings, section, argname):
        """
        Raise an exception if a required argument is missing
        """
        if not settings.has_option(section, argname):
            msg = "Section %s is missing the '%s' argument -- skipping" % (
                section,
                argname,
            )
            raise MissingModelerPluginSectionArgument(msg)

    def getComponentTypeInfo(self, settings, section, log):
        """
        Grab the component meta-data information
        """
        compname, relname, modname = "", "", ""
        if settings.has_option(section, "compname"):
            compname = settings.get(section, "compname")
        relname = settings.get(section, "relname")
        modname = settings.get(section, "modname")
        return compname, relname, modname

    def getAttributes(self, current, settings, section, log):
        """
        eval() the 'attributes' argument, if any
        """
        attributes = {}
        if not settings.has_option(section, "attributes"):
            return attributes
        attributesTemplate = settings.get(section, "attributes")
        try:
            attributes = attributesTemplate % {"counter": current}
            attributes = eval(attributes)
            if not attributes:
                attributes = {}
        except Exception:
            log.warn(
                "Unable to parse section '%s' attributes entry: %s",
                section,
                attributes,
            )
            attributes = {}
        return attributes

    def createComponent(
        self,
        current,
        idTemplate,
        settings,
        attributes,
        compname=None,
        modname=None,
    ):
        """
        Create an object map (om) from the definition
        """
        om = self.objectMap(attributes)
        om.id = idTemplate % {"counter": current}
        if compname:
            om.compname = compname
        om.modname = modname
        return om
