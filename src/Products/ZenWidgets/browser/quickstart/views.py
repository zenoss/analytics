##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import cgi
import logging
import re

from Acquisition import aq_base
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile

from Products.ZenMessaging.audit import audit
from Products.ZenModel.IpNetwork import AutoDiscoveryJob
from Products.ZenUtils import Ext
from Products.ZenUtils.jsonutils import json

from ...messaging import IMessageSender

log = logging.getLogger("zen.quickstart")


def _is_network(x):
    return bool(re.compile(r"^(\d+\.){3}\d+\/\d+$").search(x))


def _is_range(x):
    return bool(re.compile(r"^(\d+\.){3}\d+\-\d+$").search(x))


class QuickstartBase(BrowserView):
    """Standard macros for the quickstart."""

    template = ZopeTwoPageTemplateFile("templates/quickstart_macros.pt")

    def __getitem__(self, key):
        return self.template.macros[key]


class OutlineView(BrowserView):
    """Displays the steps the user will soon be completing."""

    __call__ = ZopeTwoPageTemplateFile("templates/outline.pt")


class CreateUserView(BrowserView):
    """Creates the initial user and sets the admin password."""

    __call__ = ZopeTwoPageTemplateFile("templates/createuser.pt")


class DeviceAddView(BrowserView):
    """Specify devices to be added."""

    @property
    def hasLDAPInstalled(self):
        try:
            import ZenPacks.zenoss.LDAPAuthenticator  # noqa F401

            # return javascript true/false
            return "true"
        except ImportError:
            return "false"

    @json
    def default_communities(self):
        """
        Format the value of Devices.Discovered.zSnmpCommunities for a textarea
        """
        devclass = self.context.dmd.Devices.Discovered.primaryAq()
        return "\n".join(devclass.zSnmpCommunities)

    def _assemble_types_list(self):
        """
        Walks all device classes building a list of description/protocol pairs.
        """
        ALLOWED_PROTOCOLS = ("SSH", "SNMP", "WMI", "WinRM")
        devclass = self.context.dmd.Devices
        orgs = devclass.getSubOrganizers()
        types = []
        for org in orgs:
            # Skip it if it doesn't have types registered
            if not hasattr(aq_base(org), "devtypes") or not org.devtypes:
                continue
            for t in org.devtypes:
                try:
                    desc, ptcl = t
                except ValueError:
                    continue

                # Both must be defined
                if not ptcl or not desc:
                    continue

                # special case for migrating from WMI to WinRM so we
                # can allow the zenpack to be backwards compatible
                if (
                    org.getOrganizerName() == "/Server/Microsoft/Windows"
                    and ptcl == "WMI"
                ):
                    ptcl = "WinRM"
                # We only care about orgs with acceptable protocols
                if ptcl not in ALLOWED_PROTOCOLS:
                    continue
                types.append((org.getOrganizerName(), desc, ptcl))
        return types

    @json
    def collectors(self):
        return [
            [name]
            for name in self.context.dmd.Monitors.getPerformanceMonitorNames()
        ]

    @json
    def device_types(self):
        """
        Build an object for populating an Ext ComboBox representing "device
        types," which should exactly correspond to DeviceClasses in the system.

        This method iterates over a predetermined list of types we might want
        to see and checks each DeviceClass for existence (i.e., is the
        appropriate ZenPack installed?).
        """
        # Turn them into the dictionary format expected
        types = {"win": [], "ssh": [], "snmp": [], "winrm": []}
        for t in self._assemble_types_list():
            if t[2] == "WMI":
                types["win"].append(t)
            elif t[2] == "SNMP":
                types["snmp"].append(t)
            elif t[2] == "SSH":
                types["ssh"].append(t)
            elif t[2] == "WinRM":
                types["win"].append(t)

        def dev_class_exists(path):
            """
            Return a boolean indicating whether the specified DeviceClass
            exists.
            """
            try:
                self.context.unrestrictedTraverse("/zport/dmd/Devices" + path)
            except AttributeError:
                return False
            else:
                return True

        def format_type(credtype, classpath, description, protocol):
            """
            Turn information representing a device class into a dictionary of
            the format our ComboBox expects.
            """
            value = "%s_%s" % (classpath, credtype)
            return dict(
                value=value,
                shortdesc="%s (%s)" % (description, protocol),
                description=description,
                protocol=protocol,
            )

        # Iterate over all types
        response = []
        for credtype, devtypes in types.iteritems():
            for devtype in devtypes:
                # Check for existence
                if dev_class_exists(devtype[0]):
                    # Exists, so add it to the list
                    response.append(format_type(credtype, *devtype))

        # Sort alphabetically by description
        response.sort(key=lambda x: x["description"])

        # Final response needs an object under a defined root, in this case
        # "types"
        return dict(types=response)

    @Ext.form_action
    def autodiscovery(self):
        response = Ext.FormResponse()
        submitted = self.request.form.get("network", [])
        if isinstance(submitted, basestring):
            submitted = [submitted]
        zProperties = {
            "zCommandUsername": self.request.form.get("sshusername"),
            "zCommandPassword": self.request.form.get("sshpass"),
            "zWinRMUser": self.request.form.get("winusername"),
            "zWinRMPassword": self.request.form.get("winpass"),
            "zSnmpCommunities": self.request.form.get(
                "snmpcommunities"
            ).splitlines(),
        }
        collector = self.request.form.get(
            "autodiscovery_collector", "localhost"
        )
        # Split rows into networks and ranges
        nets = []
        ranges = []
        for row in submitted:
            if _is_network(row):
                nets.append(row)
            elif _is_range(row):
                ranges.append(row)
        if not nets and not ranges:
            response.error(
                "network", "You must enter at least one network or IP range."
            )
        if nets:
            for net in nets:
                # Make the network if it doesn't exist, so zendisc has
                # something to discover
                _ = self.context.dmd.Networks.createNet(net)
            try:
                netdesc = (
                    "network %s" % nets[0]
                    if len(nets) == 1
                    else "%s networks" % len(nets)
                )
                self.context.JobManager.addJob(
                    AutoDiscoveryJob,
                    description="Discover %s" % netdesc,
                    kwargs=dict(
                        nets=nets, zProperties=zProperties, collector=collector
                    ),
                )
            except Exception as e:
                log.exception(e)
                response.error(
                    "network",
                    "There was an error scheduling this job. "
                    "Please check your installation and try again.",
                )
            else:
                IMessageSender(self.context).sendToUser(
                    "Autodiscovery Task Created",
                    "Discovery of the following networks is in progress: %s"
                    % (", ".join(nets)),
                )
        if ranges:
            # Ranges can just be sent to zendisc, as they are merely sets of
            # IPs
            try:
                rangedesc = (
                    "IP range %s" % ranges[0]
                    if len(ranges) == 1
                    else "%s IP ranges" % len(ranges)
                )
                self.context.JobManager.addJob(
                    AutoDiscoveryJob,
                    description="Discover %s" % rangedesc,
                    kwargs=dict(
                        ranges=ranges,
                        zProperties=zProperties,
                        collector=collector,
                    ),
                )
            except Exception as e:
                log.exception(e)
                response.error(
                    "network",
                    "There was an error scheduling this job. "
                    "Please check your installation and try again.",
                )
            else:
                IMessageSender(self.context).sendToUser(
                    "Autodiscovery Task Created",
                    "Discovery of the following IP ranges is in progress: %s"
                    % (", ".join(ranges)),
                )

        audit(
            "UI.Device.Autodiscovery",
            networks=",".join(nets),
            ipRanges=",".join(ranges),
        )
        response.redirect("/zport/dmd")
        return response

    @Ext.form_action
    def manual(self):
        # Pull all the device name keys
        response = Ext.FormResponse()
        devs = filter(
            lambda x: x.startswith("device_"), self.request.form.keys()
        )
        # Make sure we have at least one device name
        devnames = filter(lambda x: bool(self.request.form.get(x)), devs)
        if not devnames:
            response.error(
                "device_0", "You must enter at least one hostname/IP."
            )
            return response
        # Create jobs based on info passed
        for k in devs:
            # Ignore empty device names
            if not self.request.form.get(k):
                continue
            idx = k.split("_")[1]
            devclass, type_ = self.request.form.get(
                "deviceclass_%s" % idx
            ).split("_")
            collector = self.request.form.get(
                "collector_" + str(idx), "localhost"
            )
            # Set zProps based on type
            if type_ == "ssh":
                zProps = {
                    "zCommandUsername": self.request.form.get(
                        "sshuser_%s" % idx
                    ),
                    "zCommandPassword": self.request.form.get(
                        "sshpass_%s" % idx
                    ),
                }
            elif type_ == "win":
                zProps = {
                    "zWinRMUser": self.request.form.get("winuser_%s" % idx),
                    "zWinRMPassword": self.request.form.get(
                        "winpass_%s" % idx
                    ),
                }
            elif type_ == "snmp":
                zProps = {
                    "zSnmpCommunities": self.request.form.get(
                        "snmpcomm_%s" % idx
                    ).splitlines()
                }
            deviceName = self.request.form.get(k)
            perfConf = self.context.Monitors.getPerformanceMonitor(collector)
            perfConf.addCreateDeviceJob(
                deviceName=deviceName,
                performanceMonitor=collector,
                devicePath=devclass,
                zProperties=zProps,
                discoverProto="auto",
            )
            deviceClassUid = "/Devices" + devclass
            deviceUid = "/".join([deviceClassUid, "devices", deviceName])
            audit(
                "UI.Device.Add",
                deviceUid,
                deviceClass=deviceClassUid,
                model=True,
            )
        devnames = [self.request.form.get(dev) for dev in devs]
        IMessageSender(self.context).sendToUser(
            "Devices Added",
            "Modeling of the following devices has been scheduled: %s"
            % (cgi.escape(", ".join(filter(None, devnames)))),
        )
        response.redirect("/zport/dmd")
        return response
