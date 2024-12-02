##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """
Adds the /Status/Flapping event class as well as the default configuration for
event flapping detection.
"""

import Migrate
import logging
log = logging.getLogger('zen.migrate')


class EventFlapping(Migrate.Step):
    version = Migrate.Version(4, 2, 70)

    def cutover(self, dmd):
        # add the flapping organizer
        dmd.Events.createOrganizer('/Status/Flapping')

        # add the per event class event flapping configuration
        edict = dmd.getDmdRoot('Events')
        edict._buildEventFlappingZProperties()

EventFlapping = EventFlapping()
