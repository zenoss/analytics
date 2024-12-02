##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

__all__ = ("main",)


def main():
    from .configcache import main
    main()


if __name__ == "__main__":
    main()
