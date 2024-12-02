##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
import sys
import time
import transaction
import zope.component
from zope.component.factory import Factory
from zope.component.interfaces import IFactory
from zExceptions import NotFound

from Acquisition import aq_parent, Implicit, aq_base
from interfaces import IModelCatalog
from collections import defaultdict
from Products.AdvancedQuery import And, Or, Eq, Not, In
from Products.ZCatalog.interfaces import ICatalogBrain
from Products.ZenModel.Software import Software
from Products.ZenModel.OperatingSystem import OperatingSystem
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.Zuul.catalog.exceptions import ModelCatalogError, ModelCatalogUnavailableError
from transaction.interfaces import IDataManager
from zenoss.modelindex import indexed, index
from zenoss.modelindex.field_types import StringFieldType, \
     ListOfStringsFieldType, IntFieldType, DictAsStringsFieldType, LongFieldType
from zenoss.modelindex.exceptions import IndexException, SearchException
from zenoss.modelindex.constants import NULL_SEARCH_LIMIT, DEFAULT_SEARCH_LIMIT
from zenoss.modelindex.model_index import IndexUpdate, INDEX, UNINDEX, SearchParams
from .indexable import MODEL_INDEX_UID_FIELD, OBJECT_UID_FIELD

from zope.component import getGlobalSiteManager, getUtility
from zope.interface import implements

import traceback

log = logging.getLogger("model_catalog")

#logging.getLogger("requests").setLevel(logging.ERROR) # requests can be pretty chatty

SOLR_CONFIG = []

TX_SEPARATOR = "@=@"

TX_STATE_FIELD = "tx_state"

MANDATORY_FIELDS = set([ TX_STATE_FIELD, OBJECT_UID_FIELD, MODEL_INDEX_UID_FIELD ])


class IterResults(object):
    def __init__(self, results, parse_method, context):
        self.results = results
        self.parse_method = parse_method
        self.context = context

    def __iter__(self):
        # Must use next(self) to initialize the generator in the 'next' method
        return next(self)

    def next(self):
        for results in self.results:
            brains = self.parse_method(results, self.context)
            for brain in brains:
                yield brain


class SearchResults(object):

    def __init__(self, results, total, hash_, areBrains=True):
        self.results = results
        self.total = total
        self.hash_ = hash_
        self.areBrains = areBrains
        self.facets = None

    def __hash__(self):
        return self.hash_

    def __iter__(self):
        return self.results

    def __len__(self):
        return self.total


class CursorSearchResults(object):
    def __init__(self, results):
        self.results = results

    def __iter__(self):
        return iter(self.results)


class ModelCatalogBrain(Implicit):
    implements(ICatalogBrain)

    def __init__(self, data, idxs=None):
        """
        @param  data: dict with the brain's data
        @params idxs: indices the brain must have
        """
        self._data = data  # for debug purposes store the data the brain was built from
        self.idxs = data.keys()
        if idxs is not None:
            self.idxs = idxs
        for idx in self.idxs:
            setattr(self, idx, data.get(idx))

    def has_key(self, key):
        return self.__contains__(key)

    def __contains__(self, name):
        return hasattr(self, name)

    def getPath(self):
        """ Get the physical path for this record """
        uid = str(getattr(self, OBJECT_UID_FIELD))
        if not uid.startswith('/zport/dmd'):
            uid = '/zport/dmd/' + uid
        return uid

    def _unrestrictedGetObject(self):
        """ """
        return self.getObject()

    def getObject(self):
        """Return the object for this record

        Will return None if the object cannot be found via its cataloged path
        (i.e., it was deleted or moved without recataloging), or if the user is
        not authorized to access the object.
        """
        parent = aq_parent(self)
        obj = None
        try:
            obj = parent.unrestrictedTraverse(self.getPath())
        except (NotFound, KeyError, AttributeError):
            log.error(
                "Unable to get object from brain. "
                "Path: %s. Model catalog may be out of sync.",
                self.uid,
            )
            raise
        return obj

    def getRID(self):
        """Return the record ID for this object."""
        return getattr(self, "uuid")

    def to_dict(self, idxs=None):
        
        if idxs:
            if isinstance(idxs, basestring):
                idxs = [idxs]
        else:
            idxs = self.idxs
        return {idx:getattr(self, idx) for idx in idxs}
        


