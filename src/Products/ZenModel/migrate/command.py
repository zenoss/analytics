##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zCommandPath to DeviceClass.

'''
import Migrate

class Commands(Migrate.Step):
    version = Migrate.Version(0, 23, 0)

    def update(self, dmd, oldname, name, default, **kw):
        if dmd.Devices.hasProperty(oldname):
            value = not dmd.Devices.getProperty(oldname)
            dmd.Devices._setProperty(name, value, **kw)
            dmd.Devices._delProperty(oldname)
        elif not dmd.Devices.hasProperty(name):
            dmd.Devices._setProperty(name, default, **kw)

    def cutover(self, dmd):
        from Products.ZenUtils.Utils import zenPath
        self.update(dmd, "zNagiosPath", "zCommandPath", zenPath('libexec'))
        if dmd.Devices.hasProperty("zNagiosCycleTime"):
            dmd.Devices._delProperty("zNagiosCycleTime")
        zem = self.dmd.ZenEventManager
        conn = zem.connect()
        try:
            curs = conn.cursor()
            for name in 'zenagios', 'zencacti':
                curs.execute('DELETE FROM heartbeat where component = "%s"' % name)
        finally: zem.close(conn)

Commands()
