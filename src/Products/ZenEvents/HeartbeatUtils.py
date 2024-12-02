##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


# This program is part of Zenoss Core, an open source monitoring platform.
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
# For complete information please visit: http://www.zenoss.com/oss/
from Products.Zuul import getFacade
from time import time

def deviceLink(deviceRoot, deviceName):
    if deviceRoot is None:
        return deviceName
    device = deviceRoot.findDevice(deviceName)
    if device is None:
        return deviceName
    return "<a href='%s'>%s</a>" % (device.getPrimaryUrlPath(),
            device.titleOrId())

def getHeartbeatObjects(failures=True, limit=0, deviceRoot=None,
        keys=('alink', 'comp', 'dtime', 'devId')):
    beats = []
    now = int(time() * 1000)
    heartbeats = getFacade('zep').getHeartbeats()
    for heartbeat_dict in heartbeats:
        # Seconds is difference between current time and last reported time
        # ZEP returns milliseconds, so perform appropriate conversion
        seconds = (now - heartbeat_dict['last_time']) / 1000
        if failures is False or seconds >= heartbeat_dict['timeout_seconds']:
            beat = {
                keys[0]: deviceLink(deviceRoot, heartbeat_dict['monitor']),
                keys[1]: heartbeat_dict['daemon'],
                keys[2]: seconds
            }
            if len(keys) > 3:
                beat[keys[3]] = heartbeat_dict['monitor']
            beats.append(beat)
    if limit:
        return beats[:limit]
    return beats
