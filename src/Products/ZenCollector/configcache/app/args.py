##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import argparse as _argparse

from Products.ZenUtils.terminal_size import (
    get_terminal_size as _get_terminal_size,
)


def get_arg_parser(description, epilog=None):
    parser = _argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=ZenHelpFormatter,
    )
    _fix_optional_args_title(parser)
    return parser


def get_subparser(subparsers, name, description=None, parent=None):
    subparser = subparsers.add_parser(
        name,
        description=description + ".",
        help=description,
        parents=[parent] if parent else [],
        formatter_class=ZenHelpFormatter,
    )
    _fix_optional_args_title(subparser, name.capitalize())
    return subparser


def _fix_optional_args_title(parser, title="General"):
    for grp in parser._action_groups:
        if grp.title == "optional arguments":
            grp.title = "{} Options".format(title)


class ZenHelpFormatter(_argparse.ArgumentDefaultsHelpFormatter):
    """
    Derive to set the COLUMNS environment variable when displaying help.
    """

    def __init__(self, *args, **kwargs):
        size = _get_terminal_size()
        kwargs["width"] = size.columns - 2
        super(ZenHelpFormatter, self).__init__(*args, **kwargs)