class ObjectUpdate(object):
    """ Contains the info needed to create a modelindex.IndexUpdate """
    def __init__(self, obj, op=INDEX, idxs=None):
        self.uid = aq_base(obj).getPrimaryId()
        self.obj = obj
        self.op = op
        self.idxs = idxs


class ModelCatalogClient(object):

    def __init__(self, solr_url, context):
        self.context = context
        self._data_manager = zope.component.createObject('ModelCatalogDataManager', solr_url, context)

    @property
    def model_index(self):
        return self._data_manager.model_index

    def _get_forbidden_classes(self):
        return ()

    def get_indexes(self):
        return self._data_manager.get_indexes()

    def get_object_indexes(self, obj, idxs=None):
        return self._data_manager.get_indexes(obj, idxs)

    def cursor_search(self, search_params, context):
        return self._data_manager.cursor_search(search_params, context)

    def search(self, search_params, context, commit_dirty=False):
        return self._data_manager.search(search_params, context, commit_dirty)

    def search_brain(self, path, context, fields=None, commit_dirty=False):
        return self._data_manager.search_brain(path, context, fields, commit_dirty)

    def catalog_object(self, obj, idxs=None):
        if not isinstance(obj, self._get_forbidden_classes()):
            try:
                self._data_manager.add_model_update(ObjectUpdate(obj, op=INDEX, idxs=idxs))
            except IndexException as e:
                log.error("EXCEPTION %s %s", e, e.message)
                self._data_manager.raise_model_catalog_error("Exception indexing object")

    def uncatalog_object(self, obj):
        if not isinstance(obj, self._get_forbidden_classes()):
            try:
                self._data_manager.add_model_update(ObjectUpdate(obj, op=UNINDEX))
            except IndexException as e:
                log.error("EXCEPTION %s %s", e, e.message)
                self._data_manager.raise_model_catalog_error("Exception unindexing object")

    def get_brain_from_object(self, obj, context, fields=None):
        """ Builds a brain for the passed object without performing a search """
        spec = self._data_manager.model_index.get_object_spec(obj, idxs=fields)
        brain = ModelCatalogBrain(spec.to_dict(use_attr_query_name=True))
        brain = brain.__of__(context.dmd)
        return brain


class NoRollbackSavepoint(object):
    def __init__(self, datamanager):
        self.datamanager = datamanager

    def rollback(self):
        pass


