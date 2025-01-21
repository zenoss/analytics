#!/bin/bash
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

ZP_NAME=MultiRealmIP
FIXED_VERSION=2.2.4
EGG=`find /opt/zenoss/ZenPacks/ -name ZenPacks.zenoss.${ZP_NAME}* | head -n 1`
function version_gt() { test "$(printf '%s\n' "$@" | sort -V | head -n 1)" != "$1"; }

if [[ -z "$EGG" ]]; then
  exit
else
  CURRENT_VERSION=$(echo $EGG| cut -d'-' -f 2)
  if version_gt $FIXED_VERSION $CURRENT_VERSION; then
    echo "ZenPacks.zenoss.${ZP_NAME}-${CURRENT_VERSION}-py2.7.egg needs patching. Issue ZEN-29563"
    FILE_TO_PATCH=$EGG/ZenPacks/zenoss/${ZP_NAME}/__init__.py
    patch -N $FILE_TO_PATCH <<__EOF__
--- __init__.py
+++ __init__.py
@@ -47,8 +47,6 @@ Important Methods that are changed are:

 """

-__import__('pkg_resources').declare_namespace(__name__)
-
 import os
 import os.path
__EOF__
  fi
fi

