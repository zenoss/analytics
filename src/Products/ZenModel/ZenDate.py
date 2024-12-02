##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Persistence import Persistent
from DateTime import DateTime
from Products.ZenUtils import Time

class ZenDate(Persistent):
    """
    DEPRECATED wraper so that date sets on device don't provoke entire object
    store
    """
    
    def __init__(self, date=None):
        self.setDate(date)
        
    def setDate(self, date=None):
        if date == None: date = DateTime()
        if isinstance(date, basestring):
            date = DateTime(date)
        self.date = date

    def __float__(self):
        return float(self.date)

    def getDate(self):
        return self.date
   
    def getString(self):
        """Date in format 2006/09/13 12:16:06.000
        """
        return Time.LocalDateTime(self.date.timeTime())

    def getStringSecsResolution(self):
        """Date in format 2006/09/13 12:16:06
        """
        return Time.LocalDateTimeSecsResolution(self.date.timeTime())
