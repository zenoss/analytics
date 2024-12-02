##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


class FakeRequest(dict):
    ''' Used for ajax calls from event console and elsewhere.  This is used
    as a container for REQUEST['message'] which we are interested in.  It has
    the advantage over the regular REQUEST object in that it won't actually
    bother to render anything when callZenScreen() is called with one.
    '''
    dontRender = True
    dontRedirect = True
    
    def __init__(self, *args, **kw):
        dict.__init__(self, *args, **kw)
        self['oneKeyValueSoInstanceIsntEmptyAndEvalToFalse'] = True
        
    def setMessage(self, R):
        if R and self.get('message', ''):
            R['message'] = self['message']
