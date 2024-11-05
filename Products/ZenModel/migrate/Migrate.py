##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

'''Migrate

A small framework for data migration.

'''

from __future__ import print_function

import re

import transaction
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenUtils.Version import Version as VersionBase
from Products.ZenReports.ReportLoader import ReportLoader
from Products.ZenUtils.path import zenPath
from Products.ZenModel.ZVersion import VERSION
from Products.ZenUtils.terminal_size import get_terminal_size

import sys
from textwrap import wrap
import logging
log = logging.getLogger('zen.migrate')
HIGHER_THAN_CRITICAL = 100
allSteps = []

class MigrationFailed(Exception): pass

class Version(VersionBase):
    def __init__(self, *args, **kw):
        VersionBase.__init__(self, 'Zenoss', *args, **kw)


def cleanup():
    "recursively remove all files ending with .pyc"
    import os
    count = 0
    for p, d, fs in os.walk(zenPath('Products')):
        for f in fs:
            if f.endswith('.pyc'):
                fullPath = os.path.join(p, f)
                os.remove(fullPath)
                count += 1
    log.debug('removed %d .pyc files from Products' % count)


class Step(object):
    'A single migration step, to be subclassed for each new change'

    # Every subclass should set this so we know when to run it
    version = -1
    dependencies = None


    def __init__(self):
        "self insert ourselves in the list of all steps"
        allSteps.append(self)

    def __eq__(self, other):
        if not isinstance(other, Step):
            return False
        if self is other:
            return True
        return (
            self.version == other.version
            and self.dependencies == other.dependencies
        )

    def __lt__(self, other):
        if not isinstance(other, Step):
            return NotImplemented
        if self is other:
            return False
        if self.version > other.version:
            return False
        return self._equivalency(other)

    def __le__(self, other):
        if not isinstance(other, Step):
            return NotImplemented
        if self is other:
            return True
        return self._equivalency(other)

    def _equivalency(self, other):
        if self.version > other.version:
            return False
        if self.version == other.version:
            if self in other.getDependencies():
                return True
            if other in self.getDependencies():
                return False
            return self.name() < other.name()
        return True

    def getDependencies(self):
        if not self.dependencies:
            return []
        result = []
        for d in self.dependencies:
            if d is not self:
                result.append(d)
                result.extend(d.getDependencies())
            else:
                log.error("Circular dependency among migration Steps: "
                          "%s is listed as a dependency of %s ",
                          self.name(), d.name())
        return result

    def prepare(self):
        "do anything you must before running the cutover"
        pass

    def cutover(self, dmd):
        "perform changes to the database"
        raise NotImplementedError

    def cleanup(self):
        "remove any intermediate results"
        pass

    def revert(self):
        pass

    def name(self):
        return self.__class__.__name__

    def log_progress(self, message):
        if sys.stdout.isatty():
            sys.stdout.write("\r" + message)
            sys.stdout.flush()
        else:
            log.info(message)


