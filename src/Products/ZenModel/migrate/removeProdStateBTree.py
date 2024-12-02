##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import transaction

log = logging.getLogger("zen.migrate")

from Products.ZenUtils.guid.interfaces import IGUIDManager

import Migrate

MIGRATED_FLAG = "_migrated_prodstates"


class RemoveProdStateBTree(Migrate.Step):
    """
    Move production states from the BTree back to the objects
    """
    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):

        # Check to see if the BTree exists
        btree = getattr(dmd, 'prodstate_table', None)
        if btree:
            guidManager = IGUIDManager(dmd)
            count = 0
            total = len(btree)
            for guid, states in btree.iteritems():
                obj = guidManager.getObject(guid)

                # 'ProdState' code no longer exists so 'states' object is going to be broken
                # Setting it this way instead of using 'setProdState' will NOT trigger a re-index
                #  but anybody upgrading to this version is going to have to run a full re-index post-upgrade
                if not obj:
                    continue
                try:
                    obj.productionState = states.__Broken_state__['productionState']
                    obj.preMWProductionState = states.__Broken_state__['preMWProductionState']
                except AttributeError:
                    log.warning("Coulnd't get production state for %s, setting up 'Production' to it", obj)
                    obj.productionState = 1000
                    obj.preMWProductionState = 1000

                count += 1

                if count % 100 == 0:
                    log.info("Migrated production state for %d objects of %d", count, total)

                if count % 1000 == 0:
                    log.info("Committing transaction for 1000 objects")
                    transaction.commit()

            # Tidy up whatever's in the last 1000 that didn't get committed
            if count % 100:
                log.info("Migrated %d objects of %d", count, total)
            if count % 1000:
                log.info("Committing transaction for %d objects", count % 1000)
                transaction.commit()

            # Now drop the BTree
            log.info("Removing production state BTree")
            dmd._delOb('prodstate_table')
            transaction.commit()

            log.info("Migration Complete")
        elif not getattr(dmd, MIGRATED_FLAG, False):
            # We don't have a BTree, but we haven't been migrated yet, so this is from back before the BTree existed,
            #  When prodstate was an attribute called 'productionState' on the object.
            #  Since 'productionState' is now the name of a property, we have to pull the old productionState off of the
            #  object's __dict__
            def migrate_object(obj):
                obj._p_activate() # Activate the object so the old attributes end up in __dict__
                if 'preMWProductionState' in obj.__dict__:
                    obj.preMWProductionState = obj.__dict__['preMWProductionState']
                    del obj.__dict__['preMWProductionState']

                if 'productionState' in obj.__dict__:
                    obj.productionState = obj.__dict__['productionState']
                    del obj.__dict__['productionState']

            count = 0
            for device in dmd.Devices.getSubDevicesGen_recursive():
                migrate_object(device)
                count += 1

                # migrate components
                try:
                    cmps = device.getDeviceComponents()
                except AttributeError:
                    pass
                else:
                    for c in cmps:
                        migrate_object(c)

                if count % 100 == 0:
                    log.info("Migrated production state for %d devices", count)

                if count % 1000 == 0:
                    log.info("Committing transaction for 1000 objects")
                    transaction.commit()

            # Tidy up whatever's in the last 1000 that didn't get committed
            if count % 100:
                log.info("Migrated %d devices", count)
            if count % 1000:
                log.info("Committing transaction for %d devices", count % 1000)
                transaction.commit()
        else:
            log.info("Nothing to migrate")

        setattr(dmd, MIGRATED_FLAG, True)


RemoveProdStateBTree()
