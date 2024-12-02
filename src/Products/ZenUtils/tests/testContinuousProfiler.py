##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from unittest import makeSuite
from Products.ZenUtils.debugtools import ContinuousProfiler
import os
import random

class TestContinuousProfiler(BaseTestCase):
    """
    Tests the functionality of the ContinuousProfiler class
    """

    def helper(self, profiler, dump_stats_args):
        self.assertEqual(profiler.isRunning, False)

        profiler.start()
        self.assertEqual(profiler.isRunning, True)

        sysRand = random.SystemRandom()
        [i * sysRand.random() for i in range(100)]

        filename, tmpdir = dump_stats_args
        pstats_filepath = profiler.dump_stats(filename, tmpdir)
        self.assertEqual(os.path.isfile(pstats_filepath), True)
        if filename is not None:
            if tmpdir is None:
                tmpdir = '/tmp'
            self.assertEqual(pstats_filepath, os.path.join(tmpdir, filename))

        profiler.stop()
        self.assertEqual(profiler.isRunning, False)

    def testContinuousProfiling(self):
        p1 = ContinuousProfiler()
        self.helper(p1, (None, None))

    def testContinuousProfilingWithProcessIdentifer(self):
        p2 = ContinuousProfiler(process_identifier='TestContinuousProfiler')
        self.helper(p2, (None, None))

    def testContinuousProfilingWithFilename(self):
        p3 = ContinuousProfiler()
        self.helper(p3, ('TestContinuousProfiler', None))

    def testContinuousProfilingWithFilenameAndDirectory(self):
        p4 = ContinuousProfiler()
        self.helper(p4, ('TestContinuousProfiler', '/tmp'))

    def testContinuousProfilingWithLogging(self):
        import logging
        log = logging.getLogger('zen.testContinuousProfiler')
        p5 = ContinuousProfiler(log=log)
        self.helper(p5, (None, None))

def test_suite():
    return makeSuite(TestContinuousProfiler)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
