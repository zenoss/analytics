##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

import Migrate

log = logging.getLogger("zen.migrate")


_data = [{
    "id": "zenjobs-aborted",
    "example": "Job aborted by user",
    "explanation": "A job was aborted by a user",
}, {
    "id": "zenjobs-failure",
    "example": "AttributeError: foo",
    "explanation":
        "A job has failed due to an error while the job was running",
}, {
    "id": "zenjobs-timeout",
    "example": "Job killed after 5 hours",
    "explanation":
        "A job was killed because its running time exceeded the time limit",
}]


class AddEventClassInstancesForZenJobs(Migrate.Step):
    """Adds three EventClassInst objects to the /App/Zenoss event class.
    """

    version = Migrate.Version(200, 5, 1)

    def cutover(self, dmd):
        zenoss = dmd.Events.App.Zenoss
        instances = zenoss.getInstances()
        for fields in _data:
            inst_id = fields["id"]
            exists = next(
                (True for i in instances if i.id == inst_id), False,
            )
            if exists:
                log.info("/App/Zenoss instance '%s' already exists.", inst_id)
                continue
            log.info("Adding '%s' as an /App/Zenoss instance.", inst_id)
            instance = zenoss.createInstance(inst_id)
            instance.sequence = 1001
            instance.example = fields["example"]
            instance.explanation = fields["explanation"]


AddEventClassInstancesForZenJobs()
