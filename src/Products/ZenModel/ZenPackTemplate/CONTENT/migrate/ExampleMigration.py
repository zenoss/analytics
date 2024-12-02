import logging
log = logging.getLogger('zen.migrate')

import Globals

from Products.ZenModel.ZenPack import ZenPackMigration
from Products.ZenModel.migrate.Migrate import Version
from Products.ZenUtils.Utils import unused

unused(Globals)


# Your migration class must subclass ZenPackMigration.
class ExampleMigration(ZenPackMigration):

    # There are two scenarios under which this migrate script will execute.
    #   1. Fresh Install - If this ZenPack is being installed for the first
    #      time and the migrate script version is greater than or equal to the
    #      ZenPack's version, it will execute.
    #
    #   2. Upgrade - If this ZenPack is being upgraded and the migrate script
    #      version is greater than or equal to the version of the ZenPack that
    #      is already installed, it will execute.
    version = Version(0, 0, 1)

    def migrate(self, dmd):
        log.info("Running ExampleMigration")

        # Do the migration work. No commit is needed.
        pass


# Run the migration when this file is imported.
ExampleMigration()
