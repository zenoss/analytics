from Products.Zuul.form import schema
from Products.Zuul.interfaces.component import IComponentInfo
from Products.Zuul.interfaces.template import IRRDDataSourceInfo

# ZuulMessageFactory is the translation layer. You will see strings intended to
# been seen in the web interface wrapped in _t(). This is so that these strings
# can be automatically translated to other languages.
from Products.Zuul.utils import ZuulMessageFactory as _t

# In Zenoss 3 we mistakenly mapped TextLine to Zope's multi-line text
# equivalent and Text to Zope's single-line text equivalent. This was
# backwards so we flipped their meanings in Zenoss 4. The following block of
# code allows the ZenPack to work properly in Zenoss 3 and 4.

# Until backwards compatibility with Zenoss 3 is no longer desired for your
# ZenPack it is recommended that you use "SingleLineText" and "MultiLineText"
# instead of schema.TextLine or schema.Text.
from Products.ZenModel.ZVersion import VERSION as ZENOSS_VERSION
from Products.ZenUtils.Version import Version
if Version.parse('Zenoss %s' % ZENOSS_VERSION) >= Version.parse('Zenoss 4'):
    SingleLineText = schema.TextLine
    MultiLineText = schema.Text
else:
    SingleLineText = schema.Text
    MultiLineText = schema.TextLine


class IExampleDataSourceInfo(IRRDDataSourceInfo):
    """
    Defines what fields should be displayed on the edit dialog for this
    datasource in the Zenoss web interface.
    """

    # We inherit common datasource fields like event class, severity and others
    # from IRRDDataSourceInfo.

    exampleProperty = SingleLineText(
        title=_t(u'Example Property'),
        group=_t(u'Example Protocol'),
        )


class IExampleComponentInfo(IComponentInfo):
    attributeOne = schema.Int(title=_t(u"Attribute #1"))
    attributeTwo = SingleLineText(title=_t(u"Attribute #2"))
