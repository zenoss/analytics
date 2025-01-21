#!/usr/bin/env python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import sys, re

if (len(sys.argv) < 2):
    print "Usage: mib_split <MIB filaname>"
    sys.exit(1)

begun = 0
begin_re = re.compile(r'^(\S+)\s+DEFINITIONS\s+::=\s+BEGIN')

source_mib = open(sys.argv[1], 'r')
dest_mib = None

for line in source_mib:
    matches = begin_re.search(line)
    if matches:
        begun += 1

        filename = matches.groups()[0] + '.txt'
        print "Writing " + filename

        if dest_mib: dest_mib.close()
        dest_mib = open(filename, 'w')

    if begun:
        dest_mib.write(line)

dest_mib.close()
source_mib.close()
