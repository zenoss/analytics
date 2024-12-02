##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""RenderServer

This class is deprecated.
Frontend that passes RRD graph options to rrdtool to render,
and then returns an URL to access the rendered graphic file.
"""

from .RRDToolItem import RRDToolItem


class RenderServer(RRDToolItem):
    """
    Not used any more since version 5.0.
    """

    meta_type = "RenderServer"
