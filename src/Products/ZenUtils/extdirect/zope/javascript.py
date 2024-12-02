##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import zope.interface
from zope.viewlet.manager import WeightOrderedViewletManager
from zope.viewlet.viewlet import JavaScriptViewlet
from interfaces import IExtDirectJavaScriptManager
from interfaces import IJsonApiJavaScriptManager
from interfaces import IExtDirectJavaScriptAndSourceManager

class ExtDirectJavaScriptManager(WeightOrderedViewletManager):
    zope.interface.implements(IExtDirectJavaScriptManager)

class JsonApiJavaScriptManager(WeightOrderedViewletManager):
    zope.interface.implements(IJsonApiJavaScriptManager)

class ExtDirectJavaScriptAndSourceManager(WeightOrderedViewletManager):
    zope.interface.implements(IExtDirectJavaScriptAndSourceManager)

DirectSourceViewlet = JavaScriptViewlet('direct.js')
