##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import logging
import re
import os
import time
import signal
from contextlib import contextmanager
from sre_parse import parse_template
from md5 import md5

from Products.ZenUtils.Utils import prepId

log = logging.getLogger("zen.osprocessmatcher")

BLANK_PARSE_TEMPLATE = ([],[])

class OSProcessClassMatcher(object):
    """
    Mixin class, for process command line matching functionality common to
    OSProcessClass and OSProcess.

    Classes which mixin OSProcessClassMatcher must provide:
        self.includeRegex: string
        self.excludeRegex: string or None
        self.replaceRegex: string or None
        self.replacement: string or None
        self.processClassPrimaryUrlPath(): string
    """

    def matches(self, processText):
        """
        Compare the process name and parameters.

        @return: Does the process's command line match this process matcher?
        @rtype: Boolean
        """
        if not processText: return False
        processText = processText.strip()
        if self._searchIncludeRegex(processText):
            return not self._searchExcludeRegex(processText)
        return False

    def generateId(self, processText):
        """
        Generate the unique ID of the OSProcess that the process belongs
        to, based on the given process's command line. Assumes that the
        processText has already passed the OSProcessClass's matches method.

        The ID is based on a digest of the result of generateName, scoped below
        the OSProcessClass's primaryUrlPath.

        (In order to get an "other" bucket, the replaceRegex should be written
        to match the entire string, and every capture group should be optional.)

        @return: The unique ID of the corresponding OSProcess
        @rtype: string
        """
        return self.generateIdFromName(self.generateName(processText))

    def generateIdFromName(self, name):
        """
        Generate the unique ID of the OSProcess that the process belongs
        to, based on the results of generateName(). Assumes that the
        processText has already passed the OSProcessClass's matches method,
        and that the name provided came from generateName(processText).

        The ID is based on a digest of the name, scoped below the
        OSProcessClass's primaryUrlPath.

        @return: The unique ID of the corresponding OSProcess
        @rtype: string
        """
        generatedId = prepId(self.processClassPrimaryUrlPath()) + "_" + \
                      md5(name).hexdigest().strip()
        log.debug("Generated unique ID: %s", generatedId)
        return generatedId


    def generateName(self, processText):
        """
        Generate the name of an OSProcess.

        Strips the processText of whitespace, applies the replacement
        (globally), and strips any remaining leading and trailing whitespace.

        @return: The name of the corresponding OSProcess
        @rtype: string
        """
        return self._applyReplacement(processText.strip()).strip()

    def _applyReplacement(self, processText):
        regex = self._compiledRegex('replaceRegex')
        if regex:
            # We can't simply use re.sub, it blows up if the replacement
            # back-references an optional capture group that captured None.
            # In that case, we want it to replace the back-reference with ''.
            try:
                groups, literals = self._compiledReplacement('replaceRegex',
                                                             'replacement')
            except Exception:
                log.warn("Invalid replacement rule on %s", self)
                return processText
            parts = []
            frontier = 0
            for match in regex.finditer(processText):
                if match.start() == match.end():
                    continue
                parts.append(processText[frontier:match.start()])
                for index, group in groups:
                    try:
                        literal = match.group(group) or ''
                    except IndexError as e:
                        log.warn("Invalid replacement rule on %s", self)
                        return processText
                    literals[index] = literal
                parts.extend(literals)
                frontier = match.end()
            parts.append(processText[frontier:])
            return ''.join(parts)
        return processText

    def _searchIncludeRegex(self, processText):
        r = self._compiledRegex('includeRegex')
        return r and r.search(processText)

    def _searchExcludeRegex(self, processText):
        r = self._compiledRegex('excludeRegex')
        return r and r.search(processText)

    def _compiledRegex(self, field):
        regex = getattr(self, field, None)
        if not regex: return None
        cache = self._compiledCache()
        if field in cache and regex in cache[field]:
            return cache[field][regex]
        else:
            try:
                compiled = re.compile(regex)
                cache[field] = {regex : compiled}
                return compiled
            except re.error as e:
                log.warn("Invalid %s on %s", field, self)
                cache[field] = {regex : None}
                return None

    def _compiledReplacement(self, regexField, replField):
        repl = getattr(self, replField, None)
        if not repl: return BLANK_PARSE_TEMPLATE
        cache = self._compiledCache()
        regex = getattr(self, regexField, None)
        if replField in cache and (regex,repl) in cache[replField]:
            return cache[replField][(regex,repl)]
        else:
            try:
                compiled = parse_template(repl, self._compiledRegex(regexField))
                cache[replField] = {(regex,repl) : compiled}
                return compiled
            except Exception:
                log.warn("Invalid %s on %s", replField, self)
                cache[replField] = {(regex,repl) : None}
                return None

    def _compiledCache(self):
        cache = getattr(self, '_compiled_cache', None)
        if not cache:
            cache = self._compiled_cache = {}
        return cache

