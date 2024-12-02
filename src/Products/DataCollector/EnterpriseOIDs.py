##############################################################################
#
# Copyright (C) Zenoss, Inc. 2025, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import collections
import json
import re
import unicodedata

from zenoss.pen import PEN_ORG_FILE


class _EnterpriseOIDs(collections.Mapping):
    def __init__(self, *args, **kw):
        self.__oids = {}
        super(_EnterpriseOIDs, self).__init__(*args, **kw)

    def __getitem__(self, key):
        self.__load()
        return self.__oids[key]

    def __iter__(self):
        self.__load()
        return iter(self.__oids)

    def __len__(self):
        self.__load()
        return len(self.__oids)

    def __load(self):
        if self.__oids:
            return
        if not PEN_ORG_FILE.exists():
            return
        with open(PEN_ORG_FILE.as_posix(), "r") as f:
            self.__oids.update(json.load(f, object_pairs_hook=_as_bytes))


EnterpriseOIDs = _EnterpriseOIDs()


_control_chars_regex = re.compile(r"[^\w!.,<>@#$%^&*\/():\"']")


def _as_bytes(pairs):
    return {str(k): str(_encode(v)) for k, v in pairs}


def _encode(value):
    val = unicodedata.normalize("NFKD", value).encode("ascii", "ignore")
    return _control_chars_regex.sub(" ", val).strip()
