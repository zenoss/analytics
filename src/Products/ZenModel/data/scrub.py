##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import re

subs = (
    ("\S+\@\S+\.(com|org|net)", "email@email.com"),
    ("\d+\.\d+\.\d+\.\d+", "1.1.1.1"),
)

lines = open("events.xml").readlines()
out = open("events.xml.new", "w")
for line in lines:
    for regex, sub in subs:
        line = re.sub(regex, sub, line)
