##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from zope.interface import Interface


class IReturnPayloadProcessor(Interface):
    """
    Implementers process returned data from callhome
    """

    def process(dmd, data):
        """
        Process returned Callhome data. These must be named adapters, and the
        name of the adapter should correspond to the its key in the callhome
        return payload.

        @param dmd: Reference to dmd
        @param data: Callhome return payload
        @return: None
        """
