##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import json

from datetime import datetime
from time import time

from hashlib import md5

from zope.component import createObject

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from Products.Jobber.task import requires, DMD
from Products.Jobber.zenjobs import app

from ..cache import OidMapRecord, ConfigStatus
from ..constants import Constants
from ..utils import OidMapProperties


@app.task(
    bind=True,
    base=requires(DMD),
    name="configcache.build_oidmap",
    summary="Create OID Map Task",
    description_template="Create an OID map for zentrap.",
    ignore_result=True,
    dmd_read_only=True,
)
def build_oidmap(self, submitted=None):
    """
    Create a map of SNMP OIDs.

    @param configclassname: The fully qualified name of the class that
        will create the device configuration.
    @type configclassname: str
    @param submitted: timestamp of when the job was submitted
    @type submitted: float
    """
    buildOidMap(self.dmd, self.log, submitted)


# NOTE: the buildOidMap function exists so that it can be tested
# without having to handle Celery details in the unit tests.


def buildOidMap(dmd, log, submitted):
    store = _getStore()

    # record when this build starts
    started = time()

    # Check whether this is an old job, i.e. job pending timeout.
    # If it is an old job, skip it, manager already sent another one.
    status = store.get_status()

    if _job_is_old(status, submitted, started, log):
        return

    # If the status is Expired, another job is coming, so skip this job.
    if isinstance(status, ConfigStatus.Expired):
        log.warn(
            "skipped this job because another job is coming  submitted=%f",
            submitted,
        )
        return

    # If the status is Pending, verify whether it's for this job, and if not,
    # skip this job.
    if isinstance(status, ConfigStatus.Pending):
        s1 = int(submitted * 1000)
        s2 = int(status.submitted * 1000)
        if s1 != s2:
            log.warn(
                "skipped this job in favor of newer job  submitted=%f",
                submitted,
            )
            return

    # Change the configuration's status to 'building' to indicate that
    # a config is now building.
    store.set_building(time())
    log.info("building oidmap")

    oidmap = {b.oid: b.id for b in dmd.Mibs.mibSearch() if b.oid}

    # get a new store; the prior store's connection may have gone stale.
    store = _getStore()

    if not oidmap:
        log.info("no oidmap was built")
        _delete_oidmap(store, log)
        return

    checksum = md5(  # noqa: S324
        json.dumps(oidmap, sort_keys=True).encode("utf-8")
    ).hexdigest()

    record = OidMapRecord.make(time(), checksum, oidmap)

    # Get the current status of the configuration.
    recent_status = store.get_status()

    # Test whether the status should be updated
    update_status = _should_update_status(recent_status, started, log)

    created_ts = datetime.fromtimestamp(record.created).isoformat()
    if not update_status:
        # recent_status is not ConfigStatus.Building, so another job
        # will be submitted or has already been submitted.
        store.put_config(record)
        log.info(
            "saved oidmap without changing status  created=%s", created_ts
        )
    else:
        verb = "replaced" if status is not None else "added"
        store.add(record)
        log.info("%s oidmap  created=%s", verb, created_ts)


def _should_update_status(recent_status, started, log):
    # Check for expected statuses.
    if isinstance(recent_status, ConfigStatus.Building):
        # The status is Building, so let's update the status.
        return True

    if isinstance(recent_status, ConfigStatus.Expired):
        update_status = bool(recent_status.expired < started)
        if not update_status:
            log.info("oidmap (re)expired while building new oidmap")
        else:
            log.warning(
                "oidmap status has inconsistent state  status=Expired "
                "expired=%s",
                datetime.fromtimestamp(recent_status.expired).isoformat(),
            )
        return update_status

    if isinstance(recent_status, ConfigStatus.Pending):
        update_status = bool(recent_status.submitted < started)
        if not update_status:
            log.info("another job submitted while building oidmap")
        else:
            log.warning(
                "oidmap status has inconsistent state  status=Pending "
                "submitted=%s",
                datetime.fromtimestamp(recent_status.submitted).isoformat(),
            )
        return update_status

    log.warning(
        "Unexpected status change during oidmap build  status=%s",
        type(recent_status).__name__,
    )
    return True


def _delete_oidmap(store, log):
    if not store:
        return
    store.remove()
    log.info("removed previously built oidmap")
    # Ensure all statuses for this key are deleted.
    store.clear_status()


def _job_is_old(status, submitted, now, log):
    if submitted is None or status is None:
        # job is not old (default state)
        return False
    limit = OidMapProperties().pending_timeout
    if submitted < (now - limit):
        log.warn(
            "skipped this job because it's too old  "
            "service=%s submitted=%f %s=%s",
            status.key.service,
            submitted,
            Constants.oidmap_pending_timeout_id,
            limit,
        )
        return True
    return False


def _getStore():
    client = getRedisClient(url=getRedisUrl())
    return createObject("oidmapcache-store", client)