class OSProcessMatcher(OSProcessClassMatcher):
    """
    Mixin class, for process command line matching functionality in OSProcess.

    Classes which mixin OSProcessMatcher must provide:
        self.includeRegex: string
        self.excludeRegex: string or None
        self.replaceRegex: string or None
        self.replacement: string or None
        self.processClassPrimaryUrlPath(): string
        self.generatedId: string
    """
    def matches(self, processText):
        if super(OSProcessMatcher, self).matches(processText):
            generatedId = getattr(self,'generatedId',False)
            return self.generateId(processText) == generatedId
        return False

class DataHolder(object):
    def __init__(self, **attribs):
        for k,v in attribs.items():
            setattr(self,k,v)

    def __repr__(self):
        return "<" + self.__class__.__name__ + ": " + str(self.__dict__) + ">"

    def processClassPrimaryUrlPath(self):
        return self.primaryUrlPath


class OSProcessClassDataMatcher(DataHolder, OSProcessClassMatcher):
    pass

class OSProcessDataMatcher(DataHolder, OSProcessMatcher):
    pass

def applyOSProcessClassMatchers(matchers, lines):
    """
    @return (matched, unmatched), where...
            matched is: {matcher => {generatedName => [line, ...], ...}, ...}
            unmatched is: [line, ...]
    """
    matched = {}
    unmatched = []
    for line in lines:
        log.debug("COMMAND LINE: %s", line)
        unmatchedLine = True
        for matcher in matchers:
            if matcher.matches(line):
                if matcher not in matched:
                    matched[matcher] = {}
                generatedName = matcher.generateName(line)
                if generatedName not in matched[matcher]:
                    matched[matcher][generatedName] = []
                matched[matcher][generatedName].append(line)
                unmatchedLine = False
                break
        if unmatchedLine:
            unmatched.append(line)
    return (matched, unmatched)

def applyOSProcessMatchers(matchers, lines):
    """
    @return (matched, unmatched), where...
            matched is: {generatedName => [line, ...], ...}
            unmatched is: [line, ...]
    """
    matched = {}
    unmatched = []
    for line in lines:
        log.debug("COMMAND LINE: %s", line)
        unmatchedLine = True
        for matcher in matchers:
            if matcher.matches(line):
                if matcher.generatedName not in matched:
                    matched[matcher.generatedName] = []
                matched[matcher.generatedName].append(line)
                unmatchedLine = False
                break
        if unmatchedLine:
            unmatched.append(line)
    return (matched, unmatched)

def buildObjectMapData(processClassMatchData, lines):
    matchers = map(lambda(d):OSProcessClassDataMatcher(**d), processClassMatchData)
    matched, unmatched = applyOSProcessClassMatchers(matchers, lines)
    result = []
    for matcher, matchSet in matched.items():
        for name, matches in matchSet.items():
            result.append({
                'id': matcher.generateIdFromName(name),
                'displayName': name,
                'setOSProcessClass': matcher.primaryDmdId,
                'monitoredProcesses': matches})
    return result
