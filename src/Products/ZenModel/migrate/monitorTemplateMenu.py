##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import os.path

from . import Migrate


class MonitorTemplateMenu(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        dmd.buildMenus(
            {
                "PerformanceMonitor_list": [
                    {
                        "action": "performanceTemplates",
                        "description": "Templates",
                        "id": "performanceTemplates",
                        "ordering": 16.0,
                        "permissions": ("View Device",),
                    }
                ],
                "StatusMonitor_list": [
                    {
                        "action": "performanceTemplates",
                        "description": "Templates",
                        "id": "performanceTemplates",
                        "ordering": 16.0,
                        "permissions": ("View Device",),
                    }
                ],
            }
        )
        for c in dmd.Monitors.objectValues(spec="MonitorClass"):
            c.buildRelations()
        for c in dmd.Monitors.objectValues(spec="Monitor"):
            c.buildRelations()
        dmd.Monitors.buildRelations()
        if len(dmd.Monitors.rrdTemplates()) == 0:
            from Products.ZenRelations.ImportRM import ImportRM

            template = os.path.join(
                os.path.dirname(__file__), "monitorTemplate.xml"
            )
            im = ImportRM(noopts=True, app=dmd.zport)
            im.loadObjectFromXML(xmlfile=template)


monitorTemplateMenu = MonitorTemplateMenu()
