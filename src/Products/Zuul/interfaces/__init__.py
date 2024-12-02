##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in 
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""
The concept of an interface is part of the Zope Component Architecture (ZCA).
Interfaces are used in the Zuul Python API to document the attributes of the
interface implementations.  Using interfaces also allows the facades to get
info objects that adapt a ZenModel object, e.g. IInfo(self._dmd.Devices).  The
definition that determines the concrete implementation returned by such a
statement is in Zuul/configure.zcml.
"""

from zope.interface import Interface, Attribute   


class IFacade(Interface):
    """
    An API facade
    """
    context = Attribute('The context of the adapter.')


class IMarshaller(Interface):
    """
    An adapter that converts an object to a dictionary
    """

    def marshal(keys=None):
        """
        Convert an object to a dictionary.
        """


class IUnmarshaller(Interface):
    """
    An adapter that converts a dictionary to an object.
    """

    def unmarshal(data): 
        """
        Convert a dictionary to an object.
        """


class IMarshallable(Interface):
    """
    Marker interface for an object able to be marshalled by an IMarshaller.
    """


class IDataRootFactory(Interface):
    """
    Returns a DataRoot object from the current connection.
    """


from process import *
from service import *
from device import *
from properties import *
from devicemanagement import *
from component import *
from info import *
from tree import *
from triggers import *
from template import *
from command import *
from network import *
from graphpoint import *
from organizer import *
from mib import *
from zep import *
from reportable import *
from report import *
from stats import *
from jobs import *
from software import *
from devicedumpload import *
from eventclasses import *
from manufacturers import *
from backup import *
from metric import *
from security import *
from application import *
from monitor import *
from user import *
from host import *
