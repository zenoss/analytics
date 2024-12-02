##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Interface
from zope.configuration.fields import GlobalObject
from zope.schema import TextLine

class IDirectRouter(Interface):
    """
    Registers a name and a javascript viewlet for a DirectRouter subclass.
    """
    name = TextLine(
        title=u"Name",
        description=u"The name of the requested view.")

    for_ = GlobalObject(
        title=u"For Interface",
        description=u"The interface the directive is used for.",
        required=False)

    class_ = GlobalObject(
        title=u"Class",
        description=u"The DirectRouter subclass"
    )

    namespace = TextLine(
        title=u"Namespace",
        description=unicode("The JavaScript namespace under which the"
                            " remote methods should be available"),
        required=False
    )

    layer = TextLine(
        title=u"Layer",
        description=u"The layer",
        required=False
    )

    timeout = TextLine(
        title=u"Timeout",
        description=unicode("Override the default timeout (in milliseconds)"
                            " for the calls"),
        required=False,
        default=u"30000"
    )

    permission = TextLine(
        title=u"Permission",
        description=unicode("The base permission required to access methods"
                            " on this router. Individual methods can override"
                            " this setting using the require decorator"),
        required=False,
        default=u"zope.Public"
    )
