##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


# _xmlplus is included in two packages, so we get an annoying UserWarning when
# we import pkg_resources. If everything imports from here, we can filter out
# the warning centrally.
import warnings
warnings.filterwarnings('ignore', '.*_xmlplus.*', UserWarning)

# There is a nasty incompatibility between pkg_resources and twisted.
# Importing pkg_resources before the twisted reactor works around the problem.
# See http://dev.zenoss.org/trac/ticket/3146 for details
import pkg_resources

from Products.ZenUtils.Utils import unused
unused(pkg_resources)

__all__ = ['pkg_resources']
