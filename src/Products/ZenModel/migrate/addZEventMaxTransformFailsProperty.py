##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__='''
This migration script adds zEventMaxTransformFail property to /Events.
'''

import logging
log = logging.getLogger("zen.migrate")

import Migrate

EVENT_MAX_TRANSFORM_FAILS_PROPERTY = 'zEventMaxTransformFails'
TRANSFORM_ENABLED_PROPERTY = 'transformEnabled'


class AddZEventMaxTransformFailsProperty(Migrate.Step):
    version = Migrate.Version(109, 0, 0)

    def cutover(self, dmd):
        try:
            log.debug('Adding %s property to /Events.', EVENT_MAX_TRANSFORM_FAILS_PROPERTY)
            if not hasattr(dmd.Events, EVENT_MAX_TRANSFORM_FAILS_PROPERTY):
                dmd.Events._setProperty(EVENT_MAX_TRANSFORM_FAILS_PROPERTY, 10, type='int')
        except Exception as e:
            log.warn('Exception trying to add %s property to /Events, %s', EVENT_MAX_TRANSFORM_FAILS_PROPERTY, e)

class AddTransformEnabledProperty(Migrate.Step):
    version = Migrate.Version(109, 0, 0)

    def cutover(self, dmd):
        try:
            log.debug('Adding %s property to /Events.', TRANSFORM_ENABLED_PROPERTY)
            if not hasattr(dmd.Events, TRANSFORM_ENABLED_PROPERTY):
                dmd.Events._setProperty(TRANSFORM_ENABLED_PROPERTY, True, type='bool')
        except Exception as e:
            log.warn('Exception trying to add %s property to /Events, %s', TRANSFORM_ENABLED_PROPERTY, e)

AddZEventMaxTransformFailsProperty()
AddTransformEnabledProperty()
