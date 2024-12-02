##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""LocationDump

Dump location data from pre 0.11.7 database to text to be reloaded
in new location format
"""

from ZCmdBase import ZCmdBase

class LocationDump(ZCmdBase):
    """
    Dump location data
    """
    
    def dump(self):
        """
        Dump location data to the specified output file.
        """
        outfile = open(self.options.outfile, "w")
        if not hasattr(self.dataroot, "getSubDevices"):
            raise RuntimeError("dataroot doesn't have getSubDevices")
        devs = self.dataroot.getSubDevices()
        for dev in devs:
            dcname = dev.getDataCenterName()
            rname = dev.getRackName()
            if rname: 
                locpath = dcname.split("-")
                locpath.append(rname)
            else:
                locpath = ("NoLocation",)
            line = "%s|%s\n" % (dev.getId(), "/" + "/".join(locpath))
            outfile.write(line)
        outfile.close()


    def buildOptions(self):
        """
        Command-line options for LocationDump
        """
        ZCmdBase.buildOptions(self)
        self.parser.add_option('-o', '--outfile',
                    dest='outfile',
                    default="locdump.out",
                    help='output file')
        

if __name__ == "__main__":
    ld = LocationDump()
    ld.dump()
