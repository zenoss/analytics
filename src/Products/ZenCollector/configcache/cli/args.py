##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import argparse

import six


class MultiChoice(argparse.Action):
    """Allow multiple values for a choice option."""

    def __init__(self, option_strings, dest, **kwargs):
        kwargs["type"] = self._split_listed_choices
        super(MultiChoice, self).__init__(option_strings, dest, **kwargs)

    @property
    def choices(self):
        return self._choices_checker

    @choices.setter
    def choices(self, values):
        self._choices_checker = _ChoicesChecker(values)

    def _split_listed_choices(self, value):
        if "," in value:
            return tuple(value.split(","))
        return value

    def __call__(self, parser, namespace, values=None, option_string=None):
        if isinstance(values, six.string_types):
            values = (values,)
        setattr(namespace, self.dest, values)


class _ChoicesChecker(object):
    def __init__(self, values):
        self._choices = values

    def __contains__(self, value):
        if isinstance(value, (list, tuple)):
            return all(v in self._choices for v in value)
        else:
            return value in self._choices

    def __iter__(self):
        return iter(self._choices)


_devargs_parser = None


def get_devargs_parser():
    global _devargs_parser
    if _devargs_parser is None:
        _devargs_parser = argparse.ArgumentParser(add_help=False)
        _devargs_parser.add_argument(
            "-m",
            "--collector",
            type=str,
            default="*",
            help="Name of the performance collector.  Supports simple '*' "
            "wildcard comparisons.  A lone '*' selects all collectors.",
        )
        _devargs_parser.add_argument(
            "-s",
            "--service",
            type=str,
            default="*",
            help="Name of the configuration service.  Supports simple '*' "
            "wildcard comparisons.  A lone '*' selects all services.",
        )
        _devargs_parser.add_argument(
            "device",
            nargs="*",
            default=argparse.SUPPRESS,
            help="Name of the device.  Multiple devices may be specified. "
            "Supports simple '*' wildcard comparisons. Not specifying a "
            "device will select all devices.",
        )
    return _devargs_parser
