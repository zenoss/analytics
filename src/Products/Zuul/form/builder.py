##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import operator
import zope.schema
from zope.component import adapts
from zope.interface import implements, providedBy
from zope.schema.vocabulary import getVocabularyRegistry
from zope.schema.vocabulary import VocabularyRegistryError
from Products import Zuul
from Products.Zuul.form.interfaces import IFormBuilder
from Products.Zuul.interfaces import IInfo

ordergetter = operator.itemgetter('order')

FIELDKEYS = (
    'xtype',
    'title',
    'description',
    'readonly',
    'order',
    'group',
    'decimalPrecision',
    'alwaysEditable',
    'vtype',
    'required'
)


class FormBuilder(object):
    implements(IFormBuilder)
    adapts(IInfo)

    def __init__(self, context):
        self.context = context
        self.readOnly = False
        self.hasAlwaysEditableField = False

    def vocabulary(self, field):
        vocabulary = field.vocabulary
        if vocabulary is None:
            reg = getVocabularyRegistry()
            try:
                vocabulary = reg.get(self.context, field.vocabularyName)
            except VocabularyRegistryError:
                raise ValueError("Can't get values from vocabulary %s" %
                                 field.vocabularyName)
        return [(t.value, t.token) for t in vocabulary._terms]

    def fields(self, fieldFilter=None):
        d = {}
        for iface in providedBy(self.context):
            f = zope.schema.getFields(iface)
            def _filter(item):
                include = True
                if fieldFilter:
                    key=item[0]
                    include = fieldFilter(key)
                else:
                    include = bool(item)
                return include
            if f:
                for k,v in filter(_filter, f.iteritems()):
                    c = self._dict(v)
                    c['name'] = k
                    value =  getattr(self.context, k, None)
                    c['value'] = value() if callable(value) else value                    
                    if c['xtype'] in ('autoformcombo', 'itemselector'):
                        c['values'] = self.vocabulary(v)
                    d[k] = c
        return d

    def groups(self, fieldFilter=None):
        g = {}
        for k, v in self.fields(fieldFilter).iteritems():
            g.setdefault(v['group'], []).append(v)
        for l in g.values():
            l.sort(key=ordergetter)
        return g

    def render(self, fieldsets=True, readOnly=False, fieldFilter=None):
        self.readOnly = readOnly
        if not fieldsets:
            fields = sorted(self.fields(fieldFilter).values(), key=ordergetter)
            for field in fields:
                if field['xtype'] == 'password' and field['value']:
                    field['value'] = '*' * len(field['value'])
            form = map(self._item, fields)
            return {'items':[{'xtype':'fieldset', 'items':form}]}
        # group the fields
        groups = self.groups(fieldFilter)
        form = {
            'items': [self._fieldset(k, v) for k,v in groups.iteritems()]
        }
        return form

    def _dict(self, field):
        """
        Turns a zope.schema.Field into a dictionary with our desired keys.
        """
        return dict((k, getattr(field, k, None)) for k in FIELDKEYS)

    def _fieldset(self, name, items):
        """
        Turns a list into a fieldset config.
        """
        return {
            'xtype': 'fieldset',
            'title': name,
            'items': map(self._item, items)
            }

    def _item(self, item):
        """
        Turns a dict representing a field into a config.
        """
        if item['alwaysEditable']:
            self.hasAlwaysEditableField = True

        if item['readonly'] or self.readOnly and not item['alwaysEditable']:
            if item['xtype']=='checkbox':
                xtype = 'checkbox'
                item['disabled'] = True
            elif item['xtype']=='linkfield':
                xtype = 'linkfield'
            else:
                xtype = 'displayfield'
        else:
            xtype = item['xtype']

        labelProperty = 'boxLabel' if xtype=='checkbox' else 'fieldLabel'
        labelStyle = 'display:none' if xtype=='checkbox' else None

        value = item['value']

        if xtype == 'linkfield':
            value = Zuul.marshal(value, keys=['uid', 'name'])

        field = {
            'xtype': xtype,
            labelProperty: item['title'],
            'labelStyle': labelStyle,
            'inputAttrTpl': " data-qtip='" + item['description']  + "' ",            
            'anchor':'85%',
            'name': item['name'],
            'value': value,
            'vtype': item['vtype'],
            'allowBlank': not item['required'],
            'disabled': item.get('disabled', False)
            }

        # fileupload has a superfluous button we must remove
        if xtype == 'fileuploadfield':
            field['buttonCfg'] = dict(hidden=True)

        if xtype == 'numberfield':
            field['decimalPrecision'] = item['decimalPrecision']
        if xtype in ('autoformcombo', 'itemselector'):
            field['values'] = item['values']
        if xtype=='checkbox':
            field['checked'] = value
        return field