class ModelCatalogTransactionState(object):
    """ This class stores all the infromation about objects updated during a transaction """

    def __init__(self, tid):
        """ """
        self.tid = tid
        #
        self.pending_updates = {}  # { object_uid :  ObjectUpdate }
        self.indexed_updates = {}  # { object_uid :  IndexUpdate }
        # ^^
        # In indexed_updates we store updates that we indexed mid transaction
        # because a search came in. Only this transaction should see such changes
        self.temp_indexed_uids = set() # object uids of temporary indexed documents
        self.temp_deleted_uids = set() # object uids of temporary deleted documents

        # During the tpc_begin phase, IndexUpdates are created for each
        # object we need to index
        self._updates_to_finish_tx = {} # { object_uid: modelindex.IndexUpdate}

        self.commits_metric = []

    def add_model_update(self, object_update):
        """
        Generates and stores an ObjectUpdate than combines the received ObjectUpdate
        with any previous updates to the same object (if any)
        """
        uid = object_update.uid
        op = object_update.op
        idxs = object_update.idxs
        if idxs:
            if isinstance(idxs, basestring):
                idxs = set([idxs])
            else:
                idxs = set(idxs)

        previous_model_update = self.pending_updates.get(uid) if self.pending_updates.get(uid) else self.indexed_updates.get(uid)
        # When we get INDEX after UNINDEX or UNINDEX after INDEX, the last operation to come overwrites the previous
        if previous_model_update and previous_model_update.op == INDEX: # combine the previous update with the new one
            if op == UNINDEX:
                idxs = None # unindex the object
            else: # previous op was index, lets check if it was a partial update or not
                if not previous_model_update.idxs or not idxs: # one or both of them was a full index
                    idxs = None # index the whole object
                elif previous_model_update.idxs and idxs: # combine them
                    idxs = set(idxs) | set(previous_model_update.idxs)

        if idxs: # make sure mandatory idxs are always sent
            idxs.update( MANDATORY_FIELDS ) # Mandatory fields

        # store the ObjectUpdate. Defer creating the IndexUpdate
        # until the end of the transaction or before a dirty search
        self.pending_updates[object_update.uid] = ObjectUpdate(object_update.obj, op=op , idxs=idxs)

    def get_pending_updates(self):
        """ return updates that have not been sent to the index """
        # build the IndexUpdate from the ObjectUpdate buffered in self.pending_updates
        modelindex_updates = {}
        for object_update in self.pending_updates.values():
            uid = object_update.uid
            op = object_update.op
            idxs = object_update.idxs
            modelindex_updates[uid] = IndexUpdate(object_update.obj, op=op , idxs=idxs, uid=uid)
        return modelindex_updates

    def get_indexed_updates(self):
        # self.indexed_updates stores the IndexUpdate
        return self.indexed_updates.values()

    def get_updates_to_finish_transaction(self):
        """
        This is called during tpc.finish
        """
        return self._updates_to_finish_tx.values()

    def prepare_updates_to_finish_transaction(self):
        """
        This is called during tx tpc_vote phase. return all
        modelindex.IndexUpdate that need to be commited in solr
        """
        self.commits_metric.append(len(self.pending_updates))
        # Get all updates
        self._updates_to_finish_tx = {}
        for uid, update in self.indexed_updates.iteritems():
            # update the uid and tx_state
            if update.op == INDEX:
                update.spec.set_field_value(MODEL_INDEX_UID_FIELD, uid)
                update.spec.set_field_value(TX_STATE_FIELD, 0)
            self._updates_to_finish_tx[uid] = update
        # Any non mid tx commit update overwrites any previous update
        self._updates_to_finish_tx.update(self.get_pending_updates())

    def are_there_pending_updates(self):
        return len(self.pending_updates) > 0

    def are_there_indexed_updates(self):
        return len(self.indexed_updates) > 0

    def mark_pending_updates_as_indexed(self, indexed_updates, indexed_uids, deleted_uids):
        """
        @param indexed_updates: dict {uid: IndexUpdate} containing the IndexUpdates
                                that were just sent to solr
        @param indexed_uids: temporary uids we indexed the docs with
        """
        self.commits_metric.append(len(indexed_updates))
        self.temp_indexed_uids = self.temp_indexed_uids | indexed_uids
        self.temp_deleted_uids = self.temp_deleted_uids | deleted_uids
        self.temp_indexed_uids = self.temp_indexed_uids - deleted_uids
        self.temp_deleted_uids = self.temp_deleted_uids - indexed_uids
        self.indexed_updates.update(indexed_updates)
        self.pending_updates = {} # clear pending updates
        #log.info("SEARCH TRIGGERED TEMP INDEXING. {0}".format(traceback.format_stack()))   # @TODO TEMP LOGGING


