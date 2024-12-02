##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """
If the zFlappingSeverity field already exists on the 'Events' event class and is a string,
this will change it to an int.
"""

import Migrate
import logging
from Acquisition import aq_base
log = logging.getLogger('zen.migrate')


class FlappingSeverityType(Migrate.Step):
    version = Migrate.Version(5, 0, 0)

    def cutover(self, dmd):

        edict = dmd.getDmdRoot('Events')
        existingFlappingAttr = getattr(aq_base(edict), "zFlappingSeverity", None)

        if existingFlappingAttr is not None and dmd.Events.getPropertyType('zFlappingSeverity') != 'int':
            log.debug("Removing/re-adding zFlappingSeverity property to Events event class")
            edict._delProperty("zFlappingSeverity")
            edict._setProperty("zFlappingSeverity", int(existingFlappingAttr), type="int")


FlappingSeverityType = FlappingSeverityType()
