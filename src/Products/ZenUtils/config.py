##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
Zenoss config parsers.

There are mutiple stages to config parsing. Parsing is split into stages so
that we can validate a whole config file and possibly rebuild it to correct
errors.

The stages are:

* Parse - Split the config file in to ConfigLine types while maintaining line
  order, comments, and new lines
* Validate - Check that all lines are valid
* Report - Investigate why a line might be invalid (ex: invalid key format)
* Load - Get a config object back
* Write - An optional stage to write the config back to a file
"""

from __future__ import absolute_import, print_function

import re

import six


class ConfigError(Exception):
    """Error for problems parsing config files."""


class ConfigLineError(ConfigError):
    """Error for problems parsing config files with line context."""

    def __init__(self, message, lineno):
        super(ConfigLineError, self).__init__(message)
        self.lineno = lineno

    def __str__(self):
        return "%s on line %d" % (self.message, self.lineno)


class ConfigErrors(ConfigError):
    """A group of errors while parsing config."""

    def __init__(self, message, errors):
        super(ConfigErrors, self).__init__(message)
        self.errors = errors

    def __str__(self):
        output = [self.message]
        for error in self.errors:
            output.append(str(error))

        return "\n    - ".join(output)


class InvalidKey(ConfigError):
    pass


class ConfigLineKeyError(ConfigLineError):
    pass


class Config(dict):
    """
    A bunch of configuration settings. Uses dictionary access,
    or object attribute access.

    Provides some Convenience functions for different types.
    """

    def __getattr__(self, attr):
        return self[attr]

    def getbool(self, key, default=None):
        """
        Convenience function to convert the value to a bool.
        Valid values are and case of true, yes, y, 1 anything
        else is considered False.

        If key doesn't exist, returns `default`.
        """
        try:
            return self[key].lower() in ("true", "yes", "y", "1")
        except KeyError:
            return default

    getboolean = getbool

    def getint(self, key, default=None):
        """
        Convenience function to convert the value to an int.
        Valid values are anything `int(x)` will accept.

        If key doesn't exist or can't be converted to int, returns `default`.
        """
        try:
            return int(self[key])
        except (KeyError, ValueError):
            return default

    def getfloat(self, key, default=None):
        """
        Convenience function to convert the value to a float.
        Valid values are anything `float(x)` will accept.

        If key doesn't exist or can't be converted to float, returns `default`.
        """
        try:
            return float(self[key])
        except (KeyError, ValueError):
            return default


class ConfigLine(object):
    """Abstract class that represents a single line in the config."""

    def __init__(self, line):
        self.line = line

    def __str__(self):
        return self.line

    @property
    def setting(self):
        """
        Return a key, value tuple if this line represents a setting.
        """
        return NotImplemented

    @classmethod
    def parse(cls, line):
        """
        Returns an instance of cls if this class can parse this line.
        Otherwise returns None.
        """
        return NotImplemented

    @classmethod
    def checkError(cls, line, lineno):
        """
        Checks the string for possible matches, considers why it doesn't match
        exactly if it's close and returns a ConfigLineError.
        """
        return NotImplemented


class SettingLine(ConfigLine):
    """Represents a config line with a `key = value` pair."""

    _regexp = re.compile(
        r"^(?P<key>[a-z]+([a-z\d_]|-[a-z\d_])*)"  # key
        r"\s*(?P<delim>(=|:|\s)*)"  # delimiter
        r"\s*(?P<value>.*)$",  # value
        re.I,
    )

    def __init__(self, key, value=None, delim="="):
        self.key = key
        self.value = value
        self.delim = delim

    def __str__(self):
        return "{key} {delim} {value}".format(**self.__dict__)

    @property
    def setting(self):
        return self.key, self.value

    @classmethod
    def parse(cls, line):
        match = cls._regexp.match(line)
        if match:
            data = match.groupdict()
            return cls(**data)

    @classmethod
    def checkError(cls, line, lineno):
        match = re.match(
            r"^(?P<key>.+?)\s*(?P<delim>(=|:|\s)+)\s*(?P<value>.+)$",
            line,
            re.I,
        )
        if match and not cls._regexp.match(line):
            return ConfigLineKeyError(
                'Invalid key "%s"' % match.groupdict()["key"], lineno
            )


class CommentLine(ConfigLine):
    @property
    def setting(self):
        return None

    @classmethod
    def parse(cls, line):
        if line.startswith("#"):
            return cls(line[1:].strip())

    @classmethod
    def checkError(cls, line, lineno):
        return None

    def __str__(self):
        return "# %s" % self.line


class EmptyLine(ConfigLine):
    def __init__(self):
        pass

    @property
    def setting(self):
        return None

    @classmethod
    def parse(cls, line):
        if line == "":
            return cls()

    @classmethod
    def checkError(cls, line, lineno):
        return None

    def __str__(self):
        return ""


class InvalidLine(ConfigLine):
    """
    Default line if no other ConfigLines matched. Assumed to be invalid
    input.
    """

    @property
    def setting(self):
        return None

    @classmethod
    def parse(cls, line):
        return None

    @classmethod
    def checkError(cls, line, lineno):
        return None


class ConfigFile(object):
    """
    Parses Zenoss's config file format.

    Example:

        key value
        key intvalue
        key = value
        key=value
        key:value
        key : value
    """

    # Lines to parse the config against
    _lineTypes = [
        SettingLine,
        CommentLine,
        EmptyLine,
    ]

    # Line to use if the line didn't match any other types
    _invalidLineType = InvalidLine

    def __init__(self, file):
        """
        @param file file-like-object
        """
        self.file = file
        self.filename = (
            self.file.name if hasattr(self.file, "name") else "Unknown"
        )
        self._lines = None

    def _parseLine(self, line):
        cleanedLine = line.strip()
        for type in self._lineTypes:
            match = type.parse(cleanedLine)
            if match:
                return match

        return self._invalidLineType(cleanedLine)

    def _checkLine(self, line, lineno):
        cleanedLine = line.strip()
        for type in self._lineTypes:
            match = type.checkError(cleanedLine, lineno)
            if match:
                return match

    def parse(self):
        """
        Parse a config file which has key-value pairs.Returns a list of config
        line information. This line information can be used to accuratly
        recreate the config without losing comments or invalid data.
        """
        if self._lines is None:
            self._lines = []
            for line in self.file:
                self._lines.append(self._parseLine(line))

        return self._lines

    def write(self, file):
        """
        Write the config out to a file. Takes a new file argument
        because the input file object often doesn't have write access.

        @param file file-like-object
        """
        for line in self:
            file.write(str(line) + "\n")

    def validate(self):
        """
        Validate that there are no errors in the config file

        @throws ConfigError
        """
        errors = []
        for lineno, line in enumerate(self):
            if isinstance(line, self._invalidLineType):
                # Identify possible errors
                error = self._checkLine(line.line, lineno)
                if error:
                    errors.append(error)
                else:
                    errors.append(
                        ConfigLineError(
                            'Unexpected config line "%s"' % line.line,
                            lineno + 1,
                        )
                    )

        if errors:
            raise ConfigErrors(
                'There were errors parsing the config "%s".' % self.filename,
                errors,
            )

    def __iter__(self):
        for line in self.parse():
            yield line

    def items(self):
        for line in self:
            if line.setting:
                yield line.setting


def _parse(file):
    configFile = ConfigFile(file)
    configFile.validate()
    return configFile.items()


class ConfigLoader(object):
    """Lazily load the config when requested."""

    def __init__(self, config_files, config=Config):
        """
        :param config Config The config instance or class to load data into.
            Must support update which accepts an iterable of (key, value).
        :param config_files list<string> A list of config file names to
            parse in order.
        """
        if not isinstance(config_files, list):
            config_files = [config_files]

        self.config_files = config_files
        self.config = config
        self._config = None

    def load(self):
        """Load the config_files into an instance of config_class."""
        if isinstance(self.config, type):
            self._config = self.config()
        else:
            self._config = self.config

        if not self.config_files:
            raise ConfigError("Config loader has no config files to load.")

        for file in self.config_files:
            if isinstance(file, six.string_types):
                # It's a string, so open it first
                with open(file, "r") as fp:
                    options = _parse(fp)
            else:
                # Assume it's an open file
                options = _parse(file)

            for k, v in options:
                self._config[k] = v

    def __call__(self):
        """Lazily load the config file."""
        if self._config is None:
            self.load()

        return self._config
