##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import sys

import six

from zope.configuration import xmlconfig


def initialize_environment(configs=(), overrides=(), useZope=True):
    if useZope:
        _use_zope(configs=configs, overrides=overrides)
    else:
        _no_zope(configs=configs, overrides=overrides)


def _use_zope(configs, overrides):
    from Zope2.App import zcml
    from OFS.Application import import_products
    from Products.ZenUtils.zenpackload import load_zenpacks
    import Products.ZenWidgets

    import_products()
    load_zenpacks()
    zcml.load_site()
    _load_overrides(
        zcml._context, [("scriptmessaging.zcml", Products.ZenWidgets)]
    )
    _load_configs(zcml._context, configs)
    _load_overrides(zcml._context, overrides)


def _no_zope(configs, overrides):
    ctx = xmlconfig._getContext()
    _load_configs(ctx, configs)
    _load_overrides(ctx, overrides)


def _load_configs(ctx, configs):
    for filename, module in configs:
        if isinstance(module, six.string_types):
            module = sys.modules[module]
        xmlconfig.file(filename, package=module, context=ctx)


def _load_overrides(ctx, overrides):
    for filepath, module in overrides:
        xmlconfig.includeOverrides(ctx, filepath, package=module)
        ctx.execute_actions()
