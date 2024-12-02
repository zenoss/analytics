##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""BasicLoader.py

BasicLoader provides functionality for batch database loaders
it has a main loop that will the method loaderBody which should
be defined in sub classes of BasicLoader to actually load data.

$Id: BasicLoader.py,v 1.14 2004/04/07 00:52:46 edahl Exp $"""

__version__ = "$Revision: 1.14 $"[11:-2]

import sys
import os

import transaction

from ZCmdBase import ZCmdBase

class BasicLoader(ZCmdBase):
    '''Load a machine'''

    def __init__(self, noopts=0, app=None, ignoreComments=True):
        '''Handle command line options, get app instance,and setup log file'''
        ZCmdBase.__init__(self, noopts, app)
        self.lineNumber = 0
        self.ignoreComments = ignoreComments


    def setfields(self, fieldnames, line, delimiter='|'):
        fields = line.split(delimiter)
        for i in range(len(fields)):
            setattr(self, fieldnames[i], fields[i])

    
    def loadDatabase(self):
        '''do the load'''
        if self.filename and os.path.exists(self.filename):
            lines = open(self.filename).readlines()
        else:
            self.log.critical("filename %s not found", self.filename)
            sys.exit(1)
    
        for line in lines:
            self.lineNumber += 1
            line = line.strip()
            if not line or (self.ignoreComments and line[0] == '#'): continue
            try:
                quit = self.loaderBody(line)
                if quit == True: break # return True to stop
            except Exception:
                self.log.exception("Line Number %i", self.lineNumber)
            if (not self.options.noCommit 
                and not self.lineNumber % self.options.commitCount):
                trans = transaction.get()
                trans.note('Initial load using %s' % self.__class__.__name__)
                trans.commit()
                self.app._p_jar.sync()

        if self.options.noCommit:
            self.log.info("No commit has been made.")
        else:
            trans = transaction.get()
            trans.note('Initial load using %s' % self.__class__.__name__)
            trans.commit()


    def buildOptions(self):
        self.usage = "%prog [options] file"
        ZCmdBase.buildOptions(self)
        
        self.parser.add_option('-x', '--commitCount',
                    dest='commitCount',
                    default=20,
                    type="int",
                    help='how many lines should be loaded before commit')

        self.parser.add_option('-n', '--noCommit',
                    dest='noCommit',
                    action="store_true",
                    default=0,
                    help='Do not store changes to the Dmd (for debugging)')


    def parseOptions(self):
        ZCmdBase.parseOptions(self)
        if len(self.args) > 0:
            self.filename = self.args[0]


if __name__ == "__main__":
    loader = BasicLoader()
    loader.loadDatabase()
    print "Database Load is finished!"
