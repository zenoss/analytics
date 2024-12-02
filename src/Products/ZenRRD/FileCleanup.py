#! /usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""FileCleanup

Walk a tree recursively and cleanup files.  Slowly.

"""

import os
import re
import time

from twisted.internet import reactor

THIRTY_DAYS = 30 * 24 * 60 * 60


class FileCleanup:
    def __init__(
        self, root, pattern, tooOld=THIRTY_DAYS, maxProcess=50, frequency=60
    ):
        """Recursively delete all  files under [root] matching
        [pattern] older than [tooOld], processing only [maxProcess]
        files every [frequency] seconds."""
        self.tooOld = tooOld
        self.pattern = re.compile(pattern)
        self.root = root
        self.frequency = frequency
        self.maxProcess = maxProcess
        self.iter = None

    def start(self):
        "Begin processing the directory, recursively"
        reactor.callLater(0, self.run)

    def run(self):
        "Start a run at the directory"
        if self.iter is None:
            self.now = time.time()
            self.iter = self.walk(self.root)
        for i, f in enumerate(self.iter):
            if i > self.maxProcess:
                break
            if self.test(f):
                self.process(f)
        else:
            self.iter = None
        reactor.callLater(self.frequency, self.run)

    def process(self, fullPath):
        "Hook for cleanin up the file"
        os.unlink(fullPath)

    def test(self, fullPath):
        "Test file file for pattern, age and type"
        if not os.path.isfile(fullPath):
            return False
        if not self.pattern.match(fullPath):
            return False
        mtime = os.path.getmtime(fullPath)
        if mtime > self.now - self.tooOld:
            return False
        return True

    def walk(self, root):
        "Generate the list of all files"
        for f in os.listdir(root):
            fullPath = os.path.join(root, f)
            yield fullPath
            if os.path.exists(fullPath) and os.path.isdir(fullPath):
                for k in self.walk(fullPath):
                    yield k


if __name__ == "__main__":
    import sys

    f = FileCleanup("/tmp", 604800, ".*\\.xpi$", 10, 1)
    f.process = lambda x: sys.stdout.write("%s\n" % x)
    f.start()
    reactor.run()
