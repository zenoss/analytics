##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import transaction
import unittest

from Products.AdvancedQuery import Eq, MatchGlob, In
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.catalog.model_catalog import ModelCatalogDataManager, SearchParams, \
                                                TX_SEPARATOR, TX_STATE_FIELD, MANDATORY_FIELDS
from Products.Zuul.catalog.indexable import MODEL_INDEX_UID_FIELD as SOLR_UID
from Products.Zuul.catalog.indexable import OBJECT_UID_FIELD as UID

from Products.ZenModel.Device import manage_createDevice

from zenoss.modelindex.model_index import SearchParams


class TestModelCatalogTransactions(BaseTestCase):

    def afterSetUp(self):
        super(TestModelCatalogTransactions, self).afterSetUp()
        # Lets change the ModelCatalogTestDataManager with ModelCatalogDataManager
        self.model_catalog = IModelCatalogTool(self.dmd)
        self.data_manager = ModelCatalogDataManager('localhost:8983', self.dmd)
        self.model_catalog.model_catalog_client._data_manager = self.data_manager
        # get a reference to model_index to be able to fo checks bypassing the data manager
        self.model_index = self.data_manager.model_index

    def beforeTearDown(self):
        # we dont need to put back the test data manager since each test creates its own
        pass

    def _get_transaction_state(self):
        tid = self.data_manager._get_tid()
        return self.data_manager._current_transactions.get(tid)

    def _check_tx_state(self, pending=None, temp_indexed=None, temp_deleted=None):
        tx_state = self._get_transaction_state()

        if pending and isinstance(pending, basestring):
            pending = [ pending ]
        if temp_indexed and isinstance(temp_indexed, basestring):
            temp_indexed = [ temp_indexed ]
        if temp_deleted and isinstance(temp_deleted, basestring):
            temp_deleted = [ temp_deleted ]

        if pending:
            for uid in pending:
                self.assertTrue(uid in tx_state.pending_updates)
        if temp_indexed:
            for uid in temp_indexed:
                self.assertTrue(uid in tx_state.temp_indexed_uids)
                self.assertFalse(uid in tx_state.temp_deleted_uids)
        if temp_deleted:
            for uid in temp_deleted:
                self.assertTrue(uid in tx_state.temp_deleted_uids)
                self.assertFalse(uid in tx_state.temp_indexed_uids)

    def _validate_temp_indexed_results(self, results, expected_object_uids):
        found_object_uids = set()
        for result in results:
            solr_uid = getattr(result, SOLR_UID)
            uid = getattr(result, UID)
            found_object_uids.add(uid)
            self.assertNotEquals(uid, solr_uid)
            self.assertTrue(uid in solr_uid)
            self.assertTrue(TX_SEPARATOR in solr_uid)
            self.assertIsNotNone(getattr(result, TX_STATE_FIELD))
            self.assertTrue(getattr(result, TX_STATE_FIELD) != 0)
        self.assertEquals(set(found_object_uids), set(expected_object_uids))

    def _simulate_tx_commit(self):
        tx = transaction.get()
        self.data_manager.tpc_begin(tx)
        self.data_manager.tpc_finish(tx)

    def testPartialUpdates(self):
        # for this test we need to create a test device and commit the changes to
        device = manage_createDevice(self.dmd, 'my_device', '/')
        ip = "10.10.10.1"
        prod_state = 500
        device_uid = device.idx_uid()
        device.setManageIp(ip)
        device.setProdState(prod_state)

        # get the uids we are about to commit so we can revert them at the end
        tx_state = self._get_transaction_state()
        tid = tx_state.tid
        updated_uids = set(tx_state.pending_updates.keys()) | tx_state.temp_indexed_uids
        try:
            # simulate the transaction was committed and do a few partial updates
            self._simulate_tx_commit()
            # make sure the device was correctly indexed
            fields = ["productionState", "text_ipAddress"]
            search_results = self.model_catalog.search(query=Eq(UID, device_uid), fields=fields, commit_dirty=False)
            self.assertEquals(search_results.total, 1)
            brain = search_results.results.next()
            self.assertEquals(brain.uid, device_uid)
            self.assertEquals(brain.text_ipAddress, ip)
            self.assertEquals(brain.productionState, prod_state)

            # update prod state triggers an atomic update
            new_prod_state = 1000
            device.setProdState(new_prod_state)
            # tx_state.pending_updates.values()[0].spec.to_dict()
            # mi_results = self.model_index.search(SearchParams(Eq(UID, device_uid)))
            # repeat the search and make sure that the atomic update has all the fields it should
            search_results = self.model_catalog.search(query=Eq(UID, device_uid), fields=fields, commit_dirty=True)
            self.assertEquals(search_results.total, 1)
            brain = search_results.results.next()
            self.assertEquals(brain.uid, device_uid)
            self.assertEquals(brain.text_ipAddress, ip)
            self.assertEquals(brain.productionState, new_prod_state)
            # Make sure the index update is correct
            tx_state = self._get_transaction_state()
            index_update = tx_state.indexed_updates.get(device_uid)
            self.assertIsNotNone(index_update)
            expected_fields = MANDATORY_FIELDS | set( [ "productionState" ] )
            self.assertEquals(expected_fields, index_update.idxs)

            # Set manage ip also sends a partial update for fields 
            # 'decimal_ipAddress', 'text_ipAddress'
            new_ip = "10.10.10.2"
            device.setManageIp(new_ip)
            search_results = self.model_catalog.search(query=Eq(UID, device_uid), fields=fields, commit_dirty=True)
            self.assertEquals(search_results.total, 1)
            brain = search_results.results.next()
            self.assertEquals(brain.uid, device_uid)
            self.assertEquals(brain.text_ipAddress, new_ip)
            self.assertEquals(brain.productionState, new_prod_state)
            # Make sure the partial updates have been correctly combined
            tx_state = self._get_transaction_state()
            index_update = tx_state.indexed_updates.get(device_uid)
            self.assertIsNotNone(index_update)
            expected_fields = MANDATORY_FIELDS | set([ 'decimal_ipAddress', 'text_ipAddress', "productionState" ])
            self.assertEquals(expected_fields, index_update.idxs)

            # simulate another transaction commit and check everything went well
            self._simulate_tx_commit()
            search_results = self.model_catalog.search(query=Eq(UID, device_uid), fields=fields, commit_dirty=False)
            self.assertEquals(search_results.total, 1)
            brain = search_results.results.next()
            self.assertEquals(brain.uid, device_uid)
            self.assertEquals(brain.text_ipAddress, new_ip)
            self.assertEquals(brain.productionState, new_prod_state)

            # make sure all temp documents have beed deleted
            search_results = self.model_catalog.search(query=Eq(TX_STATE_FIELD, tid), commit_dirty=False)
            self.assertEquals(search_results.total, 0)
        finally:
            query = In(UID, updated_uids)
            self.model_index.unindex_search(SearchParams(query))


    def testMultipleUpdates(self):
        device = manage_createDevice(self.dmd, 'my_device', '/')
        device_uid = device.idx_uid()
        # On creationg, a index update of the whole object should have been created
        tx_state = self._get_transaction_state()
        self._check_tx_state(pending=device_uid)
        # temporary commit changes made so far
        self.data_manager.do_mid_transaction_commit()
        # We should be able to find the newly created device
        search_results = self.model_catalog.search(query=Eq(UID, device_uid), commit_dirty=False)
        self._validate_temp_indexed_results(search_results, expected_object_uids=[device_uid])
        # Changing the managed ip should trigger another index update
        ip = "10.10.10.1"
        device.setManageIp(ip)
        self.assertTrue(device_uid in tx_state.pending_updates)
        self.assertTrue(device_uid in tx_state.temp_indexed_uids)

        # a serch by ip "10.10.10.1" should return our device
        search_results = self.model_catalog.search(query=Eq("text_ipAddress", ip), commit_dirty=True)
        self._validate_temp_indexed_results(search_results, expected_object_uids=[device_uid])

        # set the managed ip to a different value
        old_ip = ip
        new_ip = "10.10.10.2"
        device.setManageIp(new_ip)
        # search by new ip should return out device
        search_results = self.model_catalog.search(query=Eq("text_ipAddress", new_ip), commit_dirty=True)
        self._validate_temp_indexed_results(search_results, expected_object_uids=[device_uid])
        # search by old ip should NOT return anything
        search_results = self.model_catalog.search(query=Eq("text_ipAddress", old_ip), commit_dirty=True)
        self._validate_temp_indexed_results(search_results, expected_object_uids=[])

        # set production state
        prod_state = 1100
        device.setProdState(prod_state)
        search_results = self.model_catalog.search(query=Eq("productionState", prod_state), commit_dirty=True)
        self._validate_temp_indexed_results(search_results, expected_object_uids=[device_uid])

        # Search by uid and check all the fields are correct
        fields = ["productionState", "text_ipAddress"]
        search_results = self.model_catalog.search(query=Eq(UID, device_uid), fields=fields, commit_dirty=False)
        self.assertEquals(search_results.total, 1)
        brain = search_results.results.next()
        self.assertEquals(brain.uid, device_uid)
        self.assertEquals(brain.text_ipAddress, new_ip)
        self.assertEquals(brain.productionState, prod_state)

    def testDataManager(self):
        # before any changes are made, tx_state is None
        self.assertIsNone(self._get_transaction_state())
        device_class_1 = "device_class_1"
        device_class_2 = "device_class_2"
        device_class_3 = "device_class_3"
        device_class_4 = "device_class_4"

        # create an organizer
        dc_1 = self.dmd.Devices.createOrganizer(device_class_1)
        tx_state = self._get_transaction_state()
        dc_1_uid = dc_1.idx_uid()

        # Some tx_state checks
        self.assertIsNotNone(tx_state)
        self.assertTrue( len(tx_state.pending_updates) > 0 )
        self.assertTrue( len(tx_state.indexed_updates) == 0 )
        self.assertTrue( len(tx_state.temp_indexed_uids) == 0 )
        self.assertTrue( len(tx_state.temp_deleted_uids) == 0 )

        # The new organizer index update should have been buffered in tx_state
        self._check_tx_state(pending=dc_1_uid)

        # A search with commit_dirty=False should not find the new device organizer
        search_results = self.model_catalog.search(query=Eq(UID, dc_1_uid), commit_dirty=False)
        self.assertEquals( search_results.total, 0 )

        # A search with commit_dirty=True must find the new device organizer
        search_results = self.model_catalog.search(query=Eq(UID, dc_1_uid), commit_dirty=True)
        # model catalog should return the dirty doc
        self.assertEquals( search_results.total, 1 )
        self._validate_temp_indexed_results(search_results, expected_object_uids=[dc_1_uid])

        # the tx_state object should have been updated appropiately
        self._check_tx_state(temp_indexed=dc_1_uid)
        self.assertTrue( len(tx_state.pending_updates) == 0 )
        
        # create another organizer
        dc_2 = self.dmd.Devices.createOrganizer(device_class_2)
        dc_2_uid = dc_2.idx_uid()

        # check tx_state has been updated accordinly
        self._check_tx_state(pending=dc_2_uid, temp_indexed=dc_1_uid)

        # search for both device classes with commit_dirty=False, it should only return dc_1_uid
        query = MatchGlob(UID, "/zport/dmd/Devices/device_class*")
        search_results = self.model_catalog.search(query=query, commit_dirty=False)
        self._validate_temp_indexed_results(search_results, expected_object_uids=[dc_1_uid])
        # tx_state should not have changed
        self._check_tx_state(pending=dc_2_uid, temp_indexed=dc_1_uid)

        # now with commit_dirty=True
        search_results = self.model_catalog.search(query=query, commit_dirty=True)
        self._check_tx_state(temp_indexed=[dc_1_uid, dc_2_uid])
        # it should return 2 device classes
        self.assertEquals( search_results.total, 2 )
        self._validate_temp_indexed_results(search_results, expected_object_uids=[dc_1_uid, dc_2_uid])

        # Lets delete device_class_1
        self.dmd.Devices._delObject(device_class_1)
        self._check_tx_state(pending=[dc_1_uid])
        #   a search with commit = True should not return device_class_1 anymore
        search_results = self.model_catalog.search(query=query, commit_dirty=True)
        self._validate_temp_indexed_results(search_results, expected_object_uids=[dc_2_uid])
        self._check_tx_state(temp_deleted=[dc_1_uid])
        #   however, we should have two temp docs matching "/zport/dmd/Devices/device_class*"
        mi_results = self.model_index.search(SearchParams(query))
        self.assertTrue( mi_results.total_count == 2 )
        #   make sure a count type of query works (search with limit=0)
        search_results = self.model_catalog.search(query=query, limit=0, commit_dirty=True)
        self.assertTrue( search_results.total == 1 )

        #   some more tx_state checks before moving on to the next thing
        tx_state = self._get_transaction_state()
        self.assertTrue( len(tx_state.pending_updates) == 0 )
        self.assertTrue( len(tx_state.indexed_updates) == 2 )
        self.assertTrue( len(tx_state.temp_indexed_uids) == 1 )
        self.assertTrue( len(tx_state.temp_deleted_uids) == 1 )

        # Simulate transaction is committed and do checks
        updated_uids = set(tx_state.pending_updates.keys()) | tx_state.temp_indexed_uids
        try:
            tid = self.data_manager._get_tid()
            # before commit we should have 2 docs with tx_state = tid
            mi_results = self.model_index.search(SearchParams( Eq(TX_STATE_FIELD, tid) ))
            self.assertTrue( mi_results.total_count == 2 )
            # Lets do the commit
            self._simulate_tx_commit()
            self.assertIsNone(self._get_transaction_state())
            # Check we only have one doc matching "/zport/dmd/Devices/device_class*"
            search_results = self.model_catalog.search(query=query, commit_dirty=False)
            self.assertEquals( search_results.total, 1 )
            # Check the result's tx_state field has been set to zero
            brain = search_results.results.next()
            self.assertEquals( brain.tx_state, 0 )
            # No documents should remain with tx_state == tid
            mi_results = self.model_index.search(SearchParams( Eq(TX_STATE_FIELD, tid) ))
            self.assertEquals( mi_results.total_count, 0 )
        finally:
            # clean up created docs in solr
            query = In(UID, updated_uids)
            self.model_index.unindex_search(SearchParams(query))

        # create another organizer in a new transaction
        dc_3 = self.dmd.Devices.createOrganizer(device_class_3)
        dc_3_uid = dc_3.idx_uid()
        self._check_tx_state(pending=dc_3_uid)
        tx_state = self._get_transaction_state()
        self.assertTrue( len(tx_state.pending_updates) == 1 )
        self.assertTrue( len(tx_state.indexed_updates) == 0 )
        self.assertTrue( len(tx_state.temp_indexed_uids) == 0 )
        self.assertTrue( len(tx_state.temp_deleted_uids) == 0 )
        # Manual mid-transaction commit
        self.data_manager.do_mid_transaction_commit()
        self._check_tx_state(temp_indexed=dc_3_uid)
        self.assertTrue( len(tx_state.pending_updates) == 0 )
        self.assertTrue( len(tx_state.indexed_updates) == 1 )
        self.assertTrue( len(tx_state.temp_indexed_uids) == 1 )
        self.assertTrue( len(tx_state.temp_deleted_uids) == 0 )
        query = MatchGlob(UID, "/zport/dmd/Devices/device_class*")
        search_results = self.model_catalog.search(query=query, commit_dirty=False)
        self._validate_temp_indexed_results(search_results, expected_object_uids=[dc_3_uid])
        # Simulate transaction is aborted and check tx state has been reset
        self.data_manager.abort(transaction.get())
        # No docs should match the device class uid
        search_results = self.model_catalog.search(query=Eq(UID, dc_3_uid), commit_dirty=False)
        self.assertTrue(search_results.total == 0)
        # No documents should remain with tx_state == tid
        tid = self.data_manager._get_tid()
        mi_results = self.model_index.search(SearchParams( Eq(TX_STATE_FIELD, tid) ))
        self.assertEquals( mi_results.total_count, 0 )
        self.assertIsNone(self._get_transaction_state())

        # delete a doc that exists before current tx, do a search with commit dirty and abort
        dc_4 = self.dmd.Devices.createOrganizer(device_class_4)
        dc_4_uid = dc_4.idx_uid()
        query = Eq(UID, dc_4_uid)
        try:
            self._simulate_tx_commit() # commit to get the device_class_4 doc in solr
            # check the doc exists in solr
            search_results = self.model_catalog.search(query=query)
            self.assertTrue(search_results.total == 1)
            # delete the object
            self.dmd.Devices._delObject(device_class_4)
            # a model catalog search with commit_dirty=True should no return the deleted doc
            search_results = self.model_catalog.search(query=query, commit_dirty=True)
            self.assertTrue(search_results.total == 0)
            # however the doc is still in solr
            mi_results = self.model_index.search(SearchParams(query))
            self.assertTrue( mi_results.total_count == 1 )
            # Abort tx
            self.data_manager.abort(transaction.get())
            # The doc should have been left intact in solr
            search_results = self.model_catalog.search(query=query)
            self.assertTrue(search_results.total == 1)
        finally:
            # clean up created docs in solr
            self.model_index.unindex_search(SearchParams(query))  

    def testSearchBrain(self):
        # create an object
        device_class_1 = "device_class_1"
        dc_1 = self.dmd.Devices.createOrganizer(device_class_1)
        dc_1_uid = dc_1.idx_uid()
        search_results = self.data_manager.search_brain(uid=dc_1_uid, context=self.dmd, commit_dirty=False)
        self.assertTrue( search_results.total == 0 )
        search_results = self.data_manager.search_brain(uid=dc_1_uid, context=self.dmd, commit_dirty=True)
        self.assertTrue( search_results.total == 1 )
        self._validate_temp_indexed_results(search_results, expected_object_uids=[dc_1_uid])

    def testSearches(self):
        n_organizers = 100
        organizers = {}
        pattern = "testSearches_DEVICE_CLASS_"
        for i in xrange(n_organizers):
            dc = self.dmd.Devices.createOrganizer("{}{:02}".format(pattern, i))
            organizers[dc.idx_uid()] = dc
        query = MatchGlob(UID, "/zport/dmd/Devices/{}*".format(pattern))
        search_results = self.model_catalog.search(query=query, commit_dirty=False)
        self.assertTrue( search_results.total == 0 )
        search_results = self.model_catalog.search(query=query, commit_dirty=True)
        self.assertTrue( search_results.total == n_organizers )
        search_results = self.model_catalog.search(query=query, limit=0)
        self.assertTrue( search_results.total == n_organizers )
        limit = 18
        for start in [ 0, 12, 45, 70 ]:
            expected_uids = { "/zport/dmd/Devices/{}{:02}".format(pattern, i) for i in xrange(start, start+limit) }
            search_results = self.model_catalog.search(query=query, start=start, limit=limit)
            self.assertTrue( search_results.total == n_organizers )
            brain_uids = { getattr(brain, UID) for brain in search_results.results }
            self.assertEquals( len(brain_uids), limit )
            self.assertEquals( len(brain_uids), len(expected_uids) )
            self.assertTrue( len( expected_uids - brain_uids ) == 0 )
            self.assertTrue( len( brain_uids - expected_uids ) == 0 )


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(TestModelCatalogTransactions),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
