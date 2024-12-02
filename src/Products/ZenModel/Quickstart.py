##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

__doc__="""Quickstart
Quickstart provides API to allow ZenPacks to embed their specific setup steps into
the quickstart sequence after the user defned the admin password and set up the
master user and before the page where they can add initial devices. It allows
multiple ZenPacks to add or remove their setup steps and each one will be executed
in the last-in first-out order 
"""

import logging

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from OFS.SimpleItem import SimpleItem
from Products.ZenModel.ZenModelItem import ZenModelItem

log = logging.getLogger("zen.Quickstart")



def _defaultQuickstartStepList(context):
    """
    If not done already initialize the QuickstartStepList dmd object and add the default
    QuickstartStep used by core which is qs-step2 
    """
    if not hasattr(context, 'QuickstartStepList'):
        addQuickstartStepList(context)
        addQuickstartStep(context)
    quickstartStepList = context.QuickstartStepList.qs_steps
    return quickstartStepList
    

def addQuickstartStep(context, id='QuickstartStep', module='quickstart', qs_step='qs-step2', before=0):
    """
    Add a QuickstartStep object to the list of objects. By default the requested pages will be called
    in the last-in first-out (LIFO) order. Used at the time ZenPack that requires this is installed.
    
    If the requested module is already in the list its old entry will first be deleted and the new one
    added at the requested place. 
    
    If there is a need for more than one quickstart page to be added for the same software module then
    the module parameter takes the form "module:number", e.g. "myModule:2" for the 2nd quickstart page
    of myModule. However this is just to satisfy the unique module name requirement for the quickstart
    steps list and the order of execution is determined solely by the order of the list entries.   
    
    module String:    name of the module requesting the 
    qs_step String:   name of the webpage that will service this quickstart step 
    before int:       where to put the requested step in the quickstart list, 0 means at the beginning 
    """
    quickstartStepList = _defaultQuickstartStepList(context)
    
    try:
        quickstartStep = next(x for x in quickstartStepList if x.module==module)
        i = quickstartStepList.index(quickstartStep)
        del quickstartStepList[i]
    except StopIteration:
        pass
    quickstartStep = QuickstartStep(id, module=module, qs_step=qs_step)
    quickstartStepList.insert(before, quickstartStep)
    context.QuickstartStepList._p_changed = True
    
def removeQuickstartStep(context, module='quickstart'):
    """
    Remove a quickstart step from the list. Used when ZenPack is uninstalled.
    
    module String:    identifies the quickstart step list entry to be removed 
    """
    quickstartStepList = _defaultQuickstartStepList(context)

    quickstartStep = next(x for x in quickstartStepList if x.module==module)
    i = quickstartStepList.index(quickstartStep)
    del quickstartStepList[i]
    context.QuickstartStepList._p_changed = True

    
def getQuickstartStep(context, module='quickstart'):
    """
    Get the quickstart step for the module

    module String:    identifies the quickstart step list entry to return 
    
    Return String:    webpage to invoke for the named module
    """
    quickstartStepList = _defaultQuickstartStepList(context)
    
    quickstartStep = next(x for x in quickstartStepList if x.module==module)
    return quickstartStep.qs_step

def getTopQuickstartStep(context):
    """
    Get the first quickstart step. This is what userView module uses to determine
    which page to redirect to once the user enters the admin password and user
    
    Return String:    the first quickstart webpage to activate
    """
    quickstartStepList = _defaultQuickstartStepList(context)
    
    return quickstartStepList[0].qs_step

def getNextQuickstartStep(context, module='quickstart'):
    """
    Get the next quickstart step after the named module is finished with its
    quickstart step.

    module String:    identifies the quickstart step to invoke after the named module is done
                      with its processing
    
    Return String:    webpage to invoke after the named module
    """
    quickstartStepList = _defaultQuickstartStepList(context)
    
    quickstartStep = next(x for x in quickstartStepList if x.module==module)
    i = quickstartStepList.index(quickstartStep) + 1
    return quickstartStepList[i].qs_step
        
def addQuickstartStepList(context):
    """
    Provide a list of QuickstartStep objects which makes for an ordered
    sequence of execution of quickstart step webpages at the initial system
    run.
    """
    if not hasattr(context, 'QuickstartStepList'):
        quickstartStepList = QuickstartStepList()
        context._setObject('QuickstartStepList', quickstartStepList)


class QuickstartStep(ZenModelItem, SimpleItem):
    """
    QuickstartStep object stores the module name and the name of the webpage that
    is registered to be activated during the quickstart process. If a single ZenPack
    requires more than one quickstart page then the module name has to be made
    unique for each quickstart step by appending ":number" to the module name, e.g.
    "myModule:2".
    """

    meta_type = 'QuickstartStep'

    security = ClassSecurityInfo()

    _properties = (
        {'id': 'module', 'type': 'string'},
        {'id': 'qs_step', 'type': 'string'},
    )

    def __init__(self, id, module='quickstart', qs_step='qs-step2'):
        self.id = id
        self.module = module
        self.qs_step = qs_step
    
class QuickstartStepList(ZenModelItem, SimpleItem):
    """
    QuickstartStepList is an object that provides storage for the registered quickstart
    steps. These are then executed in their sequential order given by the list. Normally
    all quickstart steps are added at the beginning so all steps will be executed in the
    LIFO order.
    """

    meta_type = 'QuickstartStepList'

    security = ClassSecurityInfo()

    _properties = (
        {'id': 'qs_steps', 'type': 'lines'}
    )
    
    def __init__(self):
        self.qs_steps = []

    security = ClassSecurityInfo()
    
InitializeClass(QuickstartStepList)
InitializeClass(QuickstartStep)
