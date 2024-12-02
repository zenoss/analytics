##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging

from collections import defaultdict

log = logging.getLogger("zen.zentrap")


class LegacyVarbindProcessor(object):
    MODE = 0

    def __init__(self, oid2name):
        self.oid2name = oid2name

    def __call__(self, varbinds):
        result = defaultdict(list)
        for oid, value in varbinds:
            base_name = self.oid2name(oid, exactMatch=False, strip=True)
            full_name = self.oid2name(oid, exactMatch=False, strip=False)
            result[base_name].append(str(value))
            if base_name != full_name:
                suffix = full_name[len(base_name) + 1 :]
                result[base_name + ".ifIndex"].append(suffix)
        return {name: ",".join(vals) for name, vals in result.iteritems()}


class DirectVarbindProcessor(object):
    MODE = 1

    def __init__(self, oid2name):
        self.oid2name = oid2name

    def __call__(self, varbinds):
        result = defaultdict(list)
        for oid, value in varbinds:
            base_name = self.oid2name(oid, exactMatch=False, strip=True)
            full_name = self.oid2name(oid, exactMatch=False, strip=False)
            result[full_name].append(str(value))
            if base_name != full_name:
                suffix = full_name[len(base_name) + 1 :]
                result[base_name + ".sequence"].append(suffix)
        return {name: ",".join(vals) for name, vals in result.iteritems()}


class MixedVarbindProcessor(object):
    MODE = 2

    def __init__(self, oid2name):
        self.oid2name = oid2name

    def __call__(self, varbinds):
        result = defaultdict(list)
        groups = defaultdict(list)

        # Group varbinds having the same MIB Object name together
        for key, value in varbinds:
            base_name = self.oid2name(key, exactMatch=False, strip=True)
            full_name = self.oid2name(key, exactMatch=False, strip=False)
            groups[base_name].append((full_name, str(value)))

        # Process each MIB object by name
        for base_name, data in groups.items():
            offset = len(base_name) + 1

            # If there's only one instance for a given object, then add
            # the varbind to the event details using pre Zenoss 6.2.0 rules.
            if len(data) == 1:
                full_name, value = data[0]
                result[base_name].append(value)

                suffix = full_name[offset:]
                if suffix:
                    result[base_name + ".ifIndex"].append(suffix)
                continue

            # Record the varbind instance(s) in their 'raw' form.
            for full_name, value in data:
                suffix = full_name[offset:]
                result[full_name].append(value)
                if suffix:
                    result[base_name + ".sequence"].append(suffix)
        return {name: ",".join(vals) for name, vals in result.iteritems()}
