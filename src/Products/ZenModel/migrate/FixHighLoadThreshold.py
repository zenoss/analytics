##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """
Up to this version we used to ship with a high load threshold of 1200,
this was an obviously insane value. We are adjusting upgrades to have
a high load threshold of 2.1
"""

import Migrate


class FixHighLoadThreshold(Migrate.Step):
    version = Migrate.Version(4, 0, 0)

    def cutover(self, dmd):
        # look for all high load thresholds
        brains = dmd.zport.global_catalog(meta_type='ThresholdClass',
                                          name="high load",
                                          path='/zport/dmd/Devices/Server/SSH/Linux/rrdTemplates')
        for brain in brains:
            try:
                obj = brain.getObject()
                maxval = int(obj.maxval)
            except (TypeError, ValueError):
                continue
            # we can safely assume they really do not want 1200 as a value
            if maxval == 1200:
                obj.maxval = 2.1


FixHighLoadThreshold()