class Migration(ZenScriptBase):
    "main driver for migration: walks the steps and performs commit/abort"

    useDatabaseVersion = True

    def __init__(self, noopts=0):
        ZenScriptBase.__init__(self, noopts=noopts, connect=False)
        self.connect()
        self.allSteps = allSteps[:]
        self.allSteps.sort() # _must_ sort the dependencies

        # Log output to a file
        # self.setupLogging() does *NOT* do what we want.
        logFilename = zenPath('log', 'zenmigrate.log')
        import logging.handlers
        maxBytes = self.options.maxLogKiloBytes * 1024
        backupCount = self.options.maxBackupLogs
        file_handler = logging.handlers.RotatingFileHandler(
              logFilename, maxBytes=maxBytes, backupCount=backupCount)
        stdout_handler = logging.StreamHandler(stream=sys.stdout)
        for handler in file_handler, stdout_handler:
            handler.setFormatter(logging.Formatter(
                    "%(asctime)s %(levelname)s %(name)s: %(message)s",
                    "%Y-%m-%d %H:%M:%S"))
            log.addHandler(handler)

    def message(self, msg):
        log.info(msg)

    def _currentVersion(self):
        """
        Return a VersionBase instance representing the version of the database.
        This also does some cleanup of dmd.version in case in is
        nonexistant, empty or set to a float value.
        """
        if not hasattr(self.dmd, 'version') or not self.dmd.version:
            self.dmd.version = 'Zenoss ' + VERSION
        if type(self.dmd.version) == type(1.0):
            self.dmd.version = "Zenoss 0.%f" % self.dmd.version
        v = VersionBase.parse(self.dmd.version)
        v.name = 'Zenoss'
        return v

    def getEarliestAppropriateStepVersion(self, codeVers=None):
        """
        Return a Version instance that represents the earliest version
        of migrate step appropriate to run with this code base.
        The earliest version is basically the first sprint/alpha release
        for the current minor version.
        codeVers represents the current version of the code.  It exists
        for testing purposes and should usually not be passed in.
        """
        if codeVers is None:
            codeVers = VersionBase.parse('Zenoss %s' % VERSION)
        if codeVers.micro >= 70:
            # We are in a dev/beta release.  Anything back through the start
            # of this dev/beta cycle is appropriate.
            earliestAppropriate = Version(codeVers.major, codeVers.minor, 70)
        elif codeVers.minor > 0:
            # We are in a regular release that is not a  N.0 version.
            # Anything back through the previous dev/beta cycle is
            # appropriate
            earliestAppropriate = Version(codeVers.major, codeVers.minor-1, 70)
        else:
            # This is a X.0.Y release.  This is tough because we don't know
            # what the minor version was for the last release of version X-1.
            # We take the reasonable guess that the last version of X-1 that
            # we see migrate steps for was indeed the last minor release
            # of X-1.
            beforeThis = Version(codeVers.major)
            # self.allSteps is ordered by version, so just look back through
            # all steps for the first one that predates beforeThis.
            for s in reversed(self.allSteps):
                if s.version < beforeThis:
                    lastPrevious = s.version
                    break
            else:
                # We couldn't find any migrate step that predates codeVers.
                # Something is wrong, this should never happen.
                raise MigrationFailed('Unable to determine the appropriate '
                    'migrate script versions.')
            if lastPrevious.micro >= 70:
                earliestAppropriate = Version(lastPrevious.major,
                        lastPrevious.minor, 70)
            else:
                earliestAppropriate = Version(lastPrevious.major,
                        lastPrevious.minor-1, 70)
        return earliestAppropriate


    def determineSteps(self):
        """
        Return a list of steps from self.allSteps that meet the criteria
        for this migrate run
        """
        # Ensure all steps have version numbers
        for step in self.allSteps:
            if step.version == -1:
                raise MigrationFailed("Migration %s does not set "
                                      "the version number" %
                                      step.__class__.__name__)

        # Level was specified
        if self.options.level is not None:
            levelVers = VersionBase.parse('Zenoss ' + self.options.level)
            steps = [s for s in self.allSteps
                        if s.version >= levelVers]

        # Step was specified
        elif self.options.steps:
            import re
            def matches(name):
                for step in self.options.steps:
                    if re.match('.*' + step + '.*', name):
                        return True
                return False
            steps = [s for s in self.allSteps if matches(s.name())]
            if not steps:
                log.error("No steps found that matched '%s'",
                           ', '.join(self.options.steps))
                log.error("Aborting")
                sys.exit(1)
            log.info("Will execute these steps: %s",
                     ', '.join(self.options.steps))

        else:
            currentDbVers = self._currentVersion()
            # The user did not specify steps to be run, so we run the default
            # steps.
            newDbVers = max(self.allSteps, key = lambda x:x.version).version
            if currentDbVers == newDbVers:
                # There are no steps newer than the current db version.
                # By default we rerun the steps for the current version.
                # If --newer was specified then we run nothing.
                if self.options.newer:
                    steps = []
                else:
                    steps = [s for s in self.allSteps
                                if s.version == currentDbVers]
            else:
                # There are steps newer than the current db version.
                # Run the newer steps.
                steps = [s for s in self.allSteps
                            if s.version > currentDbVers]

        return steps


    def migrate(self, steps, executed):
        """
        Determine the correct migrate steps to run and apply them
        """
        if steps:
            for m in steps:
                m.prepare()
            currentDbVers = self._currentVersion()
            if steps[-1].version > currentDbVers and not self.options.dont_bump:
                self.message('Database going to version %s'
                                               % steps[-1].version.long())
            # hide uncatalog error messages since they do not do any harm
            log = logging.getLogger('Zope.ZCatalog')
            oldLevel = log.getEffectiveLevel()
            log.setLevel(HIGHER_THAN_CRITICAL)
            for m in steps:

                self.message('Installing %s (%s)'
                                % (m.name(), m.version.short()))

                m.cutover(self.dmd)
                executed.append(m)
                if m.version > currentDbVers and not self.options.dont_bump:
                    self.dmd.version = m.version.long()
            for m in steps:
                m.cleanup()
            log.setLevel(oldLevel)
        cleanup()

        if not self.options.steps:
            self.message('Loading Reports')
            rl = ReportLoader(noopts=True, app=self.app)
            # when reports change make sure the new version is loaded during the migrate
            rl.options.force = True
            rl.options.logseverity = self.options.logseverity + 10
            rl.setupLogging()
            rl.loadDatabase()

            # Update JavaScript portlets
            self.dmd.ZenPortletManager.update_source()

    def cutover(self):
        '''perform the migration, applying all the new steps,
        recovering on error'''
        if not self.allSteps:
            self.message('There are no migrate scripts.')
            return
        self.backup()
        steps = self.determineSteps()
        executed = []
        try:
            self.disableTimeout()
            self.migrate(steps, executed)
            if not self.options.steps:
                self.list(steps, executed)
            self.success()
        except Exception:
            log.warning("Recovering")
            self.recover()
            if not self.options.steps:
                self.list(steps, executed)
            raise

    def disableTimeout(self):
        try:
            from ZenPacks.zenoss.CatalogService.service import disableTransactionTimeout
            disableTransactionTimeout()
        except ImportError:
            pass

    def error(self, msg):
        "Deprecated"
        log.error(msg)


    def backup(self):
        pass


    def recover(self):
        transaction.abort()
        steps = self.allSteps[:]
        current = self._currentVersion()
        while steps and steps[0].version < current:
            steps.pop(0)
        for m in steps:
            m.revert()


    def success(self):
        if self.options.commit:
            self.message('Committing changes')
            transaction.commit()
        else:
            self.message('Rolling back changes')
            self.recover()
        self.message("Migration successful")


    def parseOptions(self):
        ZenScriptBase.parseOptions(self)
        if self.args:
            if self.args == ['run']:
                sys.stderr.write('Use of "run" is deprecated.\n')
            elif self.args == ['help']:
                sys.stderr.write('Use of "help" is deprecated,'
                                    'use --help instead.\n')
                self.parser.print_help()
                self.parser.exit()
            elif self.args[0]:
                self.parser.error('Unrecognized option(s): %s\n' %
                    ', '.join(self.args) +
                    'Use --help for list of options.\n')


    def buildOptions(self):
        self.parser.add_option('--step',
                               action='append',
                               dest="steps",
                               help="Run the specified step.  This option "
                                    'can be specified multiple times to run '
                                    'more than one step.')
        # NB: The flag for this setting indicates a false value for the setting.
        self.parser.add_option('--dont-commit',
                               dest="commit",
                               action='store_false',
                               default=True,
                               help="Don't commit changes to the database")
        self.parser.add_option('--list',
                               action='store_true',
                               default=False,
                               dest="list",
                               help="List all the steps")
        self.parser.add_option('--level',
                               dest="level",
                               type='string',
                               default=None,
                               help="Run the steps for the specified level "
                                    ' and above.')
        self.parser.add_option('--newer',
                                dest='newer',
                                action='store_true',
                                default=False,
                                help='Only run steps with versions higher '
                                        'than the current database version.'
                                        'Usually if there are no newer '
                                        'migrate steps the current steps '
                                        'are rerun.')
        self.parser.add_option('--dont-bump',
                               action='store_true',
                               default=False,
                               dest="dont_bump",
                               help="Don't bump database version.")
        ZenScriptBase.buildOptions(self)


    def orderedSteps(self):
        return self.allSteps

    def list(self, inputSteps=None, execSteps=None):
        steps = inputSteps or self.allSteps
        nameWidth = max(list(len(x.name()) for x in steps))
        maxwidth = min(get_terminal_size().columns, 200)
        indentSize = 8 + 3 + nameWidth

        def switch(inp):
            switcher = {
                1: ((" Ver     Name" + " "*(nameWidth-3) + "Status\n"
                       "--------+" + "-"*nameWidth +"+-------"),
                    "%-8s %-{}s %-8s".format(nameWidth+1)),
                0: ((" Ver     Name" + " "*(nameWidth-2) + "Description\n"
                        "--------+" + "-"*(nameWidth+1) +"+-----------"
                        + "-"*(maxwidth - indentSize - 3)),
                    "%-8s %-{}s %s".format(nameWidth+1))
            }
            return switcher.get(inp)
        header, outputTemplate = switch(1 if inputSteps else 0)
        print(header)

        def printState(tpl, version, name, doc=None, status=None):
            if status:
                print(tpl%(version, name, status))
            else:
                print(tpl%(version, name, doc))

        indent = ' ' * indentSize
        docWidth = maxwidth
        for s in steps:
            doc = s.__doc__
            if not doc:
                doc = sys.modules[s.__class__.__module__].__doc__ \
                                                        or 'Not Documented'
            doc.strip()
            doc = re.sub("\s+", " ", doc)
            doc = '\n'.join(wrap(doc, width=docWidth,
                                 initial_indent=indent,
                                 subsequent_indent=indent))
            doc = doc.lstrip()
            if inputSteps:
                if s.name() in (x.name() for x in execSteps):
                    status = "OK"
                else:
                    status = "FAIL"
                printState(outputTemplate, s.version.short(), s.name(), status)
            else:
                printState(outputTemplate, s.version.short(), s.name(), doc)


    def main(self):
        if self.options.list:
            self.list()
            return

        self.cutover()
