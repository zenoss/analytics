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


class TemplatizeCollectorEndpoints(Migrate.Step):
    "Use templated names for collector endpoints"

    version = Migrate.Version(100, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Get all zentrap and zensyslog services.
        services = filter(lambda s: s.name in ("zentrap", "zensyslog"), ctx.services)
        log.info("Found %i services named 'zentrap' or 'zensyslog'." % len(services))

        # Make sure all public Endpoints prefix
        # the endpoint with the name of the parent collector
        for svc in services:

            parentname = ""
            parent = ctx.getServiceParent(svc)

            if not parent is None:
                parentname = parent.name

            publicEndpoints = filter(lambda endpoint: endpoint.purpose == "export", svc.endpoints)
            log.info("Found %i export endpoints for service '%s'." % (len(publicEndpoints), svc.name))
            for endpoint in publicEndpoints:

                # Fix items broken by previous implementation of this migration:
                if "{{(parent .).Name}}" in endpoint.application:
                    log.info("Replacing unprocessed template with actual parent name on endpoint application for '%s'." % svc.name)
                    endpoint.application = endpoint.application.replace("{{(parent .).Name}}", parentname)

                # Prepend parent service name to endpoint application, if it doesn't already exist
                if not endpoint.application.startswith(parentname + "_"):
                    log.info("Prepending parent name to endpoint application for '%s'." % svc.name)
                    endpoint.application = parentname + "_" + endpoint.application
                else:
                    log.info("Endpoint application for '%s' already starts with parent name." % svc.name)

                # Prepend template for parent name to the endpoint's ApplicationTemplate property
                if not endpoint.applicationtemplate.startswith("{{(parent .).Name}}_"):
                    log.info("Prepending parent.Name template to endpoint application template for '%s'." % svc.name)
                    endpoint.applicationtemplate = "{{(parent .).Name}}_" + endpoint.applicationtemplate
                else:
                    log.info("Endpoint application template for '%s' already starts with parent.Name template." % svc.name)

        ctx.commit()

TemplatizeCollectorEndpoints()
