##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""Classifier

Organizes classifier subclasses to perform high level classification of 
a device.  Subclasses know how to collect information from a device
and look in their indexes for a ClassifierEntry about the device.

$Id: Classifier.py,v 1.4 2004/03/26 23:58:44 edahl Exp $"""

__version__ = "$Revision: 1.4 $"[11:-2]

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from AccessControl import Permissions as permissions
from Products.ZenModel.ZenossSecurity import *
from OFS.OrderedFolder import OrderedFolder

from ZenModelItem import ZenModelItem

def manage_addClassifier(context, title = None, REQUEST = None):
    """make a device"""
    ce = Classifier('ZenClassifier', title)
    context._setObject(ce.id, ce)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()+'/manage_main')
                                     


class Classifier(ZenModelItem, OrderedFolder):

    meta_type = 'Classifier'
    
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'Classifier',
            'meta_type'      : 'Classifier',
            'description'    : """Class to manage product information""",
            'icon'           : 'Classifier_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addClassifier',
            'immediate_view' : 'manageClassifiers',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'manageClassifiers'
                , 'permissions'   : (
                  permissions.view, )
                },
            )
          },
        )
    
    security = ClassSecurityInfo()
    
    def __init__(self, id, title=None):
        self.id = id
        self.title = title
        self.curClassifierEntryId = 0
       

    def classifyDevice(self, deviceName, loginInfo, log=None): 
        """kick off device classification against all classifiers
        will walk down a tree of classifiers until the most specific 
        is found.  Top level classifiers can jump into the tree
        where lower level classifiers will then take over the process
        """
        classifierEntry = None
        for classifier in self.getClassifierValues():
            classifierEntry = classifier.getClassifierEntry(
                                            deviceName, loginInfo,log)
            if classifierEntry: break
        return classifierEntry
      

    def getClassifierValues(self):
        return self.objectValues()


    def getClassifierNames(self):
        """return a list of availible classifiers for entry popup"""
        return self.objectIds()


    def getNextClassifierEntryId(self):
        cid = self.curClassifierEntryId
        self.curClassifierEntryId += 1
        return "ClassifierEntry-" + str(cid)


InitializeClass(Classifier)
