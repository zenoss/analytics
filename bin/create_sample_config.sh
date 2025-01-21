#!/bin/bash
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


#
# If no configuration file exists, create a sample one.
#

. $ZENHOME/bin/zenfunctions

cd daemons
for daemonctl in * ; do
     PRGNAME=`awk -F= '/^PRGNAME=/ { print $2; }' $daemonctl | sed -e 's/\.py//' | tail -1`

     #echo "PRGNAME $PRGNAME"

     #
     # Expand any variables used to define the config file
     #
     eval CFGFILE=`awk -F= '/^CFGFILE=/ { print $2; }' $daemonctl | tail -1`
     #echo "CFGFILE $CFGFILE"

     #
     # Some sanity checks...
     #
     if [ -z "$CFGFILE" ] ; then
         echo "No configuration file for $PRGNAME found"
         continue

     elif [ $CFGFILE == '/dev/null' ] ; then
         echo "No configuration file for $PRGNAME"
         continue
     fi

     #
     # Don't overwrite possibly user-customized files!
     #
     if [ ! -f $CFGFILE ] ; then
        $PRGNAME genconf > /dev/null
        if [ "$?" -eq "0" ]; then
            echo "Creating configuration file for $PRGNAME..."
            `$PRGNAME genconf > $CFGFILE`
            chmod 0600 $CFGFILE
        fi
     fi
done

#
# Don't cause troubles if one of the above steps had issues.
#
exit 0
