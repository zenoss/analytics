#!/usr/bin/python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os
for d, dirs, filenames in os.walk(os.path.join(os.environ['ZENHOME'], 'perf')):
    for f in filenames:
        fullpath = os.path.join(d, f)
        if f.find('_') >= 0: continue
        if not f.endswith('.rrd'): continue
        base = os.path.basename(f[:-4])
        os.rename(fullpath, os.path.join(d, '%s_%s.rrd' % (base, base)))
