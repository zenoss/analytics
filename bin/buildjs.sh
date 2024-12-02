#!/bin/bash
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

JSBUILDER=$ZENHOME/share/java/sencha_jsbuilder-2/JSBuilder2.jar
JSHOME=$(python -c "import importlib_resources; print importlib_resources.files('Products.ZenUI3.browser').as_posix()")
java -jar $JSBUILDER -p $JSHOME/zenoss.jsb2 -d $JSHOME -v
exit $?
