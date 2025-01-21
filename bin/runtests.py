#!/usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008-2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""runtests.py

Run unit and Selenium (functional) tests for Zenoss
"""

from __future__ import print_function

import glob
import optparse
import os
import os.path
import re
import sys
import time

from itertools import chain
from subprocess import call

STDOUT = sys.stdout

# Remove script directory from path
scriptdir = os.path.realpath(os.path.dirname(sys.argv[0]))
sys.path[:] = [p for p in sys.path if os.path.realpath(p) != scriptdir]

ZENHOME = os.environ["ZENHOME"]
ZENPACK_HOME = "/var/zenoss/ZenPacks"


def zenhome(*args):
    return os.path.join(ZENHOME, *args)


def zenpackdir(*args):
    return os.path.join(ZENPACK_HOME, *args)


PYTHON = zenhome("bin", "python")
CONFIG = zenhome("etc", "zope.conf")
SOFTWARE_HOME = zenhome("lib", "python")
PRODUCTS = zenhome("Products")

# add SOFTWARE_HOME to sys.path, but only if Zope isn't available
try:
    import imp

    _ = imp.find_module("Zope2")
except ImportError:
    sys.path.insert(0, SOFTWARE_HOME)

exitcodes = []


def runZopeTests(options):
    from zope import testrunner
    from zope.testrunner.options import setup

    def load_config_file(option, opt, config_file, *ignored):
        print("Parsing %s" % config_file)
        import Zope2

        Zope2.configure(config_file)

    setup.add_option(
        "--config-file",
        action="callback",
        type="string",
        dest="config_file",
        callback=load_config_file,
    )

    defaults = "--tests-pattern ^tests$ -v".split()
    defaults += ["--config-file", CONFIG]

    if "-m" not in options:
        defaults += [
            "-m",
            "!^("
            "ZConfig"
            "|"
            "BTrees"
            "|"
            "persistent"
            "|"
            "ThreadedAsync"
            "|"
            "transaction"
            "|"
            "ZEO"
            "|"
            "ZODB"
            "|"
            "ZopeUndo"
            "|"
            "zdaemon"
            "|"
            "zope[.]testing"
            "|"
            "zope[.]app"
            ")[.]",
        ]

    defaults += ["--path", SOFTWARE_HOME]
    defaults += ["--package-path", PRODUCTS, "Products"]
    sys.exit(testrunner.run(defaults, options))


def overrideCoreTests(results):
    """
    Check to see if a commercial skin is installed. If so, don't run the core
    tests.

    @param results: list of directories
    @type results: list of strings
    @return: results without core tests
    @rtype: list of strings
    """
    commercial = False
    for result in results:
        if "Skin" in result:
            commercial = True
    if commercial:
        results.remove(zenhome("Products", "ZenUITests"))
    return results


def findSeleniumTests(packages=None, regex=None):
    """
    Find Selenium tests

    @param packages: packages
    @type packages: string
    @param regex: regular expression to determine to include or not
    @type regex: string
    @return: directories containing Selenium tests
    @rtype: list of strings
    """
    if packages is None:
        packages = []
    prods = findSeleniumTestableProducts(
        packages, regex, testdir="tests/selenium"
    )
    results = []
    if not regex:
        regex = "testAll"
    regex += ".py"
    for prod in prods:
        selpath = os.path.join(prod, "tests", "selenium", regex)
        if os.path.exists(selpath):
            results.append(selpath)
    return results


def demangleEggName(eggdir, name):
    """
    Deals with Python egg edge cases to expand out the directories.
    Python eggs mangle the names, so '-' gets changed
    to '_' at a *lower* level subdirectory.

    @param eggdir: path to the ZenPack
    @type eggdir: string
    @param name: name of the ZenPack
    @type name: string
    @return: path to the ZenPack
    @rtype: string
    """
    path = eggdir
    components = name.split(".", 2)  # ie a list with three items
    # Note, we discard the last item to satisfy findTestableProducts
    for component in components[0:1]:
        if os.path.isdir(os.path.join(path, component)):
            path = os.path.join(path, component)
            continue

        newcomponent = component.split("-", 1)[0] + "*"
        found = glob.glob(os.path.join(os.path.join(path, newcomponent)))
        if len(found) != 1:
            # Ouch! Something bad happened
            print(
                "Unable to find egg directory from %s and %s"
                % (path, component)
            )
            return eggdir
        path = os.path.join(path, found[0])
    return path


def expandPackDir(fulldir):
    """
    Expand Zenoss ZenPack directory names.

    This handles old-style ZenPacks as well as egg-style.

    @param fulldir: path to the ZenPack
    @type fulldir: string
    @return: path to the ZenPack
    @rtype: string
    """
    name = os.path.basename(fulldir)
    if not name.endswith(".egg"):
        # Old-style ZenPack
        return fulldir
    return demangleEggName(fulldir, name)


_packname = re.compile(r"ZenPacks\.[^-/]+\.[^-/]+").search


def zenPackName(s):
    match = _packname(s)
    if match:
        return match.group()
    return None


def findZenPackNames():
    dirs = findZenPackDirectories()
    return filter(None, map(zenPackName, dirs))


def findZenPacksFromDirectory(directory):
    paths = []
    try:
        for item in os.listdir(directory):
            fullpath = os.path.join(directory, item)
            if os.path.isdir(fullpath):
                path = expandPackDir(fullpath)
            elif item.endswith(".egg-link"):
                with open(fullpath) as f:
                    path = expandPackDir(f.readline().strip())
            else:
                continue
            if not path.endswith("ZenPacks"):
                path = os.path.join(path, "ZenPacks")
            paths.append(path)
    except OSError:
        pass
    return paths


def findZenPackDirectories():
    """
    Get the list of ZenPacks with tests

    @return: list of ZenPack directories
    @rtype: list of strings
    """
    return findZenPacksFromDirectory(ZENPACK_HOME) + findZenPacksFromDirectory(
        zenhome("ZenPacks")
    )


def findZenossProducts(include_zenpacks):
    """
    Get all Zenoss products + ZenPacks.
    """
    validProds = [
        "Products." + name
        for name in (
            "DataCollector",
            "Jobber",
            "ZenCallHome",
            "ZenEvents",
            "ZenHub",
            "ZenModel",
            "ZenModel.migrate",
            "ZenRRD",
            "ZenRelations",
            "ZenReports",
            "ZenStatus",
            "ZenUtils",
            "ZenWidgets",
            "Zuul",
            "ZenCollector",
            "ZenMessaging",
        )
    ]
    if include_zenpacks:
        zenpacks = findZenPackNames()
    else:
        zenpacks = []
    return validProds + zenpacks


def isValidPackage(package, validProducts):
    package_seq = package.split(".")
    return any(
        product == ".".join(package_seq[: len(product.split("."))])
        for product in validProducts
    )


def findSeleniumTestableProducts(packages=None, regex=None, testdir="tests"):
    """
    Get the list of Zope Products with tests

    @param packages: packages to run tests
    @type packages: list of strings
    @param regex: regular expression to determine to include or not
    @type regex: string
    @param testdir: directory name containing test files
    @type testdir: string
    @return: list of Zope Product directories
    @rtype: list of strings
    """
    if packages is None:
        packages = []
    results = []
    for target in findZenPackDirectories() + [zenhome("Products")]:
        for root, dirs, _ in os.walk(target):
            # don't look past a lib directory that is under the ZenPacks
            # directory
            rootParts = root.split(os.path.sep)
            if (
                "ZenPacks" in rootParts
                and "lib" in rootParts[rootParts.index("ZenPacks") :]
            ):
                continue

            for dir in dirs:
                if (
                    packages
                    # ZenPacks have a problem unless you do this
                    and target.split("/")[-1] not in packages
                    and dir not in packages
                ):
                    continue
                # Sigh. We need to make sure no-one ends a ZenPack
                # with 'Products'
                if target.endswith("Products"):
                    if (
                        not (dir.startswith("Zen") or dir == "DataCollector")
                        or dir in "ZenTestRunner"
                    ):
                        continue
                newdir = os.path.join(root, dir)
                if testdir in os.listdir(newdir):
                    init_file = os.path.join(newdir, testdir, "__init__.py")
                    if not os.path.exists(init_file):
                        print(
                            "Warning: missing the %s file -- skipping %s"
                        ) % (init_file, target)
                    elif regex:
                        f = os.path.join(newdir, testdir, regex + ".py")
                        if os.path.exists(f):
                            results.append(newdir)
                    else:
                        results.append(newdir)
    results = overrideCoreTests(results)
    if not results:
        print("No %s directories found for %s" % (testdir, packages))
    return results


def runSeleniumTests(
    packages=None, regex=None, zenoss_server=None, selenium_server=None
):
    """
    Run any Selenium tests that match the regular expression.

    @param packages: packages
    @type packages: list of strings
    @param regex: Regular expression
    @type regex: string
    @param zenoss_server: Zenoss server
    @type zenoss_server: string
    @param selenium_server: Selenium server name
    @type selenium_server: string
    """
    if packages is None:
        packages = []
    tests = findSeleniumTests(packages, regex)
    for testscript in tests:
        command = ["python", testscript]
        for arg in (zenoss_server, selenium_server):
            if arg is not None:
                command.append(arg)
        rc = call(command)  # noqa: S603
        exitcodes.append(rc)


def runUnitTests(
    packages=None,
    modules=None,
    names=None,
    coverage="",
    count=0,
    include_zenpacks=True,
):
    """
    Run unit tests for any packages that match the regular expression.

    @param packages: packages
    @type packages: list of strings
    @param regex: regular expression
    @type regex: string
    @param coverage: coverage
    @type coverage: string
    @param show_tests: run or just display the test name?
    @type show_tests: boolean
    """
    valid_packages = findZenossProducts(include_zenpacks)
    if not packages:
        packages = valid_packages
    if modules is None:
        modules = []
    if names is None:
        names = []
    invalid_packages = []
    for pkg in packages:
        if not isValidPackage(pkg, valid_packages):
            packages.remove(pkg)
            invalid_packages.append(pkg)
    print("=" * 30)
    print()
    print("Packages to be tested:")
    for p in packages:
        print("\t" + p)
    print()
    if invalid_packages:
        print("Invalid packages:")
        for p in invalid_packages:
            print("\t" + p)
    print("=" * 30)

    cmdline_args = ["--config-file", CONFIG]

    # Add ZenPack homes to package directories
    for d in findZenPackDirectories():
        path = d.rsplit("/", 1)[0]
        name = zenPackName(d)
        if name in packages or name in modules:
            cmdline_args.extend(["--test-path", path])
            cmdline_args.extend(["--package-path", path, name])
            packdir = os.path.join(path, *name.split("."))
            libdir = os.path.join(packdir, "lib")
            if os.path.exists(libdir):
                cmdline_args.extend(["--ignore_dir", "lib"])

    cmdline_args.extend(chain.from_iterable(["-s", p] for p in packages))
    cmdline_args.extend(chain.from_iterable(["-m", m] for m in modules))
    cmdline_args.extend(chain.from_iterable(["-t", t] for t in names))
    if count:
        cmdline_args.append("-" + ("v" * count))
    if coverage:
        cmdline_args.extend(["--coverage", coverage])
    if packages or modules or names:
        sys.argv[:] = sys.argv[:1]
        runZopeTests(cmdline_args)


usage = """%prog [options] [package1 [package2]]

