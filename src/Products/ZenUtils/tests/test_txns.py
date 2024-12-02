##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


'''
Note that this is meant to be run from zopecctl using the "test" option. If you
would like to run these tests from python, simply to the following:

    python ZenUtils/test_txns.py
'''
import unittest

from Testing.ZopeTestCase import ZopeTestCase

import random
import os
import subprocess
import transaction

from amqpTestDefns import Publisher
from ..AmqpDataManager import AmqpDataManager
import logging
log = logging.getLogger("ZenUtils.tests.txns")
log.setLevel(logging.DEBUG)

from ..transaction_contextmanagers import nested_transaction, zodb_transaction

new_state = lambda : random.choice("RED ORANGE YELLOW GREEN BLUE PURPLE".split())

# context managers for transaction and state commit/rollback
from contextlib import contextmanager

# define test-specific exception, so as not to accidentally mask real exceptions
class TestTxnsException(Exception): pass

@contextmanager
def revertAttributeOnError(obj, attrname):
    prev_value = getattr(obj, attrname)
    try:
        yield
    except Exception:
        log.debug( "restore %s to previous value %r" % (attrname, prev_value) )
        setattr(obj, attrname, prev_value)
        raise

@contextmanager
def msg_publish(chan):
    try:
        log.debug( "enable tx channel methods for channel 0x%08x" % id(chan))
        chan.tx_select()
        yield
    except Exception:
        log.debug( "cancel sending messages for channel 0x%08x" % id(chan))
        chan.tx_rollback()
        raise
    else:
        log.debug( "publish all messages for channel 0x%08x, and close channel" % id(chan))
        chan.tx_commit()
        chan.close()


class TestTransactions(ZopeTestCase):
    # This class does not inherit from BaseTestCase because it's doing low-level transactions on ZODB,
    # which we disable in BaseTestCase.

    # must define this class constant to avoid problems with 'test_folder_1_'
    _setup_fixture = 0

    def afterSetUp(self):
        super(TestTransactions,self).afterSetUp()

        self.app.txn_test_objectx = 0
        transaction.commit()

        self.connected_to_mq = False

        try:
            self.pub = Publisher()
            self.connected_to_mq = True

            # start up message listener and wait for it to report "ready"
            localpath = os.path.dirname(__file__)
            listener_script = os.path.join(localpath, "listen_db_messages.py")
            listener = subprocess.Popen(["python",listener_script], bufsize=1, shell=False, stdout=subprocess.PIPE)
            listener.stdout.readline()
            self.listener = listener
        except Exception as e:
            log.warning( "failed to setup amqp connection: %s",e )


    def beforeTearDown(self):
        try:
            if not self.connected_to_mq:
                log.debug( "no connection to mq, skipping tearDown")
                return

            log.debug("tearing down")
            self.connected_to_mq = False

            self.app._delObject('txn_test_objectx')
            transaction.commit()

            # shut down listener subprocess
            with msg_publish(self.pub.channel):
                self.pub.publish("FIN")

        finally:
            super(TestTransactions,self).beforeTearDown()
            pass

    def template_test_transaction_fn(self, n=10, raise_exception=False, raise_internal_only=False):

        if not self.connected_to_mq:
            log.debug("skipping current test, no connection")
            return

        # get current value of object in the database
        tally = self.app.txn_test_objectx

        self.state = "VIOLET"
        with msg_publish(self.pub.channel):
            log.debug("set listener record count (%d) %r" % (tally, self.pub.channel))
            self.pub.publish("INIT", str(tally))
            self.pub.publish("STATE", self.state)

        last_tally = tally
        self.added_recs = 0

        # start a transaction, perform some database updates, and send corresponding messages
        try:
            with zodb_transaction() as txn:
                if raise_internal_only:
                    # store data and send messages outside of nested txn
                    with nested_transaction():
                        for i in range(n):
                            self.app.txn_test_objectx += 1

                    with msg_publish(self.pub.channel):
                        msg = self.pub.publish("ADDRECS",str(n))
                        self.state = new_state()
                        log.debug("state changed to " + self.state)
                        msg = self.pub.publish("STATE", self.state)
                        self.added_recs += n

                try:
                    with revertAttributeOnError(self, "state"):
                        with revertAttributeOnError(self, "added_recs"):
                            with nested_transaction(AmqpDataManager(self.pub.channel, txn._manager)):
                                log.debug("using TransactionManager %r", txn._manager)
                                for i in range(n):
                                    self.app.txn_test_objectx += 1

                                msg = self.pub.publish("ADDRECS",str(n))
                                self.added_recs += n
                                self.state = new_state()
                                log.debug("state changed to " + self.state)
                                msg = self.pub.publish("STATE", self.state)
                                if raise_exception:
                                    raise TestTxnsException("undo db and messages")
                except TestTxnsException:
                    if not raise_internal_only:
                        raise
        except TestTxnsException:
            log.debug("zodb transaction got aborted...")
        except Exception as e:
            log.debug("caught unexpected exception %s", e)
            raise

        with msg_publish(self.pub.channel):
            msg = self.pub.publish("STATUS")

        # read status line from listener, compare with current tally and state
        log.debug("get status from listener, compare with current")
        listener_status = self.listener.stdout.readline()

        # now get actual object value from database
        try:
            tally = self.app.txn_test_objectx

            expected_tally = last_tally + self.added_recs
            log.debug( "Expected/actual tally: %d/%d %s" % (expected_tally, tally, (("FAIL","OK")[expected_tally==tally])) )
            self.assertEqual(expected_tally, tally)
        
            expected_status = "%d %s\n" % (tally, self.state)
            log.debug( "Expected: " + expected_status.strip())
            log.debug( "Received: " + listener_status.strip() )
            self.assertEqual(expected_status, listener_status)
        except AttributeError as ae:
            log.debug("skip test validation steps, dmd corrupted")

    def test_0transaction_commit(self):
        return self.template_test_transaction_fn()

    def test_1transaction_rollback(self):
        return self.template_test_transaction_fn(raise_exception=True)

    def test_2nested_transaction_rollback(self):
        return self.template_test_transaction_fn(raise_exception=True, raise_internal_only=True)

def test_suite():
    return unittest.makeSuite(TestTransactions)
