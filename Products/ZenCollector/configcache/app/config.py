##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os

from Products.ZenUtils.config import Config, ConfigLoader
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.path import zenPath


def add_config_arguments(parser):
    filename = "-".join(parser.prog.split(" ")[:-1]) + ".conf"
    parser.add_argument(
        "-C",
        "--configfile",
        default=os.path.join(zenPath("etc"), filename),
        help="Pathname of the configuration file"
    )


def getConfigFromArguments(parser, args):
    """
    Return a dict containing the configuration.

    @type args: argparse.Namespace
    """
    options = tuple(
        (cfg_name, opt_name, xform, default)
        for cfg_name, opt_name, xform, default in (
            (
                _long_name(act.option_strings),
                act.dest,
                act.type if act.type is not None else _identity,
                act.default,
            )
            for act in parser._actions
            if act.dest not in ("help", "version", "configfile")
        )
        if cfg_name is not None
    )
    dest_names = {
        long_name: dest_name
        for long_name, dest_name, _, _ in options
    }
    xforms = {
        long_name: xform
        for long_name, _, xform, _ in options
    }
    defaults = {
        long_name: default
        for long_name, _, _, default in options
    }
    config = defaults.copy()
    config.update(
        (key, xforms[key](value))
        for key, value in getGlobalConfiguration().items()
        if key in dest_names
    )

    configfile = getattr(args, "configfile", None)
    if configfile:
        app_config_loader = ConfigLoader(configfile, Config)
        try:
            config.update(
                (key, xforms[key](value))
                for key, value in app_config_loader().items()
                if key in dest_names
            )
        except IOError as ex:
            # Re-raise exception if the error is not "File not found"
            if ex.errno != 2:
                raise

    # Apply command-line overrides.  An override is a value from the
    # command line that differs from the default.  This does mean that
    # explicitely specified default values on the CLI are ignored.
    config.update(
        (cname, override)
        for cname, default, override in (
            (cname, defaults[cname], getattr(args, oname, None))
            for cname, oname in dest_names.items()
        )
        if override != default
    )
    return config


def _long_name(names):
    name = next((nm for nm in names if nm.startswith("--")), None)
    if name:
        return name[2:]


def _identity(value):
    return value
