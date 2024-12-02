##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
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



class AddSolrSearchLimitVar(Migrate.Step):
    version = Migrate.Version(200, 3, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        topService = ctx.getTopService()

        if not topService.context.get('global.conf.solr-search-limit', None):
            topService.context['global.conf.solr-search-limit']=u'10000'
            log.info("global.conf.solr-search-limit variable is added")
            ctx.commit()

AddSolrSearchLimitVar()
