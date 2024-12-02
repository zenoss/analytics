##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import pkg_resources
import Products

from zope.dottedname.resolve import resolve
from Products.CMFCore.utils import ProductsPath


def load_zenpacks():
    # Iterate over all ZenPack eggs and load them
    for zpkg in pkg_resources.iter_entry_points('zenoss.zenpacks'):
        pkg_path = zpkg.load().__path__[0]
        if pkg_path not in ProductsPath:
            ProductsPath.insert(0, pkg_path)
        module = resolve(zpkg.module_name)
        setattr(Products, zpkg.module_name, module)
