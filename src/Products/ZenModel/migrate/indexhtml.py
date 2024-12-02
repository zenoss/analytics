##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Create an index_html at the root level of zope that redirects to
/zports/dmd/

'''

__version__ = "$Revision$"[11:-2]

import Migrate

class IndexHtml(Migrate.Step):
    version = Migrate.Version(0, 23, 0)

    def cutover(self, dmd):
        ''' Remove index_html and replace with a python script that will
            redirect to /zport/dmd/
        '''
        app = dmd.getPhysicalRoot()
        if app.hasObject('index_html'):
            app._delObject('index_html')
        from Products.PythonScripts.PythonScript import manage_addPythonScript
        manage_addPythonScript(app, 'index_html')
        newIndexHtml = app._getOb('index_html')
        text = 'container.REQUEST.RESPONSE.redirect("/zport/dmd/")\n'
        newIndexHtml.ZPythonScript_edit('', text)

IndexHtml()
