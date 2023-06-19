##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import datetime
import logging
import os
import os.path
import re
import sys
import textwrap

from copy import copy
from optparse import (
    BadOptionError,
    NO_DEFAULT,
    Option,
    OptionGroup,
    OptionParser,
    OptionValueError,
    SUPPRESS_HELP,
)
from urllib import quote

import zope.component

from zope.traversing.adapters import DefaultTraversable
from Zope2.App import zcml

from .config import ConfigLoader
from .path import zenPath
from .Utils import (
    getAllParserOptionsGen,
    load_config_override,
    unused,
)
from .GlobalConfig import (
    _convertConfigLinesToArguments,
    getGlobalConfiguration,
)


# List of options to not include when generating a config file.
_OPTIONS_TO_IGNORE = (
    "",
    "configfile",
    "genconf",
    "genxmlconfigs",
    "genxmltable",
    "help",
    "version",
)


class DMDError:
    pass


def remove_args(argv, remove_args_novals, remove_args_vals):
    """
    Removes arguments from the argument list. Arguments in
    remove_args_novals have no arguments. Arguments in
    remove_args_vals have arguments, either in the format
    --arg=<val> or --arg <val>.
    """
    new_args = []
    it = iter(argv)
    for arg in it:
        if arg in remove_args_novals:
            continue
        add_arg = True
        for remove_arg in remove_args_vals:
            if remove_arg == arg:
                add_arg = False
                it.next()  # Skip the argument value
                break
            elif arg.startswith(remove_arg + "="):
                add_arg = False
                break
        if add_arg:
            new_args.append(arg)
    return new_args


def checkLogLevel(option, opt, value):
    if re.match(r"^\d+$", value):
        value = int(value)
    else:
        intval = getattr(logging, value.upper(), None)
        if intval is None:
            raise OptionValueError('"%s" is not a valid log level.' % value)
        value = intval

    return value


class CmdBaseOption(Option):
    TYPES = Option.TYPES + ("loglevel",)
    TYPE_CHECKER = copy(Option.TYPE_CHECKER)
    TYPE_CHECKER["loglevel"] = checkLogLevel


LogSeverityOption = CmdBaseOption