class ModelCatalogDataManager(object):
    """ Class that interfaces with the modelindex package to interact with solr """

    implements(IDataManager)

    def __init__(self, solr_servers, context):
        config = getGlobalConfiguration()
        self.model_index = zope.component.createObject('ModelIndex', solr_servers)
        self.model_index.searcher.default_row_count = int(config.get('solr-search-limit', DEFAULT_SEARCH_LIMIT))
        self.context = context
        self._current_transactions = {} # { transaction_id : ModelCatalogTransactionState }
        # @TODO ^^ Make that an OOBTREE to avoid concurrency issues? I dont think we need it since we have one per thread

    def _get_tid(self, tx=None):
        if tx is None:
            tx = transaction.get()
        return id(tx)

    def _get_tx_state(self, tx=None):
        tid = self._get_tid(tx)
        return self._current_transactions.get(tid)

    def ping_index(self):
        return self.model_index.ping()

    def get_indexes(self):
        return self.model_index.get_indexes()

    def get_object_indexes(self, obj, idxs=None):
        return self.model_index.get_indexes(obj, idxs)

    def _process_pending_updates(self, tx_state):
        """ index all pending updates during a mid transaction commit """
        updates = tx_state.get_pending_updates()
        # we are going to index all pending updates setting the MODEL_INDEX_UID_FIELD
        # field as the OBJECT_UID_FIELD appending the tid and setting tx_state field
        # to the current tid
        tweaked_updates = []
        indexed_uids = set()
        deleted_uids = set()
        for update in updates.itervalues():
            tid = tx_state.tid
            if update.op == UNINDEX:
                # dont do anything for unindexed objects, just add them to
                # a set to be able to blacklist them from search results
                deleted_uids.add(update.uid)
            else:
                # Index the object with a special uid
                temp_uid = self._mid_transaction_uid(update.uid, tx_state)

                # the first time we index a mid transaction atomic update, we need
                # to index the whole object, otherwise the temp document will only
                # have the mandatory fields and whatever fields the partial update has
                #
                if update.spec.partial_spec and update.uid not in tx_state.temp_indexed_uids:
                    original_update = update
                    obj = self.context.dmd.unrestrictedTraverse(original_update.uid)
                    update = IndexUpdate(obj, op=original_update.op , uid=original_update.uid)
                update.spec.set_field_value(MODEL_INDEX_UID_FIELD, temp_uid)
                update.spec.set_field_value(TX_STATE_FIELD, tid)
                indexed_uids.add(update.uid)
                tweaked_updates.append(update)

        # send and commit indexed docs to solr
        self.model_index.process_batched_updates(tweaked_updates)
        # marked docs as indexed
        tx_state.mark_pending_updates_as_indexed(updates, indexed_uids, deleted_uids)

    def _add_tx_state_query(self, search_params, tx_state):
        """
        only interested in docs indexed by committed transactions or
        in docs temporary committed by the current transaction
        """
        values = [ 0 ]  # default tx_state for committed transactions
        if tx_state:
            values.append(tx_state.tid)
        if isinstance(search_params.query, dict):
            search_params.query[TX_STATE_FIELD] = values
        else: # We assume it is an AdvancedQuery
            or_query = [ Eq(TX_STATE_FIELD, value) for value in values]
            search_params.query = And( search_params.query, Or(*or_query) )
        return search_params

    def raise_model_catalog_error(self, message=""):
        if not self.ping_index():
            raise ModelCatalogUnavailableError(message)
        else:
            raise ModelCatalogError(message)

    def _parse_catalog_results(self, catalog_results, context):
        """
        build brains from model catalog results. It also
        tweaks the results filtering outdated objects
        """
        tx_state = self._get_tx_state()
        tweak_results = (tx_state and tx_state.are_there_indexed_updates())
        for result in catalog_results.results:
            if tweak_results:
                tid = tx_state.tid
                result_uid = getattr(result, OBJECT_UID_FIELD)
                result_tid = getattr(result, TX_STATE_FIELD)
                if result_uid in tx_state.temp_deleted_uids:
                    continue # object was deleted
                elif result_uid in tx_state.temp_indexed_uids and result_tid != tid:
                    continue # Not the latest version of the object for this transaction
            brain = ModelCatalogBrain(result.to_dict(), result.idxs)
            brain = brain.__of__(context.dmd)
            yield brain

    def _get_fields_to_return(self, fields):
        """
        return the list of fields that brains returned by the current search will have
        """
        if isinstance(fields, basestring):
            fields = [ fields ]
        brain_fields = set(fields) if fields else set()
        return list(brain_fields | MANDATORY_FIELDS)

    def cursor_search(self, search_params, context):
        try:
            search_params.fields = self._get_fields_to_return(search_params.fields)
            search_params = self._add_tx_state_query(search_params, None)
            catalog_results = self.model_index.cursor_search(search_params)
        except SearchException as e:
            log.error("EXCEPTION: %s", e.message)
            self.raise_model_catalog_error("Exception performing search")
        else:
            results = IterResults(catalog_results, self._parse_catalog_results, context)
            return CursorSearchResults(results)

    def _do_search(self, search_params, context):
        """
        @param  context object to hook brains up to acquisition
        """
        tx_state = self._get_tx_state()
        is_tx_dirty = tx_state and tx_state.are_there_indexed_updates()

        if is_tx_dirty:
            # to get an accurate count when there are mid transaction documents
            # already committed to solr we need to get all the results :(
            original_start = search_params.start
            original_limit = search_params.limit
            search_params.start = 0
            search_params.limit = None

        try:
            search_params.fields = self._get_fields_to_return(search_params.fields)
            catalog_results = self.model_index.search(search_params)
        except SearchException as e:
            log.error("EXCEPTION: %s", e.message)
            self.raise_model_catalog_error("Exception performing search")

        brains = iter(self._parse_catalog_results(catalog_results, context))
        count = catalog_results.total_count

        # if we have mid-transaction commits, we need to extract
        # all brains from the generator to return the real count
        # Please do not use mid tx commits !!
        if is_tx_dirty:
            brains = [ b for b in brains ]
            count = len(brains)

            if original_limit != NULL_SEARCH_LIMIT or original_start != 0:
                # We need to do some slicing
                start = original_start
                if original_limit == NULL_SEARCH_LIMIT:
                    end = count
                else:
                    end = original_start + original_limit
                brains = iter(brains[start:end])
            else:
                brains = iter(brains)
            # undo changes to search_params
            search_params.start = original_start
            search_params.limit = original_limit
        
        results = SearchResults(brains, total=count, hash_=str(count))
        if catalog_results.facets:
            results.facets = catalog_results.facets
        return results

    def do_mid_transaction_commit(self):
        """
        When commit_dirty is True, objects that have been modified as a part of a transaction
        that has not been commited yet, will be commited with TX_STATE_FIELD = tid so they can be searched.
        These "dirty" objects will remain in the catalog until transaction.abort is called,
        which will remove them from the catalog, or transaction.commit is called, which will remove
        them as a "dirty" object, then add them to the catalog with TX_STATE_FIELD = 0.
        """
        tx_state = self._get_tx_state()
        # Lets add tx_state filters
        if tx_state and tx_state.are_there_pending_updates():
            # Temporarily index updated objects so the search is accurate
            self._process_pending_updates(tx_state)

    def _mid_transaction_uid(self, uid, tx_state):
        return "{0}{1}{2}".format(uid, TX_SEPARATOR, tx_state.tid)

    def search(self, search_params, context, commit_dirty=False):
        """
        Searches for objects that satisfy search_params in the catalog associated with context.
        """
        tx_state = self._get_tx_state()
        if commit_dirty:
            self.do_mid_transaction_commit()
        search_params = self._add_tx_state_query(search_params, tx_state)
        return self._do_search(search_params, context)

    def search_brain(self, uid, context, fields=None, commit_dirty=False):
        """ """
        tx_state = self._get_tx_state()
        if commit_dirty:
            self.do_mid_transaction_commit()
        query = Eq(OBJECT_UID_FIELD, uid)
        search_params = SearchParams(query, fields=fields)
        search_params = self._add_tx_state_query(search_params, tx_state)
        return self._do_search(search_params, context)


    # ----- Index related methods  ------

    def reset_tx_state(self, tx):
        tid = self._get_tid(tx)
        if tid in self._current_transactions:
            del self._current_transactions[tid]

    def add_model_update(self, update):
        tx = transaction.get()
        tid = self._get_tid(tx)
        if tid not in self._current_transactions:
            tx.join(self)
            self._current_transactions[tid] = ModelCatalogTransactionState(tid)
        tx_state = self._current_transactions[tid]
        tx_state.add_model_update(update)

    def _delete_temporary_tx_documents(self):
        tx_state = self._get_tx_state()
        if tx_state and tx_state.are_there_indexed_updates():
            try:
                query = {TX_STATE_FIELD:tx_state.tid}
                self.model_index.unindex_search(SearchParams(query))
            except Exception as e:
                log.fatal("Exception trying to abort current transaction. %s / %s", e, e.message)
                raise ModelCatalogError("Model Catalog error trying to abort transaction")

    #---------------------------------------------------------------------------
    # Two-phase commit protocol sequence of calls:
    #     tpc_begin commit tpc_vote (tpc_finish | tpc_abort)
    #---------------------------------------------------------------------------
    def abort(self, tx):
        try:
            self._delete_temporary_tx_documents()
        finally:
            self.reset_tx_state(tx)

    def tpc_begin(self, transaction):
        # Get the modelindex.IndexUpdate of all updated objects
        # Doing this in any of the following tpc phases can cause PosKeyErrors
        tx_state = self._get_tx_state(transaction)
        if tx_state:
            start = time.time()
            tx_state.prepare_updates_to_finish_transaction()
            log.debug("Preparing updates to finish tx took %s", time.time()-start)

    def commit(self, transaction):
        pass

    def tpc_vote(self, transaction):
        # Check connection to SOLR
        if not self.ping_index():
            raise ModelCatalogUnavailableError()

    def tpc_finish(self, transaction):
        try:
            tx_state = self._get_tx_state(transaction)
            if tx_state:
                updates = tx_state.get_updates_to_finish_transaction()
                dirty_tx = tx_state.are_there_indexed_updates()
                try:
                    self.model_index.process_batched_updates(updates)
                    self._delete_temporary_tx_documents()
                    log.debug("COMMIT_METRIC: %s. MID-TX COMMITS? %s", tx_state.commits_metric, dirty_tx)
                except Exception as e:
                    log.exception("Exception in tcp_finish: %s / %s", e, e.message)
                    self.abort(transaction)
                    raise
        finally:
            self.reset_tx_state(transaction)

    def tpc_abort(self, transaction):
        pass

    def sortKey(self):
        return "model_catalog"

    def savepoint(self, optimistic=False):
        return NoRollbackSavepoint(self)


