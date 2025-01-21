#!/bin/bash
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


#
# This script modifies ZenPacks that will prevent v3.0 from starting up and
# completing an upgrade process. These ZenPacks will then be upgraded
# following the upgrade of core and will be functional again.
#
PATCHCMD="patch -s -N"
find_zenpack()
{
    local zenpack_name="$1"
    unset zenpack_dir

    for zenpack in ${ZENHOME}/ZenPacks/ZenPacks*
    do
        if [[ "$zenpack" =~ "${zenpack_name}" ]]; then
            if [ -f "$zenpack" ]; then
                zenpack_dir=`head -n1 "$zenpack"`
            elif [ -d "$zenpack" ]; then
                zenpack_dir="$zenpack"
            fi
        fi
    done
}

if [ -z "$ZENHOME" ] ; then
    echo ERROR: '$ZENHOME' is not set.
    echo This is usually caused by executing this command as root rather than \
as the zenoss user.  Either define '$ZENHOME' or run this command as a \
different user.
else
    # Setup zenoss-friendly executable search path...especially for stacks.
    . $ZENHOME/bin/zenfunctions

    #
    # The Advanced Search that shipped with 3.1 deleted the saved searches
    # when you upgraded. Patch it to not do that.
    #
    zenpack_name="AdvancedSearch"
    find_zenpack "${zenpack_name}"
    init_file="${zenpack_dir}/ZenPacks/zenoss/${zenpack_name}/__init__.py"

    if [ -f "${init_file}" ]; then
        $PATCHCMD  "${init_file}" > /dev/null 2>&1 <<__EOF__
--- __init__.py.orig    2011-06-02 13:23:29.000000000 -0500
+++ __init__.py 2011-06-02 13:24:29.000000000 -0500
@@ -38,9 +38,9 @@

     def remove(self, dmd, leaveObjects=False):
         super(ZenPack, self).remove(dmd, leaveObjects)
-
-        # if we have a search manager remove it
-        for userProperties in dmd.ZenUsers.getUsers():
-            userSetting = dmd.ZenUsers._getOb(userProperties.getId())
-            if userSetting.hasObject(SEARCH_MANAGER_ID):
-                userSetting._delObject(SEARCH_MANAGER_ID)
+        if not leaveObjects:
+            # if we have a search manager remove it
+            for userProperties in dmd.ZenUsers.getUsers():
+                userSetting = dmd.ZenUsers._getOb(userProperties.getId())
+                if userSetting.hasObject(SEARCH_MANAGER_ID):
+                    userSetting._delObject(SEARCH_MANAGER_ID)
__EOF__
    fi

fi
