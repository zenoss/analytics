##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


def getImmediateView(ob):
    if hasattr(ob, "factory_type_information"):
        return ob.factory_type_information[0]["immediate_view"]
    else:
        raise NameError(
            'Cannot find default view for "%s"'
            % "/".join(ob.getPhysicalPath())
        )


def immediate_view(ob):
    view = getImmediateView(ob)
    path = ob.getPhysicalPath() + (view,)
    return "/".join(path)


def Device(ob):
    id = "/".join(ob.getPhysicalPath())
    REQUEST = getattr(ob, "REQUEST", {})
    return (
        id
        + "/devicedetail#"
        + REQUEST.get("fragment", "deviceDetailNav:device_overview")
    )


def EventClass(ob):
    id = ".".join(ob.getPhysicalPath())
    return "/zport/dmd/Events/eventclasses#classes:" + id


def DeviceClass(ob):
    id = ".".join(ob.getPhysicalPath())
    return "/zport/dmd/itinfrastructure#devices:" + id


def Manufacturer(ob):
    return (
        "zport/dmd/manufacturers#manufacturers_tree:.zport.dmd.Manufacturers."
        + ob.id
    )


def ProductClass(ob):
    mId = ob.manufacturer().id
    id = "/".join(ob.getPhysicalPath())
    return (
        "zport/dmd/manufacturers#manufacturers_tree:.zport.dmd.Manufacturers."
        + mId
        + ":"
        + id
    )


def Location(ob):
    id = ".".join(ob.getPhysicalPath())
    return "/zport/dmd/itinfrastructure#locs:" + id


def System(ob):
    id = ".".join(ob.getPhysicalPath())
    return "/zport/dmd/itinfrastructure#systemsTree:" + id


def DeviceGroup(ob):
    id = ".".join(ob.getPhysicalPath())
    return "/zport/dmd/itinfrastructure#groups:" + id


def IpNetwork(ob):
    id = ".".join(ob.getPhysicalPath())
    return "/zport/dmd/networks#networks:" + id


def DeviceComponent(ob):
    devpath = ob.device().getPrimaryUrlPath()
    return ":".join(
        [
            devpath + "/devicedetail#deviceDetailNav",
            ob.meta_type,
            ob.getPrimaryUrlPath(),
        ]
    )


def Process(ob):
    id = ".".join(ob.getPhysicalPath())
    return "/zport/dmd/process#processTree:" + id


def Service(ob):
    id = ".".join(ob.getPhysicalPath())
    if id.startswith(".zport.dmd.Services.WinService"):
        return "/zport/dmd/winservice#navTree:" + id
    return "/zport/dmd/ipservice#navTree:" + id


def MonitoringTemplate(ob):
    """
    Templates for devices are in the new Monitoring Templates screen.
    Collector templates however, are still edited in the old style.
    """
    id = "/".join(ob.getPhysicalPath())
    if id.startswith("/zport/dmd/Devices"):
        return "/zport/dmd/template#templateTree:" + id
    view = getImmediateView(ob)
    return "%s/%s" % (id, view)


def ReportClass(ob):
    id = ".".join(ob.getPhysicalPath())
    return "/zport/dmd/reports#reporttree:" + id


def CustomReport(ob):
    """
    The reportmail utility needs to get at what is the content of the
    backcompat iframe on the reports screen, and existing reportmail setups
    exist that are sending out reports using the old urls with paths
    that resemble the model hierarchy.

    On the other hand, those same old model based urls exist in some places
    in the app (ZenPack provides table for instance) and need to take the user
    into the new reports screen.
    """
    if (
        ob.REQUEST["QUERY_STRING"].find("adapt=false") != -1
        or ob.REQUEST["HTTP_REFERER"].find("/view" + ob.meta_type) != -1
    ):
        params = []
        for key in ob.REQUEST.form.keys():
            params.append("%s=%s" % (key, ob.REQUEST.form[key]))
        return (
            ob.absolute_url_path()
            + "/view"
            + ob.meta_type
            + ("?" + "&".join(params))
            if params
            else ""
        )
    id = ".".join(ob.getPhysicalPath())
    return "/zport/dmd/reports#reporttree:" + id


def MibNode(ob):
    id = "/".join(ob.getPhysicalPath()).split("/nodes/")[0]
    return "/zport/dmd/mibs#mibtree:" + id


def MibNotification(ob):
    id = "/".join(ob.getPhysicalPath()).split("/notifications/")[0]
    return "/zport/dmd/mibs#mibtree:" + id


def MibClass(ob):
    id = "/".join(ob.getPhysicalPath())
    return "/zport/dmd/mibs#mibtree:" + id
