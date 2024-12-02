##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from unittest import TestSuite, makeSuite

from Products.ZenEvents.MailProcessor import MessageProcessor
from Products.ZenTestCase.BaseTestCase import BaseTestCase


# Notes:
#
# * Tab characters in any e-mail need to be escaped or the
#   Subversion hook that checks for tab characters will go
#   insane with rage.

class TestMailProcessor(BaseTestCase):

    def afterSetUp(self):
        super(TestMailProcessor, self).afterSetUp()
        
        class zemclass: pass
        self.zem = zemclass()
        self.zem.sendEvent = self.sendEvent
        self.sent = {}

    def sendEvent(self, evt):
        "Fakeout sendEvent() method"
        self.sent = evt


    def checkMsgToEvent(self, testName ):
        "Check that an e-mail was translated as expected"
        self.sent = {}

        mp = MessageProcessor( self.zem, 2 )

        message = mail_data[testName]['msg']
        mp.process( message )

        expected_evt = mail_data[testName]['event']

        # Actually check for expected values
        for field, value in expected_evt.items():
            # ip address relies on the python socket library so we
            # just want to make sure it is not blank
            if field == "ipAddress":
                self.assertTrue( self.sent.get( field ) )
            else:
                self.assertEquals( self.sent.get( field, '' ), value )


    def testValidEmail(self):
        "Sanity check of e-mail processor"
        self.checkMsgToEvent( "simple" )


    def testInvalidEmail(self):
        "Simple sanity checks of e-mail processor for negative testing"
        self.sent = {}
        mp = MessageProcessor( self.zem, 2 )

        self.assertRaises( TypeError, mp.process, None )

        mp.process( '' )
        self.assertEquals( len(self.sent), 0 )


    def testNormalEmail(self):
        "Test of a valid e-mail with extra headers"
        self.checkMsgToEvent( "normal" )


    def testUTC(self):
        "Sanity check of e-mails using UTC"
        # Hmmmm....  can't reproduce ticket http://dev.zenoss.org/trac/ticket/3263
        # I *think* it got fixed in Python
        self.checkMsgToEvent( "utc" )

    def testParseEmail(self):
        mp = MessageProcessor(self.zem, 2)
        cases = [
            'more.info@test.example.com',
            '<more.info@test.example.com>',
            '"more.info@test.example.com"',
            '"more.info@test.example.com"',
            "'more.info@test.example.com'",
            '"More Information" <more.info@test.example.com>',
        ]
        expected = 'more.info@test.example.com'
        for email in cases:
            parsed = mp.parse_email_address(email)
            self.assertEquals(parsed, expected)


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(TestMailProcessor))
    return suite

# =================  Start of sample mail messages  =======================

# Format of a mail_data entry:
#  "name": {
#       'msg': """E-mail text here""",
#       'event': { expected_field1: expected_value1, ... },
#  },

mail_data = {

   "simple": {
       'msg': """Return-Path: example_account@example.com
Date: Thu, 11 Dec 2008 17:18:26 -0500 (EST)
From: Test Account
    <example_account@example.com>
To: Test Account <example_account@example.com>
Message-ID: <375303282.37931229033906513.JavaMail.root@zimbra1>
Subject: Test event message subject

Simple body message
""",
       'event': {
           'severity': 2, 'facility': 'unknown', 'eventClassKey': 'email',
           '_action': 'status', 'component': '',
           'summary': 'Test event message subject',
           '_clearClasses': [], 'eventKey': '',
           'device': 'example.com',
           'message': 'Simple body message\n',
           '_fields': [], 'ipAddress': '192.0.32.10'
  }
},

# ----------------------------

   "utc": {
       'msg': """Return-Path: example_account@example.com
Date: Thu, 11 Dec 2008 17:18:26 0000 (UTC)
From: Test Account <example_account@example.com>
To: Test Account <example_account@example.com>
Message-ID: <375303282.37931229033906513.JavaMail.root@zimbra1>
Subject: Test event message subject

Simple body message
""",
       'event': {
           'severity': 2, 'facility': 'unknown', 'eventClassKey': 'email',
           '_action': 'status', 'component': '', 'summary': 'Test event message subject',
           '_clearClasses': [], 'eventKey': '', 'device': 'example.com',
           'message': 'Simple body message\n', '_fields': [],
           'ipAddress': '192.0.32.10'
  }
},

# ----------------------------

   "normal": {
       'msg': """Return-Path: example_account@example.com
Received: from zimbra1.example.com (LHLO zimbra1.example.com) (74.63.38.26) by
 zimbra1.example.com with LMTP; Thu, 11 Dec 2008 17:18:31 -0500 (EST)
Received: from localhost (localhost.localdomain [127.0.0.1])
\tby zimbra1.example.com (Postfix) with ESMTP id 3D8BF2128004
\tfor <example_account@example.com>; Thu, 11 Dec 2008 17:18:31 -0500 (EST)
X-Virus-Scanned: amavisd-new at zimbra1.example.com
X-Spam-Flag: NO
X-Spam-Score: -1.431
X-Spam-Level:
X-Spam-Status: No, score=-1.431 tagged_above=-10 required=4 tests=[AWL=0.191,
\tBAYES_00=-2.599, RCVD_IN_SORBS_DUL=0.877, RDNS_NONE=0.1]
Received: from zimbra1.example.com ([127.0.0.1])
\tby localhost (zimbra1.example.com [127.0.0.1]) (amavisd-new, port 10024)
\twith ESMTP id 4FrgxduZh0Vm; Thu, 11 Dec 2008 17:18:26 -0500 (EST)
Received: from zimbra1.example.com (zimbra1.example.com [74.63.38.26])
\tby zimbra1.example.com (Postfix) with ESMTP id 861612128001
\tfor <example_account@example.com>; Thu, 11 Dec 2008 17:18:26 -0500 (EST)
Date: Thu, 11 Dec 2008 17:18:26 -0500 (EST)
From: Test Account <example_account@example.com>
To: Test Account <example_account@example.com>
Message-ID: <375303282.37931229033906513.JavaMail.root@zimbra1>
Subject: Test event message subject
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: 7bit
X-Originating-IP: [68.146.118.240]
X-Mailer: Zimbra 5.0.11_GA_2695.RHEL5_64 (ZimbraWebClient - FF3.0 (Mac)/5.0.11_GA_2695.RHEL5_64)

Body part of the message
Lots of
  lovely
    text

# special case: '.' on at the beginning of a line all on its own
#    may terminate message processing, depending on the agent

.

  Spread out all over the e-mail.

sig
""",
       'event': {
           'severity': 2, 'facility': 'unknown', 'eventClassKey': 'email',
           '_action': 'status', 'component': '', 'summary': 'Test event message subject',
           '_clearClasses': [], 'eventKey': '', 'device': 'example.com',
           'message': "Body part of the message\nLots of\n  lovely\n    text\n\n# special case: '.' on at the beginning of a line all on its own\n#    may terminate message processing, depending on the agent\n\n.\n\n  Spread out all over the e-mail.\n\nsig\n",
           '_fields': [], 'ipAddress': '192.0.32.10'
  }
},

} # End of mail data
