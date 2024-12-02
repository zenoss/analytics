##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

""" Redactor

Redact fields from dictionaries within arbitrarily complex objects.
Useful for removing passwords from objects when logging.
"""


def keymatch(k, v, candidates=[]):
    """
    Default Callback for redact function.
    :param k: dictionary item key
    :param v: dictionary item value
    :param candidates: list of candidate strings
    :return: "<REDACTED>" if k is in candidate list. Else, v
    """
    if k in candidates:
        return "<REDACTED>"
    return v


def redact(obj, names=[], callback=keymatch):
    """
    Replace specific (e.g. password) fields in a complex data structure
    Iterates recursively through obj, looking for dictionary entries with a
    key matching the 'name' parameter.
    Any dictionary entries matching 'name' have their values replaced
    with the result of a call to callback.
    :param obj: The data structure to redact
    :param names: Array of names of dictionary key to redact
    :param callback: Function to replace dictionary values.
    :return: copy of object with redactions done as appropriate
    """
    if isinstance(obj, dict):
        return {k: redact(callback(k, v, names), names, callback)
                for k, v in obj.items()}
    elif isinstance(obj, list):
        return [redact(elem, names, callback) for elem in obj]
    else:
        return obj
