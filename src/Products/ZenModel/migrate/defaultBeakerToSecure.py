##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class DefaultBeakerToSecure(Migrate.Step):
    """
    Set beaker session.secure to true in config
    """

    version = Migrate.Version(101, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        beaker_secure_text = '    session.secure          True\n'

        commit = False
        zopes_and_zauths = filter(lambda s: s.name in ["zope", "zauth", "Zope", "Zauth"], ctx.services)
        log.info("Found %i services named 'zope', 'zauth', 'Zope', or 'Zauth'." % len(zopes_and_zauths))
        for z in zopes_and_zauths:
            configfiles = z.originalConfigs + z.configFiles
            for configfile in filter(lambda f: f.name == '/opt/zenoss/etc/zope.conf', configfiles):
                lines = configfile.content.split('\n')
                in_beaker_config_block = False
                session_secure_found = False
                for i, line in enumerate(lines):
                    if line.startswith('#'):
                        continue
                    if '<product-config beaker>' in line:
                        in_beaker_config_block = True
                    if in_beaker_config_block and 'session.secure' in line:
                        session_secure_found = True
                    if in_beaker_config_block and '</product-config>' in line:
                        in_beaker_config_block = False
                        if not session_secure_found:
                            log.info("Adding session.secure entry to beaker product-config in /opt/zenoss/etc/zope.conf for service '%s'."
                                     % z.name)
                            lines[i] = beaker_secure_text + lines[i]
                            commit = True
                        session_secure_found = False
                configfile.content = '\n'.join(lines)
        if commit:
            ctx.commit()

DefaultBeakerToSecure()

