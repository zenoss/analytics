##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zFileSystemSizeOffset to DeviceClass.

'''
import Migrate
from Products.ZenModel.MinMaxThreshold import MinMaxThreshold


perfFilesystemTransform = """if device and evt.eventKey:
    for f in device.os.filesystems():
        if f.name() != evt.component and f.id != evt.component: continue

        # Extract the used blocks from the event's message
        import re
        m = re.search("threshold of [^:]+: current value ([\d\.]+)", evt.message)
        if not m: continue
    
        # Get the total blocks from the model. Adjust by specified offset.
        totalBlocks = f.totalBlocks * getattr(device, "zFileSystemSizeOffset", 1.0)
        totalBytes = totalBlocks * f.blockSize
        usedBytes = None
        
        currentValue = float(m.groups()[0])
        if 'usedBlocks' in evt.eventKey:
            usedBytes = currentValue * f.blockSize
        elif 'FreeMegabytes' in evt.eventKey:
            usedBytes = totalBytes - (currentValue * 1048576)
        else:
            continue
        
        # Calculate the used percent and amount free.
        usedBlocks = float(m.groups()[0])
        p = (usedBytes / totalBytes) * 100
        from Products.ZenUtils.Utils import convToUnits
        free = convToUnits(totalBytes - usedBytes)

        # Make a nicer summary
        evt.summary = "disk space threshold: %3.1f%% used (%s free)" % (p, free)
        evt.message = evt.summary
        break
"""

class zFileSystemSizeOffset(Migrate.Step):
    version = Migrate.Version(2, 5, 0)
    
    def cutover(self, dmd):
        # Install the zFileSystemSizeOffset zProperty
        if not dmd.Devices.hasProperty('zFileSystemSizeOffset'):
            dmd.Devices._setProperty('zFileSystemSizeOffset', 1.0, type="float")
        
        # Install the /Perf/Filesystem transform
        try:
            from md5 import md5
            baddigest = '1d6002d0a89a35dda203301df42be502'

            ec = dmd.Events.Perf.Filesystem
            if not ec.transform or md5(ec.transform).hexdigest() == baddigest:
                ec.transform = perfFilesystemTransform
        except AttributeError:
            pass
        
        # Fix thresholds and graph RPNs
        for t in dmd.Devices.getAllRRDTemplates():
            if t.id != "FileSystem": continue
            
            try:
                if t.datasources()[0].oid != "1.3.6.1.2.1.25.2.3.1.6":
                    continue
            except Exception:
                continue
            
            for th in t.thresholds():
                if not isinstance(th, MinMaxThreshold):
                    continue
                
                # Handle 2.4.2 thresholds.
                th.maxval = th.maxval.replace(
                    "(here.totalBlocks * here.zFileSystemSizeOffset)",
                    "here.getTotalBlocks()")
                th.minval = th.minval.replace(
                    "(here.totalBlocks * here.zFileSystemSizeOffset)",
                    "here.getTotalBlocks()")
                
                # Handle pre-2.4.2 thresholds.
                th.maxval = th.maxval.replace(
                    "here.totalBlocks",
                    "here.getTotalBlocks()")
                th.minval = th.minval.replace(
                    "here.totalBlocks",
                    "here.getTotalBlocks()")
            
            for g in t.graphDefs():
                for gp in g.graphPoints():
                    if not hasattr(gp, "rpn"): continue
                    if gp.rpn.endswith(",/,100,*"):
                        gp.rpn = "${here/getTotalBlocks},/,100,*"


zFileSystemSizeOffset()