class CmdBase(object):
    """
    Base class used for most Zenoss commands.
    """

    doesLogging = True

    def __init__(self, noopts=0, args=None, should_log=None):
        zope.component.provideAdapter(DefaultTraversable, (None,))
        # This explicitly loads all of the products - must happen first!
        from OFS.Application import import_products

        import_products()
        # make sure we aren't in debug mode
        import Globals

        Globals.DevelopmentMode = False
        # We must import ZenossStartup at this point so that all Zenoss daemons
        # and tools will have any ZenPack monkey-patched methods available.
        import Products.ZenossStartup

        unused(Products.ZenossStartup)
        zcml.load_site()
        import Products.ZenWidgets

        load_config_override("scriptmessaging.zcml", Products.ZenWidgets)

        self.usage = "%prog [options]"
        self.noopts = noopts
        self.inputArgs = args

        # inputArgs was created to allow unit tests to pass in command line
        # arguments and get around whatever Zope was doing to sys.argv.
        if self.inputArgs is None:
            self.inputArgs = sys.argv[1:]

        self.parser = None
        self.args = []

        self.buildParser()
        self.buildOptions()
        # Update the defaults from the config files
        self.parser.defaults.update(
            _get_defaults_from_config([] if self.noopts else self.inputArgs)
        )
        self.parseOptions()

        if should_log is not None:
            self.doesLogging = should_log

        if self.doesLogging:
            self.setupLogging()

    def buildParser(self):
        """
        Create the options parser.
        """
        if not self.parser:
            self.parser = _build_parser()

    def buildOptions(self):
        """
        Basic options setup. Other classes should call this before adding
        more options
        """
        self.buildParser()
        if self.doesLogging:
            group = OptionGroup(self.parser, "Logging Options")
            group.add_option(
                "-v",
                "--logseverity",
                dest="logseverity",
                default="INFO",
                type="loglevel",
                help="Logging severity threshold",
            )
            group.add_option(
                "--logpath",
                dest="logpath",
                default=zenPath("log"),
                type="str",
                help="Override the default logging path; default %default",
            )
            group.add_option(
                "--maxlogsize",
                dest="maxLogKiloBytes",
                default=10240,
                type="int",
                help="Max size of log file in KB; default %default",
            )
            group.add_option(
                "--maxbackuplogs",
                dest="maxBackupLogs",
                default=3,
                type="int",
                help="Max number of back up log files; default %default",
            )
            self.parser.add_option_group(group)

        self.parser.add_option(
            "-C",
            "--configfile",
            dest="configfile",
            help="Use an alternate configuration file",
        )

        self.parser.add_option(
            "--genconf",
            action="store_true",
            default=False,
            help="Generate a template configuration file",
        )

        self.parser.add_option(
            "--genxmltable",
            action="store_true",
            default=False,
            help="Generate a Docbook table showing command-line switches.",
        )

        self.parser.add_option(
            "--genxmlconfigs",
            action="store_true",
            default=False,
            help="Generate an XML file containing command-line switches.",
        )

    def parseOptions(self):
        """
        Uses the optparse parse previously populated and performs common
        options.
        """
        args = [] if self.noopts else self.inputArgs

        (self.options, self.args) = self.parser.parse_args(args=args)

        if self.options.genconf:
            self.generate_configs(self.parser, self.options)

        if self.options.genxmltable:
            self.generate_xml_table(self.parser, self.options)

        if self.options.genxmlconfigs:
            self.generate_xml_configs(self.parser, self.options)

    def loadConfigFile(self, filename):
        """
        Parse a config file which has key-value pairs delimited by white space.

        @parameter filename: path to the configuration file
        @type filename: string
        """
        lines = []
        if not os.path.exists(filename):
            return lines
        try:
            with open(filename) as file:
                for line in file:
                    if line.lstrip().startswith("#") or line.strip() == "":
                        lines.append({"type": "comment", "line": line})
                    else:
                        try:
                            # Add default blank string for keys with no
                            # default value.
                            # Valid delimiters are space, ':' and/or '='
                            # (see ZenUtils/config.py)
                            key, value = (
                                re.split(r"[\s:=]+", line.strip(), maxsplit=1)
                                + [""]
                            )[:2]
                        except ValueError:
                            lines.append(
                                {
                                    "type": "option",
                                    "line": line,
                                    "key": line.strip(),
                                    "value": None,
                                    "option": None,
                                }
                            )
                        else:
                            option = self.parser.get_option("--%s" % key)
                            lines.append(
                                {
                                    "type": "option",
                                    "line": line,
                                    "key": key,
                                    "value": value,
                                    "option": option,
                                }
                            )
        except IOError as e:
            errorMessage = (
                "WARN: unable to read config file {filename} "
                "-- skipping. ({exceptionName}: {exception})"
            ).format(
                filename=filename,
                exceptionName=e.__class__.__name__,
                exception=e,
            )
            print(errorMessage, file=sys.stderr)
            return []

        return lines

    def validateConfigFile(
        self, filename, lines, correctErrors=True, warnErrors=True
    ):
        """
        Validate config file lines which has key-value pairs delimited by
        white space, and validate that the keys exist for this command's
        option parser. If the option does not exist or has an empty value it
        will comment it out in the config file.

        @parameter filename: path to the configuration file
        @type filename: string
        @parameter lines: lines from config parser
        @type lines: list
        @parameter correctErrors: Whether or not invalid conf values should be
            commented out.
        @type correctErrors: boolean
        """
        output = []
        errors = []
        validLines = []
        date = datetime.datetime.now().isoformat()
        errorTemplate = (
            "## Commenting out by config parser (%s) on %s: %%s\n"
            % (sys.argv[0], date)
        )

        for lineno, line in enumerate(lines):
            if line["type"] == "comment":
                output.append(line["line"])
            elif line["type"] == "option":
                if line["value"] is None:
                    errors.append(
                        (lineno + 1, 'missing value for "%s"' % line["key"])
                    )
                    output.append(errorTemplate % "missing value")
                    output.append("## %s" % line["line"])
                elif line["option"] is None:
                    errors.append(
                        (lineno + 1, 'unknown option "%s"' % line["key"])
                    )
                    output.append(errorTemplate % "unknown option")
                    output.append("## %s" % line["line"])
                else:
                    validLines.append(line)
                    output.append(line["line"])
            else:
                errors.append((lineno + 1, 'unknown line "%s"' % line["line"]))
                output.append(errorTemplate % "unknown line")
                output.append("## %s" % line["line"])

        if errors:
            if correctErrors:
                for lineno, message in errors:
                    print(
                        "INFO: Commenting out %s on line %d in %s"
                        % (message, lineno, filename),
                        file=sys.stderr,
                    )

                with open(filename, "w") as file:
                    file.writelines(output)

            if warnErrors:
                for lineno, message in errors:
                    print(
                        "WARN: %s on line %d in %s"
                        % (message, lineno, filename),
                        file=sys.stderr,
                    )

        return validLines, errors

    def getParamatersFromConfig(self, lines):
        # Deprecated: This method is going away
        return _convertConfigLinesToArguments(self.parser, lines)

    def setupLogging(self):
        """
        Set common logging options.
        """
        rlog = logging.getLogger()
        rlog.setLevel(logging.WARN)
        mname = self.__class__.__name__
        self.log = logging.getLogger("zen." + mname)
        zlog = logging.getLogger("zen")
        try:
            loglevel = int(self.options.logseverity)
        except ValueError:
            loglevel = getattr(
                logging, self.options.logseverity.upper(), logging.INFO
            )
        zlog.setLevel(loglevel)

        logdir = self.checkLogpath()
        if logdir:
            logfile = os.path.join(logdir, mname.lower() + ".log")
            maxBytes = self.options.maxLogKiloBytes * 1024
            backupCount = self.options.maxBackupLogs
            h = logging.handlers.RotatingFileHandler(
                logfile, maxBytes=maxBytes, backupCount=backupCount
            )
            h.setFormatter(
                logging.Formatter(
                    "%(asctime)s %(levelname)s %(name)s: %(message)s",
                    "%Y-%m-%d %H:%M:%S",
                )
            )
            rlog.addHandler(h)
        else:
            logging.basicConfig()

    def checkLogpath(self):
        """Validate the logpath is valid."""
        if not self.options.logpath:
            return None
        else:
            logdir = self.options.logpath
            if not os.path.exists(logdir):
                # try creating the directory hierarchy if it doesn't exist...
                try:
                    os.makedirs(logdir)
                except OSError:
                    raise SystemExit(
                        "logpath:%s doesn't exist and cannot be created"
                        % logdir
                    )
            elif not os.path.isdir(logdir):
                raise SystemExit(
                    "logpath:%s exists but is not a directory" % logdir
                )
            return logdir

    def pretty_print_config_comment(self, comment):
        """
        Quick and dirty pretty printer for comments that happen to be longer
        than can comfortably be seen on the display.
        """
        new_comment = textwrap.wrap(comment, width=75)
        return "# " + "\n# ".join(new_comment)

    def _get_default_value(self, parser, opt):
        default_value = parser.defaults.get(opt.dest)
        if default_value is NO_DEFAULT or default_value is None:
            return ""
        return str(default_value)

    def _get_help_text(self, opt, default_value):
        if "%default" in opt.help:
            return opt.help.replace("%default", default_value)
        default_text = ""
        if default_value != "":
            default_text = " [default %s]" % (default_value,)
        return opt.help + default_text

    def generate_configs(self, parser, options):
        """
        Create a configuration file based on the long-form of the option names.

        :param parser: an optparse parser object which contains defaults, help
        :param options: parsed options list containing actual values
        """
        #
        # Header for the configuration file
        #
        unused(options)
        daemon_name = os.path.basename(sys.argv[0])
        daemon_name = daemon_name.replace(".py", "")

        print(
            """#
# Configuration file for %s
#
#  To enable a particular option, uncomment the desired entry.
#"""
            % (daemon_name,)
        )

        #
        # Create an entry for each of the command line flags
        #
        # NB: Ideally, this should print out only the option parser dest
        #     entries, rather than the command line options.
        #
        for opt in getAllParserOptionsGen(parser):
            if opt.help is SUPPRESS_HELP:
                continue

            #
            # Don't include items in the ignore list
            #
            option_name = re.sub(r".*/--", "", "%s" % opt)
            option_name = re.sub(r"^--", "", "%s" % option_name)
            if option_name in _OPTIONS_TO_IGNORE:
                continue

            #
            # Find the actual value specified on the command line, if any,
            # and display it
            #
            default_value = self._get_default_value(parser, opt)
            help_text = self._get_help_text(opt, default_value)
            description = self.pretty_print_config_comment(help_text)

            value = getattr(parser.values, opt.dest)
            if value is None:
                value = default_value

            comment_char = "#" if str(value) == str(default_value) else ""

            #
            # NB: I would prefer to use tabs to separate the parameter name
            #     and value, but I don't know that this would work.
            #
            print(
                "\n".join(
                    (
                        "#",
                        description,
                        "%s%s %s" % (comment_char, option_name, value),
                    )
                )
            )

        #
        # Pretty print and exit
        #
        print("#")
        sys.exit(0)

    def generate_xml_table(self, parser, options):
        """
        Create a Docbook table based on the long-form of the option names

        :param parser: an optparse parser object which contains defaults, help
        :param options: parsed options list containing actual values
        """

        #
        # Header for the configuration file
        #
        unused(options)
        daemon_name = os.path.basename(sys.argv[0])
        daemon_name = daemon_name.replace(".py", "")

        print(
            """<?xml version="1.0" encoding="UTF-8"?>

<section version="4.0" xmlns="http://docbook.org/ns/docbook"
   xmlns:xlink="http://www.w3.org/1999/xlink"
   xmlns:xi="http://www.w3.org/2001/XInclude"
   xmlns:svg="http://www.w3.org/2000/svg"
   xmlns:mml="http://www.w3.org/1998/Math/MathML"
   xmlns:html="http://www.w3.org/1999/xhtml"
   xmlns:db="http://docbook.org/ns/docbook"

  xml:id="{name}.options"
>

<title>{name} Options</title>
<para />
<table frame="all">
  <caption>{name} <indexterm><primary>Daemons</primary><secondary>{name}</secondary></indexterm> options</caption>
<tgroup cols="2">
<colspec colname="option" colwidth="1*" />
<colspec colname="description" colwidth="2*" />
<thead>
<row>
<entry> <para>Option</para> </entry>
<entry> <para>Description</para> </entry>
</row>
</thead>
<tbody>
""".format(  # noqa E501
                name=daemon_name
            )
        )

        #
        # Create an entry for each of the command line flags
        #
        # NB: Ideally, this should print out only the option parser dest
        #     entries, rather than the command line options.
        #
        import re

        for opt in getAllParserOptionsGen(parser):
            if opt.help is SUPPRESS_HELP:
                continue

            #
            # Create a Docbook-happy version of the option strings
            # Yes, <arg></arg> would be better semantically, but the output
            # just looks goofy in a table.  Use literal instead.
            #
            all_options = (
                "<literal>"
                + re.sub(
                    r"/", "</literal>,</para> <para><literal>", "%s" % opt
                )
                + "</literal>"
            )

            #
            # Don't display anything we shouldn't be displaying
            #
            option_name = re.sub(r".*/--", "", "%s" % opt)
            option_name = re.sub(r"^--", "", "%s" % option_name)
            if option_name in _OPTIONS_TO_IGNORE:
                continue

            default_value = self._get_default_value(parser, opt)

            if "%default" in opt.help:
                comment = opt.help.replace("%default", default_value)
            else:
                comment = opt.help

            default_string = ""
            if default_value != "":
                default_string = (
                    "<para> Default: <literal>"
                    + str(default_value)
                    + "</literal></para>\n"
                )

            # comment = self.pretty_print_config_comment(opt.help)

            #
            # TODO: Determine the variable name used and display the
            # --option_name=variable_name
            #
            if opt.action in ["store_true", "store_false"]:
                print(
                    """<row>
<entry> <para>%s</para> </entry>
<entry>
<para>%s</para>
%s</entry>
</row>"""
                    % (all_options, comment, default_string)
                )

            else:
                target = "=<replaceable>" + opt.dest + "</replaceable>"
                all_options = all_options + target
                all_options = re.sub(r",", target + ",", all_options)
                print(
                    """<row>
<entry> <para>%s</para> </entry>
<entry>
<para>%s</para>
%s</entry>
</row>"""
                    % (all_options, comment, default_string)
                )

        #
        # Close the table elements
        #
        print(
            """</tbody></tgroup>
</table>
<para />
</section>
"""
        )
        sys.exit(0)

    def generate_xml_configs(self, parser, options):
        """
        Create an XML file that can be used to create Docbook files
        as well as used as the basis for GUI-based daemon option
        configuration.
        """

        #
        # Header for the configuration file
        #
        unused(options)
        daemon_name = os.path.basename(sys.argv[0]).replace(".py", "")

        export_date = datetime.datetime.now()

        print(
            """<?xml version="1.0" encoding="UTF-8"?>

<!-- Default daemon configuration generated on %s -->
<configuration id="%s" >
"""
            % (export_date, daemon_name)
        )

        #
        # Create an entry for each of the command line flags
        #
        # NB: Ideally, this should print out only the option parser dest
        #     entries, rather than the command line options.
        #
        for opt in getAllParserOptionsGen(parser):
            if opt.help is SUPPRESS_HELP:
                continue

            #
            # Don't display anything we shouldn't be displaying
            #
            option_name = re.sub(r".*/--", "", "%s" % opt)
            option_name = re.sub(r"^--", "", "%s" % option_name)
            if option_name in _OPTIONS_TO_IGNORE:
                continue

            default_value = self._get_default_value(parser, opt)
            help_text = quote(self._get_help_text(opt, default_value))

            #
            # TODO: Determine the variable name used and display the
            # --option_name=variable_name
            #
            if opt.action in ["store_true", "store_false"]:
                params = (
                    ("id", option_name),
                    ("type", "boolean"),
                    ("default", default_value),
                    ("help", help_text),
                )
            else:
                params = (
                    ("id", option_name),
                    ("type", opt.type),
                    ("default", quote(default_value)),
                    ("target", opt.dest),
                    ("help", help_text),
                )
            print(
                "    <option %s />\n"
                % " ".join('%s="%s"' % (k, v) for k, v in params),
                end="",
            )

        #
        # Close the table elements
        #
        print("\n</configuration>")
        sys.exit(0)


