##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


objnoprops = """<object id='loc' module='Products.ZenRelations.tests.TestSchema' class='Location' move='False'>
</object>
"""


objwithprops = """<object id='dev' module='Products.ZenRelations.tests.TestSchema' class='Device' move='False'>
<property setter="setPingStatus" type="int" id="pingStatus" mode="w" >
0
</property>
<property type="lines" id="communities" mode="w" >
()
</property>
</object>
"""

objwithtoone = """<object id='dev' module='Products.ZenRelations.tests.TestSchema' class='Device' move='False'>
<property setter="setPingStatus" type="int" id="pingStatus" mode="w" >
0
</property>
<property type="lines" id="communities" mode="w" >
()
</property>
<toone id='location' objid='loc'/>
</object>
"""

objwithtomany = """<object id='loc' module='Products.ZenRelations.tests.TestSchema' class='Location' move='False'>
<tomany id='devices'>
<link objid='dev'/>
</tomany>
</object>
"""

objwithtomanycont = """<object id='dev' module='Products.ZenRelations.tests.TestSchema' class='Device' move='False'>
<property setter="setPingStatus" type="int" id="pingStatus" mode="w" >
0
</property>
<property type="lines" id="communities" mode="w" >
()
</property>
<tomanycont id='interfaces'>
<object id='eth0' module='Products.ZenRelations.tests.TestSchema' class='IpInterface' move='False'>
</object>
</tomanycont>
</object>
"""

objwithoutskip = """<object id='dev' module='ZenPacks.zenoss.ZenVMware.VMwareHost' class='VMwareHost'>
<tomanycont id='guestDevices'>
<object id='guest0' module='ZenPacks.zenoss.ZenVMware.VMwareGuest' class='VMwareGuest'>
</object>
</tomanycont>
</object>
"""

objwithskip = """<object id='dev' module='Products.ZenModel.Device' class='Device'>
<tomanycont id='guestDevices'>
<object id='guest0' module='ZenPacks.zenoss.ZenVMware.VMwareGuest' class='VMwareGuest'>
</object>
</tomanycont>
</object>
"""


devicexml = """
<objects>
<object id='/loc' module='Products.ZenRelations.tests.TestSchema' class='Location'/>
<object id='dev' module='Products.ZenRelations.tests.TestSchema' class='Device'>
<property setter="setPingStatus" type="int" id="pingStatus" mode="w" >
0
</property>
<tomanycont id='interfaces'>
<object id='eth0' module='Products.ZenRelations.tests.TestSchema' class='IpInterface'>
<toone id='device' objid='dev'/>
</object>
</tomanycont>
<toone id='location' objid='/loc'/>
</object>
</objects>
"""
