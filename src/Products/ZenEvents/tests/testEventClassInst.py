##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenEvents.EventClassInst import EventClassInst


class testEventClassInst(BaseTestCase):
    def afterSetUp(self):
        super(testEventClassInst, self).afterSetUp()

        self.testEvents = [EventClassInst('testEvents') for i in range(10)]
        for i, event in enumerate(self.testEvents):
            event.origSequence = i
            event.sequence = i
            event.sameKey = lambda: list(sorted(self.testEvents, key=lambda m:(m.sequence, m.origSequence)))


    def testUpdatePropertyNoDuplicates(self):
        self.testEvents[2]._updateProperty('sequence', 0)

        self.assertEqual([m.origSequence for m in self.testEvents[0].sameKey()],
                         [0, 2, 1, 3, 4, 5, 6, 7, 8, 9])

        self.testEvents[7]._updateProperty('sequence', 0)

        self.assertEqual([m.origSequence for m in self.testEvents[0].sameKey()],
                         [0, 7, 2, 1, 3, 4, 5, 6, 8, 9])

        self.testEvents[9]._updateProperty('sequence', 100)

        self.assertEqual([m.origSequence for m in self.testEvents[0].sameKey()],
                         [0, 7, 2, 1, 3, 4, 5, 6, 8, 9])
        self.assertEqual(self.testEvents[9].sequence, 100)


    def testUpdateProperty(self):
        for i, event in enumerate(self.testEvents):
            event.sequence = i

        for i, event in enumerate(self.testEvents):
            event._updateProperty('sequence', event.sequence + 100)

        for i, event in enumerate(self.testEvents):
            self.assertEqual(event.sequence, i + 100)
