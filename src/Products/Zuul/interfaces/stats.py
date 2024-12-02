##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Attribute, Interface

class ISystemMetric(Interface):
    category = Attribute("Category of the system static, eg Zope")

    def metrics():
        """
        A dictionary of metrics. A metric is either a number or a dict with a
        "value" key.
        """

class IMonitorScript(Interface):
    """
    IMonitorScript describes a script that performs a self monitoring script.

    Scripts that run under this interfaces should produce output like the 
    following:

        datapoint_name unix_timestamp value tag1=value1,tag2=value2

    The script [cmd] will be executed at the given collection interval unless the
    daemon flag is set. If the flag is set, the script is assumed to be long
    lived and will emit data like that above on a periodic basis.
    """
    cmd = Attribute("Command line to execute the script.")
    collectionInterval = Attribute("Number of seconds between collections.")
    name = Attribute("Datasource name")
    location = Attribute("comma separated list of contexts this script "
        "should run in: master, hub, collector.")
    daemon = Attribute("Is this a long running script?")
    testcmd = Attribute("Is this script initially viable?")
