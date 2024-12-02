# ZenPack Template
This README describes the structure of the ZenPack template that gets
automatically created by Zenoss when you add a ZenPack through the web
interface.

## Files
At the top-level a ZenPack must have a setup.py. Almost always a MANIFEST.in
file should exist, and in cases where external dependencies must be built for
inclusion in the ZenPack, a GNUmakefile. Examples of these files with inline
comments are included in this template.

Also included in the ZenPackTemplate is a configure.zcml. As more of Zenoss'
extensibility moves to using ZCA (Zope Component Architecture) this file
becomes crucial to hooking into various aspects of Zenoss.

## Files and Subdirectories
The following sections describe the purpose and use for each of the default
subdirectories. Note that if the described functionality is not of use in your
ZenPack it is safe to remove any of the default directories.

### src/
The src/ top-level directory in ZenPacks is the conventional place to add
third-party dependencies to your ZenPack. It should only be used as a staging
area to do any build work necessary for the dependency.

See GNUmakefile (or GNUmakefile.example) for examples of how to have
your third-party dependencies automatically compiled and installed at the right
time and into the right location.

### ZenPacks/NAMESPACE/PACKNAME/
The following sections describe the directories contained within the
namespaced ZenPacks/NAMESPACE/PACKNAME/ subdirectories.

#### bin/
Any general tools delivered by your ZenPack that would be used by the Zenoss
administrator at the command line should go into this directory by convention.
When the ZenPack is installed all files in this directory will be made
executable.

#### browser/
The browser subdirectory should contain all code and configuration that's
specific to the Zenoss web interface. The provided configure.zcml will
automatically load the example browser/configure.zcml and register the
browser/resources/ subdirectory to serve static web content.

#### daemons/
All files in the daemons/ subdirectory get special handling. Upon installing
the ZenPack, the following actions will occur.

    1. The file will be made executable (chmod 0755)
    2. A symlink to the file will be created in $ZENHOME/bin/
    3. An configuration file will be generated at $ZENHOME/etc/DAEMON_NAME.conf

Assuming that you don't have a $ZENHOME/etc/DAEMONS_TXT_ONLY file this daemon
will also become part of the normal zenoss start and stop processes.

You can find an example daemon control script in daemons/zenexample. For most
purposes this file can be renamed to the name of the daemon you want to create
and modified to change the DAEMON_NAME. No other modifications are typically
needed. Note that this example control script does expect to launch the real
daemon code which should be located at ../DAEMON_NAME.py.

In addition a ControlCenter service will be created for each file in this
subdirectory.  This behavior can be overridden by placing alternate service
definitions in the service_definition subdirectory.

#### datasources/
Any new datasource types you want to add must be added as classes into the
datasources/ subdirectory. When Zenoss is building the list of available
datasources it will scan the datasources/ subdirectory for all installed
ZenPacks.

An example datasource at datasources/ExampleDataSource.py.example.

#### lib/
The lib/ directory should be the installation target for any third-party
libraries that are built by the GNUmakefile. It can also be used as the
conventional location to drop Python-only libraries that don't require
any compilation or special installation.

#### libexec/
Any scripts executed by COMMAND datasources in your ZenPack go in this
directory by convention. When the ZenPack is installed all files in this
directory will be made executable.

#### migrate/
ZenPacks can include migrate scripts that allow you to run custom code to
handle any tasks that are needed to upgrade your ZenPack from one version to
another. All .py files in this migrate/ subdirectory will be evaluated when the
ZenPack is installed.

You can find an example migrate script at migrate/ExampleMigration.py.

#### modeler/
Any modeler plugins distributed with your ZenPack must be located under the
plugins/ subdirectory. The directory structure and filenames under plugins/
map directly to the plugins' name in the user interface. For example, if you
wanted to create a modeler plugin called "community.snmp.ExampleMap" you would
create the following directory structure.

It is recommended that the first portion of the namespace be a short lowercase
form of your name, or organization's name. Alternatively you can choose to use
"community" if you plan to publish the ZenPack and are open to outside
contributions. Zenoss, Inc. will always use "zenoss." The second portion of the
namespace can be the protocol that is used to collect the data. If you are not
using a common protocol it is acceptable to skip the second portion of the
namespace and have something like "community.MongoDB" instead.

plugins/
    __init__.py
    community/
        __init__.py
        snmp/
            __init__.py
            ExampleMap.py

Note that the __init__.py files must exist and should be empty files. Otherwise
your modeler plugins won't be imported and usable within Zenoss.

#### objects/
All .xml files in this objects/ directory will be loaded into the object
database when the ZenPack installs. All of the objects defined in the XML files
will be automatically associated with the ZenPack.

When you export the ZenPack from the user interface all objects associated with
the ZenPack will be exported into a file called "objects.xml" specifically. For
this reason it is recommended to let Zenoss manage the objects.xml file and to
never manually create or modify any .xml files in this directory unless you
know what you're doing.

When a ZenPack is removed, any objects associated with the ZenPack will be
recursively removed from Zenoss. For example, if you associated the /Server
device class with your ZenPack and removed the ZenPack, the /Server device
class, and all devices within it would also be deleted.

When a ZenPack is upgraded, or re-installed on top of itself, all objects in
the XML files are overlaid on the existing object database. This results in a
merge of the existing objects and what are defined in the XML files with the
XML file properties and relationships winning any conflicts.

#### reports/
Custom reports will be loaded from this directory when the ZenPack is
installed. Subdirectories (with the exception of plugins/) will be mapped
directly to the report folders in the web interface. So if you add a .rpt file
into a subdirectory named "Performance Reports" you will find your report in
the Performance Reports folder in the web interface after installing the
ZenPack.

The plugins/ subdirectory should include any Python plugins your custom reports
call. So if your .rpt file contains a line such as the following..

objects python:here.ReportServer.plugin('myplugin', tableState);

There should be a corresponding myplugin.py file in the plugins/ subdirectory.

You can find an example report at Example Reports/Example Report.rpt.example
that uses a plugin which can be found at plugins/example_plugin.py.

#### service_definitions/
ControlCenter services are defined in this subdirectory.  See the example file
and documentation located there for more information.

#### services/
ZenHub services will be loaded from the services/ directory. These services
run inside the zenhub daemon and are responsible from all interaction with
collector daemons.

You can find an example service at services/ExampleConfigService.py.

#### tests/
All unit tests for your ZenPack should live in this directory. You can find an
example test suite at tests/testExample.py.
