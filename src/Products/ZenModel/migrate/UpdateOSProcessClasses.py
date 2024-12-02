##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Migrate
import logging
from Products.Zuul import getFacade

log = logging.getLogger('zen.migrate')

TEMPLATE = {
    'Zope': '.*runzope.*zenoss.*',
    'zenactiond': '.*zenactiond.py.*',
    'zencommand': '.*zencommand.py.*',
    'zeneventd': '.*zeneventd.py.*',
    'zeneventserver': '.*zeneventserver.*',
    'zenhub': '.*zenhub.py.*',
    'zenjobs': '.*zenjobs.py.*',
    'zenmail': '.*zenmail.py.*',
    'zenmodeler': '.*zenmodeler.py.*',
    'zenperfsnmp': '.*zenperfsnmp.py.*',
    'zenping': '.*zenping.py.*',
    'zenpop3': '.*zenpop3.py.*',
    'zenprocess': '.*zenprocess.py.*',
    'zenstatus': '.*zenstatus.py.*',
    'zensyslog': '.*zensyslog.py.*',
    'zentrap': '.*zentrap.py.*'
}

DEPRECATED = ('zenrrdcached', 'zenrender')


class UpdateOSProcessClasses(Migrate.Step):
    " Update default OSProcess classes templates to make them work in 5.x "

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):

        f = getFacade('process')
        classes = dmd.Processes.Zenoss.getSubOSProcessClassesSorted()

        for klass in classes:
            path = '/zport/dmd/Processes/Zenoss/osProcessClasses/%s' % klass.id
            if klass.id in DEPRECATED:
                try:
                    f.deleteNode(path)
                    continue
                except Exception as e:
                    log.error("Unable to remove depricated OSProcess class %s: %s" % (klass,e))

            if klass.id in TEMPLATE:
                try:
                    f.setInfo(path, {'includeRegex': TEMPLATE[klass.id]})
                except Exception as e:
                    log.error("Unable to update OSProcess class %s: %s" % (klass, e))

UpdateOSProcessClasses()