Run Zenoss tests against specified packages.

Packages are the names of directories in $ZENHOME/Products. If no
packages are specified, tests will be executed against all testable
Zenoss packages.

Valid test types are:
    unit        Run unit tests and doctests.
    selenium    Run selenium tests.
    all         Run all tests.

Individual test modules may also be specified. For example, to run only
the Device tests, use:
    runtests.py --type unit --name testDevice Products.ZenModel

Note that Solr instance need to be up and configured as for BaseTestCase.
"""


def main():
    parser = optparse.OptionParser(prog="runtests.py", usage=usage)
    parser.add_option(
        "-t",
        "--type",
        type="choice",
        choices=("unit", "selenium", "all"),
        default="unit",
        help="The type of tests to run (default: %default)",
    )
    parser.add_option(
        "-c", "--coverage", help="Directory to store coverage stats"
    )
    parser.add_option(
        "-v", dest="count", action="count", help="Verbosity of test output"
    )
    parser.add_option(
        "-m", "--module", action="append", help="The name of a test module."
    )
    parser.add_option(
        "-n", "--name", action="append", help="The name of an individual test"
    )
    parser.add_option(
        "--selenium-server", help="The server hosting the Selenium jar"
    )
    parser.add_option(
        "--zenoss-server",
        help="The Zenoss server against which Selenium should test",
    )
    parser.add_option(
        "-Z",
        "--no-zenpacks",
        dest="no_zenpacks",
        action="store_true",
        default=False,
        help="Only run core tests, even if ZenPacks are installed",
    )
    (options, args) = parser.parse_args()

    if options.type in ("unit", "all"):
        runUnitTests(
            args,
            options.module,
            options.name,
            options.coverage,
            options.count,
            not options.no_zenpacks,
        )

    if options.type in ("selenium", "all"):
        runSeleniumTests(
            args, options.name, options.zenoss_server, options.selenium_server
        )


if __name__ == "__main__":
    start = time.time()
    main()
    if exitcodes:
        code = max(exitcodes)
    else:
        code = 0
    sys.exit(code)
