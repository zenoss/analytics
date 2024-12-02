##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""RRDMGraph

RRDMGraph stores mgraph representations for later graphing.
"""

from Persistence import Persistent


class RRDMGraph(Persistent):
    def __init__(self, mtargets, views):
        self._mtargets = mtargets
        self._views = views

    def getMTargets(self):
        return self._mtargets

    def getViews(self):
        return self._views
