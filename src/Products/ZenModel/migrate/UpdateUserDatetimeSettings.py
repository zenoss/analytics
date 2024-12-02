##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = '''
Edit User date format to comply with ZEN-28191

$Id:$
'''

import logging
log = logging.getLogger("zen.migrate")
import Migrate


class UpdateUserDatetimeSettings(Migrate.Step):
    version = Migrate.Version(200, 0, 1)

    def cutover(self, dmd):
        df_map = {
            'YY/MM/DD': 'YYYY/MM/DD',
            'DD/MM/YY': 'DD/MM/YYYY',
            'MM/DD/YY': 'MM/DD/YYYY'
        }

        for usr in dmd.ZenUsers.getAllUserSettings():
            if usr.dateFormat in df_map:
                log.info(
                    'update user %s dateFormat from %s to %s',
                    usr.id, usr.dateFormat, df_map[usr.dateFormat]
                )
                usr.dateFormat = df_map[usr.dateFormat]


UpdateUserDatetimeSettings()
