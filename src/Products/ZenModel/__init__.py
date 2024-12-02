##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""__init__

Initialize the Confmon Product

Products must follow the following standard
The name of the module (file) and the name of the product class inside
the file must be the same.

If there is a ZMI add screen it must be called "add" + class name (ie addDevice)and it must be defined at the module level.

the class factory must be a function at the module level called 
manage_add + class name (ie manage_addDevice)

If there is an icon for the product it should be called class name + _icon.gif
"""

import os
import logging
log = logging.getLogger("zenmodel")

if 0:
    __path__ = None                     # keep pyflakes quiet

from Products.CMFCore.DirectoryView import registerDirectory

confmon_globals = globals()

productNames = (
    'AdministrativeRole',
    'AdministrativeRoleable',
    'AreaGraphPoint',
    'BasicDataSource',
    'BasicDeviceLoader',
    'BatchDeviceLoader',
    'BuiltInDS',
    'CPU',
    'CdefGraphPoint',
    'CiscoLoader',
    'Classifier',
    'ClassifierEntry',
    'Collection',
    'CollectionItem',
    'Commandable',
    'CommentGraphPoint',
    'ComplexGraphPoint',
    'ConfigurationError',
    'ConfmonPropManager',
    'CustomDeviceReportClass',
    'DataPointGraphPoint',
    'DataRoot',
    'DefGraphPoint',
    'Device',
    'DeviceClass',
    'DeviceComponent',
    'DeviceGroup',
    'DeviceHW',
    'DeviceManagerBase',
    'DeviceOrganizer',
    'DeviceReport',
    'DeviceReportClass',
    'DeviceResultInt',
    'DmdBuilder',
    'EventView',
    'Exceptions',
    'ExpansionCard',
    'Fan',
    'FileSystem',
    'GprintGraphPoint',
    'GraphDefinition',
    'GraphGroup',
    'GraphPoint',
    'GraphReport',
    'GraphReportClass',
    'GraphReportElement',
    'HWComponent',
    'HardDisk',
    'Hardware',
    'HardwareClass',
    'HruleGraphPoint',
    'IpAddress',
    'IpInterface',
    'IpNetwork',
    'IpRouteEntry',
    'IpService',
    'IpServiceClass',
    'IpServiceLoader',
    'LineGraphPoint',
    'Link',
    'LinkManager',
    'Linkable',
    'Location',
    'Lockable',
    'MEProduct',
    'MaintenanceWindow',
    'MaintenanceWindowable',
    'ManagedEntity',
    'Manufacturer',
    'ManufacturerRoot',
    'MibBase',
    'MibModule',
    'MibNode',
    'MibNotification',
    'MibOrganizer',
    'MinMaxThreshold',
    'Monitor',
    'MonitorClass',
    'MultiGraphReport',
    'MultiGraphReportClass',
    'OSComponent',
    'OSProcess',
    'OSProcessClass',
    'OSProcessOrganizer',
    'OperatingSystem',
    'Organizer',
    'PerformanceConf',
    'PingDataSource',
    'PowerSupply',
    'PrintGraphPoint',
    'ProductClass',
    'RRDDataPoint',
    'RRDDataSource',
    'RRDGraph',
    'RRDTemplate',
    'RRDThreshold',
    'MetricMixin',
    'Report',
    'ReportClass',
    'Service',
    'ServiceClass',
    'ServiceOrganizer',
    'ShiftGraphPoint',
    'SiteError',
    'Software',
    'SoftwareClass',
    'StatusColor',
    'System',
    'TemperatureSensor',
    'TemplateContainer',
    'ThresholdClass',
    'ThresholdGraphPoint',
    'ThresholdInstance',
    'TickGraphPoint',
    'UserCommand',
    'UserSettings',
    'VdefGraphPoint',
    'VruleGraphPoint',
    'WinService',
    'XmlDataLoader',
    'ZDeviceLoader',
    'ZVersion',
    'ZenDate',
    'ZenMenu',
    'ZenMenuItem',
    'ZenMenuable',
    'ZenModelBase',
    'ZenModelItem',
    'ZenModelRM',
    'ZenPack',
    'ZenPackLoader',
    'ZenPackManager',
    'ZenPackPersistence',
    'ZenPackable',
    'ZenPacker',
    'ZenStatus',
    'ZenossInfo',
    'ZenossSecurity',
    'ZentinelPortal',
)

# Make the skins available as DirectoryViews.
registerDirectory('skins', globals())
registerDirectory('help', globals())


confmonModules = []
def loadConfmonModules():
    # import all modules
    for product in productNames:
        mod = __import__(product, globals(), locals(), [])
        confmonModules.append(mod)


def initialize(registrar):
    contentClasses = ()
    contentConstructors = ()

    registrar.registerHelp()
    registrar.registerHelpTitle('Zentinel Portal Help')

    if not confmonModules: loadConfmonModules()
    # register products with zope
    for module in confmonModules:
        args = []
        kwargs = {}
        className = module.__name__.split('.')[-1]
        addDtmlName = "add%s" % className
        factoryName = "manage_add%s" % className
        iconName = "www/%s_icon.gif" % className
        confclass = getattr(module, className, None)
        #contentClasses.append(confclass)
        if not confclass: continue
        args.append(confclass)
        constructors = []
        addDtml = getattr(module, addDtmlName, None)
        if addDtml: constructors.append(addDtml)
        factory = getattr(module, factoryName, None)
        if factory: constructors.append(factory)
        if not constructors: continue
        kwargs['constructors'] = constructors
        kwargs['permission'] = "Add DMD Objects"
        if os.path.exists(os.path.join(__path__[0], iconName)):
            kwargs['icon'] = iconName
        log.debug("Register Class=%s",className)
        log.debug("kwargs=%s", constructors)
        apply(registrar.registerClass, args, kwargs)
