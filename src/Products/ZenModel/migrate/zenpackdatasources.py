##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''All existing datasources should be switched to instances
of BasicDataSource instead of RRDDataSource
'''

import sys
import Migrate

class ZenPackDataSources(Migrate.Step):

    version = Migrate.Version(2, 0, 0)


    def cutover(self, dmd):
        from Products.ZenModel.BasicDataSource import BasicDataSource
        from Products.ZenModel.RRDDataSource import RRDDataSource
        try:
            from Products.ZenWeb.datasources.PageCheckDataSource \
                import PageCheckDataSource
        except ImportError:
            PageCheckDataSource = None
        numDS = 0
        numUnhandled = 0
        for t in dmd.Devices.getAllRRDTemplates():
            for s in t.datasources():
                if s.__class__ == RRDDataSource:
                    numDS += 1
                    if PageCheckDataSource and s.sourcetype == 'PAGECHECK':
                        s.__class__ = PageCheckDataSource
                    else:
                        s.__class__ = BasicDataSource
                elif issubclass(s.__class__, RRDDataSource):
                    pass
                else:
                    numUnhandled += 1
                    sys.stderr.write('ZenPackDataSources can\'t handle datasource' + \
                            ' type %s\n' % (s.__class__))
        print 'Converted %s DataSources' % numDS
        if numUnhandled:
            print 'Problems with %s DataSources' % numUnhandled

ZenPackDataSources()
