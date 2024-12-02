##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import importlib
import os

from unittest import TestCase

from Products.ZenModel import ZMigrateVersion
from Products.ZenModel.migrate import Migrate

_cwd = os.path.dirname(__file__)
_migrate_path = os.path.abspath(os.path.join(_cwd, ".."))


class VerifyMigrateVersion(TestCase):
    """Verifies that the migration scripts have the correct version numbers."""

    def test_version(self):
        current_version = Migrate.Version(
            ZMigrateVersion.SCHEMA_MAJOR,
            ZMigrateVersion.SCHEMA_MINOR,
            ZMigrateVersion.SCHEMA_REVISION,
        )
        module_names = (
            name[:-3]
            for name in os.listdir(_migrate_path)
            if name.endswith(".py")
        )
        failures = []
        for mname in module_names:
            module_path = "Products.ZenModel.migrate." + mname
            module = importlib.import_module(module_path)
            steps = (
                cls
                for cls in (getattr(module, name) for name in dir(module))
                if isinstance(cls, type) and issubclass(cls, Migrate.Step)
            )
            for step in steps:
                step_version = getattr(step, "version", None)
                if step_version and step_version > current_version:
                    failures.append(module_path)
        expected = 0
        actual = len(failures)
        self.assertEqual(
            expected, actual,
            msg="The following migrate script%s a version "
            "greater than %s: %s" % (
                " has" if actual == 1 else "s have",
                current_version.short(),
                ', '.join(failures),
            ),
        )
