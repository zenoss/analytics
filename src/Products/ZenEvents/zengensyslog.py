#! /usr/bin/env python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


NUMB_EVENTS = 120

evts = dict(
# will hit default rules and be mapped to /Ingore
#REPEAT = "<165> message repeated 4 times",

# /Security/Login/Fail
FAIL = "<165> dropbear[23]: exit before auth (user 'root', 3 fails): Max auth tries reached - user root",

# /Security/Login/BadPass
SSHBADPASS = "<165> ssh[3]: Failed password for user from 10.1.2.3 port 53529 ssh2",

# Cisco Power Loss /HW/Power/PowerLoss (will clear)
PLOSS = "<165>%C6KPWR-SP-4-PSFAIL: power supply 1 output failed",
POK = "<165>%C6KPWR-SP-4-PSOK: power supply 1 turned on",

)
keys = evts.keys()
import random
for i in range(NUMB_EVENTS):
    print evts[random.choice(keys)]
