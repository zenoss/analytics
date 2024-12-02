##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""Report

Report represents a report definition loaded from an .rpt file

$Id: Report.py,v 1.3 2004/04/06 02:19:04 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

from urllib import quote

from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable
from Products.ZenModel.BaseReport import BaseReport
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.Utils import getDisplayType
from Products.ZenUtils.deprecated import deprecated

@deprecated
def manage_addReport(context, id, title = None, text=None,
                    REQUEST = None, submit=None):
    """make a Report"""
    id = str(id)
    if REQUEST is None:
        context._setObject(id, Report(id, text))
        ob = getattr(context, id)
        if title:
            ob.pt_setTitle(title)
        return ob
    else:
        file = REQUEST.form.get('file')
        headers = getattr(file, 'headers', None)
        if headers is None or not file.filename:
            zpt = Report(id)
        else:
            zpt = Report(id, file, headers.get('content_type'))

        context._setObject(id, zpt)

        audit('UI.Report.Add', zpt.id, title=title, text=text, 
              reportType=getDisplayType(zpt), organizer=context)

        try:
            u = context.DestinationURL()
        except AttributeError:
            u = REQUEST['URL1']

        if submit == " Add and Edit ":
            u = "%s/%s" % (u, quote(id))
        REQUEST.RESPONSE.redirect(u+'/manage_main')
    return '' 


addReport = PageTemplateFile('www/reportAdd', globals(),
                            __name__='addReport')


class Report(BaseReport, ZenPackable):
    """Report object"""

    __pychecker__ = 'no-override'

    meta_type = 'Report'

    # this is deprecated don't use!!!
    description = ""

    security = ClassSecurityInfo()

    _relations = ZenPackable._relations

    def __init__(self, id, title = None, text=None, content_type='text/html'):
        ZenModelRM.__init__(self, id);
        self._template = ZopePageTemplate(id, text, content_type)
        self.title = title

    def __call__(self, *args, **kwargs):
        """Return our rendered template not our default page
        """
        if not 'args' in kwargs:
            kwargs['args'] = args
        template = self._template.__of__(self)
        path_info = template.REQUEST['PATH_INFO'].replace(' ', '%20')
        if (path_info.startswith('/zport/dmd/Reports') and
                path_info not in template.REQUEST['HTTP_REFERER'] and
                'adapt=false' not in template.REQUEST['QUERY_STRING']):
            url = '/zport/dmd/reports#reporttree:'
            url += path_info.replace('/', '.')
            template.REQUEST['RESPONSE'].redirect(url)
        self.auditRunReport()
        return template.pt_render(extra_context={'options': kwargs})


    def ZScriptHTML_tryForm(self, *args, **kwargs):
        """Test form called from ZMI test tab
        """
        return self.__call__(self, args, kwargs)


    def manage_main(self):
        """Return the ZMI edit page of our template not ourself
        """
        template = self._template.__of__(self)
        return template.pt_editForm()
    pt_editForm = manage_main
    
    
    def pt_editAction(self, REQUEST, title, text, content_type, expand):
        """Send changes to our template instead of ourself"""
        template = self._template.__of__(self)
        return template.pt_editAction(REQUEST,
            title, text, content_type, expand)


InitializeClass(Report)
