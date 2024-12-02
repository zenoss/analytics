##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009-2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Interface, Attribute
from Products.Zuul.interfaces import IFacade
from tree import ITreeNode
from info import IInfo


class IProcessEntity(Interface):
    """
    Marker interface for OSProcessClass and OSProcessOrganizer
    """

class IProcessNode(ITreeNode):
    """
    Marker interface for a node in a process tree.
    """

class IProcessInfo(IInfo):
    """
    Represents a single ProcessClass instance.
    """
    name = Attribute('The name of the process')
    description = Attribute('A description of the process')
    isMonitoringAcquired = Attribute('Does this process acquire its monitor '
                                     'eventSeverity properties from container')
    monitor = Attribute('Whether or not the process is monitored')
    eventSeverity = Attribute('The severity of the event fired when this '
                             'process goes down')
    hasRegex = Attribute('OSProcessClasses have regexes, OSProcessOrganizers'
                         ' do not')
    includeRegex = Attribute('Regular expression used to match process to a '
                             'running command on the managed host')
    excludeRegex = Attribute('Regular expression used to prevent process from '
                             'matching a running command on the managed host')
    replaceRegex = Attribute('Regular expression used to rewrite parts of '
                             'matched running commands from the managed host')
    replacement  = Attribute('Replacement template used to rewrite parts of '
                             'matched running commands from the managed host')
    minProcessCount = Attribute('Numerical value describing the minimum number'
                                ' of this process to be running at any time.') 
    maxProcessCount = Attribute('Numerical value describing the maximum number'
                                ' of this process to be running at any time.')
    minProcessMemory = Attribute('Numerical value (bytes) describing the minimum '
                                 ' memory this process should use.')
    maxProcessMemory = Attribute('Numerical value (bytes) describing the maximum '
                                 ' memory this process should use.')

class IProcessFacade(IFacade):

    def getInfo(id):
        """
        Get information about the OSProcessOrganizer and OSProcessClass
        identified by id.
        """

    def getDevices(id):
        """
        Get the devices with OSProcess instances that fall under the
        IProcessEntity identified by the id parameter.
        """

    def moveProcess(uid, targetUid):
        """
        Move an OSProcessOrganizer or OSProcessClass uniquely identified by
        the uid parameter to the OSProcessOrganizer uniquely identified by the
        targetUid parameter. Return the primary path of the object after the
        move.
        """
