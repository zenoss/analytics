
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import yaml

##############################################################################
# User-maintained Files                                                      #

# User-maintained file with devices to moniotor
DEVICE_YAML = "/opt/zenoss/etc/nub/user/devices.yaml"


##############################################################################
# The files below are maintained By update_zenpacks.py and should            #
# not be edited.                                                             #

# All zenpack-defined defined device classes and zProperties
DEVICECLASS_YAML = "/opt/zenoss/etc/nub/system/deviceclasses.yaml"

# Zenpack-defined monitoring templates
MONITORINGTEMPLATE_YAML = "/opt/zenoss/etc/nub/system/monitoringtemplates.yaml"

# Lists out each modeler plugin and a list of which deviceProperties it specifies.
MODELER_PLUGIN_YAML = "/opt/zenoss/etc/nub/system/modelerplugins.yaml"

# Lists out each modeler plugin and a list of which deviceProperties it specifies.
PARSER_PLUGIN_YAML = "/opt/zenoss/etc/nub/system/parserplugins.yaml"

# Datasource (plugins) names and corresponding classes
DATASOURCE_YAML = "/opt/zenoss/etc/nub/system/datasources.yaml"

# Information on model classes defined by zenpacks
CLASS_MODEL_YAML = "/opt/zenoss/etc/nub/system/classmodels.yaml"


def load_device_yaml():
    return yaml.load(file(DEVICE_YAML, 'r'))


def load_deviceclass_yaml():
    return (
        yaml.load(file(DEVICECLASS_YAML, 'r')),
        yaml.load(file(MONITORINGTEMPLATE_YAML, 'r')),
    )


def load_modelerplugin_yaml():
    return yaml.load(file(MODELER_PLUGIN_YAML, 'r'))


def load_parserplugin_yaml():
    return yaml.load(file(PARSER_PLUGIN_YAML, 'r'))


def load_datasource_yaml():
    return yaml.load(file(DATASOURCE_YAML, 'r'))


def load_classmodel_yaml():
    return yaml.load(file(CLASS_MODEL_YAML, 'r'))