class ModelCatalogTestDataManager(ModelCatalogDataManager):
    """
    Data Manager for tests. In tests we index everything everytime we do a search and
    we commit everyting to solr with a temp tid
    """

    def __init__(self, solr_servers, context):
        super(ModelCatalogTestDataManager, self).__init__(solr_servers, context)

    def tpc_finish(self, transaction):
        super(ModelCatalogTestDataManager, self).abort(transaction)

    def commit(self, transaction):
        super(ModelCatalogTestDataManager, self).abort(transaction)

    def abort(self, transaction):
        super(ModelCatalogTestDataManager, self).abort(transaction)

    def search(self, search_params, context, commit_dirty=False):
        return super(ModelCatalogTestDataManager, self).search(search_params, context, commit_dirty=True)

    def search_brain(self, path, context, fields=None, commit_dirty=False):
        return super(ModelCatalogTestDataManager, self).search_brain(path, context, fields, commit_dirty=True)


class ModelCatalog(object):
    """ This class provides Solr Clients """

    def __init__(self, solr_url):
        # module modelindex registers the indexer and searcher constructor factories in ZCA
        #
        self.solr_url = solr_url
        """
        Each Zope thread has its own solr indexer and reader. Model catalog clients are identified
        by the thread's zodb connection id
        """

    def get_client(self, context):
        """
        Retrieves/creates the solr client for the zope thread that is trying to access solr
        """
        zodb_conn = context.get("_p_jar")

        catalog_client = None

        # context is not a persistent object. Create a temp client in a volatile variable.
        # Volatile variables are not shared across threads, so each thread will have its own client
        #
        if zodb_conn is None:
            if not hasattr(self, "_v_temp_model_catalog_client"):
                self._v_temp_model_catalog_client = ModelCatalogClient(self.solr_url, context)
            catalog_client = self._v_temp_model_catalog_client
        else:
            #
            # context is a persistent object. Create/retrieve the catalog client
            # from the zodb connection object. We store the client in the zodb
            # connection object so we are certain that each zope thread has its own
            catalog_client = getattr(zodb_conn, 'model_catalog_client', None)
            if catalog_client is None:
                zodb_conn.model_catalog_client = ModelCatalogClient(self.solr_url, context)
                catalog_client = zodb_conn.model_catalog_client

        return catalog_client


    def catalog_object(self, obj, idxs=None):
        """ """
        catalog_client = self.get_client(obj)
        catalog_client.catalog_object(obj, idxs)

    def uncatalog_object(self, obj):
        """ """
        catalog_client = self.get_client(obj)
        catalog_client.uncatalog_object(obj)

    def get_indexes(self, context):
        catalog_client = self.get_client(context)
        return catalog_client.get_indexes()

    def get_object_indexes(self, obj, idxs=None):
        catalog_client = self.get_client(obj)
        return catalog_client.get_object_indexes(obj, idxs)


def get_solr_config(test=False):
    config = getGlobalConfiguration()
    if test:
        return config.get('solr-test-server', 'localhost:8993')
    if not SOLR_CONFIG:
        SOLR_CONFIG.append(config.get('solr-servers', 'localhost:8983'))
        log.info("Loaded Solr config from global.conf. Solr Servers: %s", SOLR_CONFIG)
    return SOLR_CONFIG[0]


def register_model_catalog(test=False):
    """
    Register the model catalog as an utility
    To get the utility we will use this code:
        >>> from Products.Zuul.catalog.interfaces import IModelCatalog
        >>> from zope.component import getUtility
        >>> getUtility(IModelCatalog)
    """
    model_catalog = ModelCatalog(get_solr_config(test))
    getGlobalSiteManager().registerUtility(model_catalog, IModelCatalog)


def register_data_manager_factory(test=False):
    if not test:
        factory = Factory(ModelCatalogDataManager, "Default Model Catalog Data Manager")
    else:
        factory = Factory(ModelCatalogTestDataManager, "Test Model Catalog Data Manager")
    getGlobalSiteManager().registerUtility(factory, IFactory, 'ModelCatalogDataManager')

register_data_manager_factory()
register_model_catalog()
