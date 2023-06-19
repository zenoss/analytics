#!/usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
# this script is meant to be ran inside of zendmd
# e.g. zendmd --script addSystemUser.py
import re
import logging
from ZODB.transact import transact
from Products.ZenUtils.path import zenPath
from subprocess import call
log = logging.getLogger("zenoss.addsystemuser")

username = 'zenoss_system'

@transact
def addSystemUser(dmd, username):
    password = dmd.ZenUsers.generatePassword()
    dmd.ZenUsers.manage_addUser(username, password=password, roles=('Manager',))
    return username, password


if dmd.ZenUsers._getOb(username, None) is None:
    username, password = addSystemUser(dmd, username)
    cmd = zenPath('bin', 'zenglobalconf') + " -u zauth-username=%s -u zauth-password=%s" % (username, password)
    rc = call(cmd, shell=True)
    if rc != 0:
        log.error("Unable to set the system username and password please update %s with these lines\nzauth-username=%s\nzauth-password=%s", zenPath('etc', 'global.conf'), username, password)

    # Now do the shipper, which is YAML
    shippercfg = zenPath('etc', 'metricshipper', 'metricshipper.yaml')
    with open(shippercfg, 'r') as f:
        cfg = f.read()
    # Could use YAML to parse/dump this, but that would remove helpful comments.
    # Wimp out with regex for now.
    cfg = re.sub(r'^\s*#?\s*username:.*', '\nusername: %s' % username, cfg,
            flags=re.MULTILINE)
    cfg = re.sub(r'^\s*#?\s*password:.*', '\npassword: %s' % password, cfg,
            flags=re.MULTILINE)
    with open(shippercfg, 'w') as f:
        f.write(cfg)
