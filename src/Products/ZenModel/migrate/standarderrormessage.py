##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
Create standard_error_message at the root level of zope
"""

from __future__ import absolute_import

import os.path
import Products.ZenModel as _zm

from . import Migrate


class StandardErrorMessage(Migrate.Step):
    version = Migrate.Version(0, 23, 0)

    def cutover(self, dmd):
        """Remove index_html and replace with a python script that will
        redirect to /zport/dmd/
        """
        app = dmd.getPhysicalRoot()
        if app.hasObject("standard_error_message"):
            app._delObject("standard_error_message")
        filepath = os.path.join(
            os.path.dirname(_zm.__file__), "dtml/standard_error_message.dtml"
        )
        with open(filepath) as fp:
            text = fp.read()
        import OFS.DTMLMethod

        OFS.DTMLMethod.addDTMLMethod(
            app, id="standard_error_message", file=text
        )


StandardErrorMessage()
