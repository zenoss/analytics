##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

import logging
log = logging.getLogger('zen.migrate')


class StringifyExpansionCardSlot(Migrate.Step):
    version = Migrate.Version(3, 0, 0)

    def cutover(self, dmd):
        try:
            for brain in dmd.Devices.componentSearch(meta_type='ExpansionCard'):
                card = brain.getObject()
                if isinstance(card.slot, int):
                    card.slot = str(card.slot)
        except Exception as ex:
            log.error('Error converting expansion card slots to strings: %s',
                ex)


StringifyExpansionCardSlot()
