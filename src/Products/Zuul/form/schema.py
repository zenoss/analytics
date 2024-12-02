##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.schema._field import Text as ZSText, TextLine, Bool, Int, Float
from zope.schema._field import Tuple, List, Password, Choice as ZSChoice

class FieldMixin(object):
    """
    A mixin providing extra attributes to zope.schema.
    """
    def __init__(self, xtype=None, order=None, group=None, vtype=None,
                 decimalPrecision=2, required=False, alwaysEditable=False,
                 *args, **kwargs):
        super(FieldMixin, self).__init__(*args, **kwargs)
        l = locals()
        for f in ('xtype', 'order', 'group', 'vtype', 'decimalPrecision', 'required', 'alwaysEditable'):
            value = l[f]
            if value is not None:
                setattr(self, f, value)

def _mixedIn(klass, **kwargs):
    """
    Return a class with FieldMixin mixed in and default attributes set.
    """
    return type(klass.__name__, (FieldMixin, klass), kwargs)

Text = _mixedIn(ZSText, xtype='textarea')
TextLine = _mixedIn(TextLine, xtype='textfield')
Bool = _mixedIn(Bool, xtype='checkbox')
Int = _mixedIn(Int, xtype='numberfield')
Float = _mixedIn(Float, xtype='numberfield')
Tuple = _mixedIn(Tuple, xtype='textarea')
List = _mixedIn(List, xtype='textarea')
Choice = _mixedIn(ZSChoice, xtype='autoformcombo')
MultiChoice = _mixedIn(ZSChoice, xtype='itemselector')
Password = _mixedIn(Password, xtype='password')
Entity = _mixedIn(ZSText, xtype='linkfield')
File = _mixedIn(ZSText, xtype='fileuploadfield')
