##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.Zuul.interfaces.info import IInfo
from Products.Zuul.form import schema


class IZenPackInfo(IInfo):
    version = schema.TextLine(title=u"Version",
                             description=u"Version number information")
    author = schema.TextLine(title=u"Author",
                             description=u"Persons or organizations who created the ZenPack.")
    organization = schema.TextLine(title=u"Organization",
                             description=u"Organization to which the autho is associated.")
    url = schema.TextLine(title=u"URL",
                             description=u"URL containing ZenPack information.")
    license = schema.TextLine(title=u"License",
                             description=u"License information.")
    compatZenossVers = schema.TextLine(title=u"License",
                             description=u"Which versions of Zenoss that this ZenPack will work on.")
    path = schema.TextLine(title=u"path",
                             description=u"Directory location of the ZenPack.")
    isDevelopment = schema.Bool(title=u"isDevelopment",
                             description=u"Can additions or updates be made to this ZenPack?.")
    isEggPack = schema.Bool(title=u"isEggPack",
                             description=u"Is this in Python egg format or Zope package format.")
    isBroken = schema.Bool(title=u"isBroken",
                             description=u"Is this ZenPack properly installed.")

    namespace = schema.TextLine(title=u"namespace",
                             description=u"Namespace where the ZenPack lives.")
    ZenPackName = schema.TextLine(title=u"ZenPackName",
                             description=u"Name of the ZenPack in the Namespace.")