def _build_parser(cls=OptionParser):
    from Products.ZenModel.ZenossInfo import ZenossInfo

    try:
        zinfo = ZenossInfo("")
        version = str(zinfo.getZenossVersion())
    except Exception:
        from Products.ZenModel.ZVersion import VERSION

        version = VERSION
    return cls(
        version="%prog " + version,
        option_class=CmdBaseOption,
    )


def _get_defaults_from_config(args):
    overrides = dict(getGlobalConfiguration())

    cparser = _build_parser(cls=_KnownOptionsParser)
    cparser.add_option(
        "-C",
        "--configfile",
        dest="configfile",
    )

    opts, _ = cparser.parse_args(args=args)
    if opts.configfile:
        try:
            appcfg = ConfigLoader(opts.configfile)()
            overrides.update(appcfg)
        except Exception as ex:  # noqa: F841 S110
            # Restore this code when the wrapper scripts no longer
            # add the -C option all the time.
            # print("warning: {}".format(ex), file=sys.stderr)
            pass
    return {key.replace("-", "_"): value for key, value in overrides.items()}


class _KnownOptionsParser(OptionParser):
    """
    Extend OptionParser to skip unknown options and disable --help.
    """

    def __init__(self, *args, **kwargs):
        OptionParser.__init__(self, *args, add_help_option=False, **kwargs)

    def _process_long_opt(self, rargs, values):
        try:
            OptionParser._process_long_opt(self, rargs, values)
        except BadOptionError:
            pass

    def _process_short_opts(self, rargs, values):
        try:
            OptionParser._process_short_opts(self, rargs, values)
        except BadOptionError:
            pass
