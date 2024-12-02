##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from socket import *

s = socket(AF_INET, SOCK_DGRAM)
import time
now = time.strftime('%b %d %T %Z %Y')
m = '''<165>%s localhost myproc[10]: %%%% It's time to make the do-nuts.  %%%%  Ingredients: Mix=OK, Jelly=OK # Devices: Mixer=OK, Jelly_Injector=OK, Frier=OK # Transport: Conveyer1=OK, Conveyer2=OK # %%%%''' % now
now = time.strftime('%b %d %T')
m = '''<165>%s foo@win2003 myproc[10]: %%%% It's time to make the do-nuts.  %%%%  Ingredients: Mix=OK, Jelly=OK # Devices: Mixer=OK, Jelly_Injector=OK, Frier=OK # Transport: Conveyer1=OK, Conveyer2=OK # %%%%''' % now
s.sendto(m, ('127.0.0.1', 514) )
