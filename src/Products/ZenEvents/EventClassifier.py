##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""

Event classifier classifies events based on their summary text.  It 
uses a positional index to determin the class.  So for each word in the
summary it looks for the same word or wild card to determine which classes
that word in that position could be part.

positionIndex is an array of dictionaries.  Each positoin of the array
represents the position of the word in the summary string.  The value
is a dictionary with the words as keys and a tuple of classids as values.
"""

import copy
from os import path
from threading import Lock

from Products.ZenUtils.Exceptions import ZentinelException

class EventClassNotFound(ZentinelException): pass

class EventClassNotUnique(ZentinelException): pass

class EventClassifier(object):

    def __init__(self, templatesource):
        self.positionIndex = []
        self.templatesource = templatesource
        self.indexlock = Lock()
        #log = logging.getLogger("EventClassifier")
        #log.setLevel(logging.DEBUG)

    
    def classify(self, event):
        words = event.summary.split()
        if hasattr(event, "process"):
            words.insert(0,event.process)
        if len(words) > len(self.positionIndex):
            raise EventClassNotFound("event summary longer than position index")
        classids = None 
        classid = -1
        for index, word in zip(self.positionIndex, words):
            if '*' in index:
                if not classids:
                    classids = copy.copy(index['*'])
                else:
                    classids = classids.union(index['*'])
            if word in index:
                if not classids: 
                    classids = copy.copy(index[word])
                else:
                    classids = classids.intersection(index[word])
            if len(classids) == 1:
                classid = classids.pop()
                break
            elif len(classids) == 0:
                raise EventClassNotFound(
                    "no class found for words: " + " ".join(words)
                )
        if classid == -1:
            raise EventClassNotUnique(
                "could not find unique classid possabilites are: %s"
                % (classids,)
            )
        #logging.debug("found classid %s for words: %s" % 
        #                (classid, " ".join(words)))
        return classid 
                 

    def learn(self):
        """build event classes based on log data"""
        pass


    def buildIndex(self):
        """get a list of summary templates
        and build our positionIndex from it"""
        with self.indexlock:
            templates = self.readTemplates()
            for process, summary, classid in templates:
                words = summary.split()
                if process: words.insert(0, process)
                # add more position index entries if words list is longer than any seen before
                self.positionIndex.extend(dict() for i in range(len(self.positionIndex), len(words)))
                for posnIndex, word in zip(self.positionIndex, words):
                    if not word in posnIndex:
                        posnIndex[word] = set()
                    posnIndex[word].add(classid)
            # need to do a second pass to clear out unneeded positions
            # and to determin if a class can't be identified uniquely


    def readTemplates(self):
        templates = []
        if "http" in self.templatesource:
            # load over xmlrpc
            pass
        elif path.exists(self.templatesource):
            file = open(self.templatesource, "r")
            for line in file.readlines():
                if line.find("#") == 0: continue
                process, summary, classid = line.split('||')
                templates.append((process,summary,int(classid)))
            file.close()
        return templates
