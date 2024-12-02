# Migrations

# Table of Contents
  - [Overview](#overview)
    - [Model Migrations](#model-migrations)
      - [Writing a new migration](#writing-a-new-migration)
    - [ Service Migrations](#service-migrations)
    - [Managing Migrate.Version](#managing-migrateversion)
      - [Starting a new release](#starting-a-new-release)
      - [Working with SCHEMA versions](#working-with-schema-versions)
      - [Release Process](#release-process)
    - [Running a migration manually](#running-a-migration-manually)

# Overview

There are 2 types of migrations, both of which are discussed below

## Model Migrations

These are migrations that affect the Zenoss model database, and possibly other zenoss-specific components.

### Writing a new migration

Below is an example migration script:

``` python
# addAttribute.py

from __future__ import absolute_import

import logging

from ..ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION
from . import Migrate

log = logging.getLogger("zen.migrate")


class AddAttribute(Migrate.Step):
    """Add 'myattr' to /Devices."""

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        dmd.Devices.myattr = "Hi there!"


AddAttribute()
```

The basic steps of a migration script are:

    - Define a new Migrate.Step subclass and set its version
    - Define the step's cutover method
        - Modify the database as needed.
    - Instantiate the class once to register it with the Migrate framework

```
TODO: Expand on this.
```

## Service Migrations

*NOTE* Service migrations using the model migration framework is now deprecated.  Please add service migrations to the
zenservicemigration package found in the zenoss-service repository.

The [service migration SDK](https://github.com/control-center/service-migration/) provides
a programmatic way of making changes to service definitions.

## Managing Migrate.Version

`Migrate.Version()` is used by the upgrade framework to control which migrations
are executed when a particular version of Zenoss is upgraded.  The basic idea is
that the `upgrade` command for the Zope service will execute all of the
migrations with a value greater than the current value stored in Zope. Upon
successful completion of the upgrade, the value of the highest migration script
is then stored in the database.

In order to better manage the values used across a range of different releases,
we have implemented a semi-automated scheme to minimize the process of manually
specifying different values for `Migrate.Version()`.

### Starting a new release

At the start of a new release, the toplevel makefile should be updated to set
the values of SCHEMA_MAJOR, SCHEMA_MINOR, & SCHEMA_REVISION to the appropriate
versions for that release.

Each new migration script added for that release should set `Migrate.Version()`
as follows:

```
from ..ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION
...
    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)
```

### Working with SCHEMA versions

The regular `make` process for prodbin, as well as `zendev devimg` and `zendev test`
will invoke the make target `generate-zversion` which will build ZMigrateVersion.py from ZMigrateVersion.py.in
using the values of SCHEMA_MAJOR, SCHEMA_MINOR, & SCHEMA_REVISION defined in the
toplevel makefile.  In this way, developers working on a new release do not need
to specify explicit versions - they can rely on the build process to inject values
for a given release.  By the same token, changes can be backported to earlier
releases without working about which versions to use for different releases because
the toplevel makefile in each release should define the values unique to that release.

### Release Process

As one of the final steps in the release process, someone must run `make replace-zmigrateversion`
which will edit all of the files in src/model/migrate, replacing the variables
SCHEMA_MAJOR, SCHEMA_MINOR, & SCHEMA_REVISION with the versions defined in the makefile.

Those changes can be verified with `make verify-explicit-zmigrateversion:` which will fail
if any files were overlooked.  If `make replace-zmigrateversion` was unable to update
the a version for some unexpected reason, the migration script can be changed manually
if necessary at this stage.

After the migration scripts have been updated, then they must be checked into git before
executing the git-flow-release process.

## Running a migration manually

Instructions for running a migration manually are available on the engineering site [here](https://sites.google.com/a/zenoss.com/engineering/home/faq/work-with-rm/howtorunzenmigrate).

