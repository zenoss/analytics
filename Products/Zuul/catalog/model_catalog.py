##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
import transaction
import zope.component
from zope.component.factory import Factory
from zope.component.interfaces import IFactory
from zExceptions import NotFound

from Acquisition import aq_parent, Implicit
from interfaces import IModelCatalog
from collections import defaultdict
from Products.AdvancedQuery import And, Or, Eq, Not, In
from Products.ZCatalog.interfaces import ICatalogBrain
from Products.ZenModel.Software import Software
from Products.ZenModel.OperatingSystem import OperatingSystem
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.Zuul.catalog.interfaces import IIndexableWrapper
from Products.Zuul.catalog.exceptions import ModelCatalogError, ModelCatalogUnavailableError
from transaction.interfaces import IDataManager
from zenoss.modelindex import indexed, index
from zenoss.modelindex.field_types import StringFieldType, \
     ListOfStringsFieldType, IntFieldType, DictAsStringsFieldType, LongFieldType
from zenoss.modelindex.constants import INDEX_UNIQUE_FIELD as UID_FIELD
from zenoss.modelindex.exceptions import IndexException, SearchException
from zenoss.modelindex.model_index import IndexUpdate, INDEX, UNINDEX, SearchParams

from zope.component import getGlobalSiteManager, getUtility
from zope.interface import implements

import traceback

log = logging.getLogger("model_catalog")

#logging.getLogger("requests").setLevel(logging.ERROR) # requests can be pretty chatty

TX_STATE_FIELD = "tx_state"


class SearchResults(object):

    def __init__(self, results, total, hash_, areBrains=True):
        self.results = results
        self.total = total
        self.hash_ = hash_
        self.areBrains = areBrains

    def __hash__(self):
        return self.hash_

    def __iter__(self):
        return self.results

    def __len__(self):
        return self.total


class ModelCatalogBrain(Implicit):
    implements(ICatalogBrain)

    def __init__(self, result):
        """
        Modelindex result wrapper
        @param result: modelindex.zenoss.modelindex.search.SearchResult
        """
        self._result = result
        for idx in result.idxs:
            setattr(self, idx, getattr(result, idx, None))

    def has_key(self, key):
        return self.__contains__(key)

    def __contains__(self, name):
        return hasattr(self._result, name)

    def getPath(self):
        """ Get the physical path for this record """
        uid = str(self._result.uid)
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
            log.error("Unable to get object from brain. Path: {0}. Catalog may be out of sync.".format(self._result.uid))
        return obj

    def getRID(self):
        """Return the record ID for this object."""
        return self._result.uuid


class ObjectUpdate(object):
    """ Contains the info needed to create a modelindex.IndexUpdate """
    def __init__(self, obj, op=INDEX, idxs=None):
        self.uid = obj.idx_uid()
        self.obj = obj
        self.op = op
        self.idxs = idxs


class ModelCatalogClient(object):

    def __init__(self, solr_url):
        self._data_manager = zope.component.createObject('ModelCatalogDataManager', solr_url)

    @property
    def model_index(self):
        return self._data_manager.model_index

    def _get_forbidden_classes(self):
        return ()

    def get_indexes(self):
        return self._data_manager.get_indexes()

    def search(self, search_params, context, commit_dirty=False):
        return self._data_manager.search(search_params, context, commit_dirty)

    def search_brain(self, path, context, fields=None, commit_dirty=False):
        return self._data_manager.search_brain(path, context, fields, commit_dirty)

    def catalog_object(self, obj, idxs=None):
        if not isinstance(obj, self._get_forbidden_classes()):
            try:
                self._data_manager.add_model_update(ObjectUpdate(obj, op=INDEX, idxs=idxs))
            except IndexException as e:
                log.error("EXCEPTION {0} {1}".format(e, e.message))
                self._data_manager.raise_model_catalog_error()

    def uncatalog_object(self, obj):
        if not isinstance(obj, self._get_forbidden_classes()):
            try:
                self._data_manager.add_model_update(ObjectUpdate(obj, op=UNINDEX))
            except IndexException as e:
                log.error("EXCEPTION {0} {1}".format(e, e.message))
                self._data_manager.raise_model_catalog_error()


class NoRollbackSavepoint(object):
    def __init__(self, datamanager):
        self.datamanager = datamanager

    def rollback(self):
        pass


TX_SEPARATOR = "@=@"


class ModelCatalogTransactionState(object):
    """ This class stores all the infromation about objects updated during a transaction """

    def __init__(self, tid):
        """ """
        self.tid = tid
        # @TODO For the time being we only have two index operations INDEX and UNINDEX
        # Once we are able to index only certain indexes and use solr
        # atomic updates this will become more complex in order to send as few requests to solr
        # as possible
        #
        # model_update may become a list of updates when we support more
        # operations other than INDEX, UNINDEX
        #
        self.pending_updates = {}  # { object_uid :  model_update }
        self.indexed_updates = {}  # { object_uid :  model_update }
        # ^^
        # In indexed_updates we store updates that we indexed mid transaction
        # because a search came in. Only this transaction should see such changes
        self.temp_indexed_uids = set() # uids (uid@=@tid) of temporary indexed documents
        self.commits_metric = []

    def add_model_update(self, object_update):
        """
        Generates and stores a IndexUpdate from the received ObjectUpdate taking into account
        any previous model update (if any)
        """
        uid = object_update.uid
        op = object_update.op
        idxs = object_update.idxs

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
                    idxs.update(TX_STATE_FIELD, UID_FIELD) # Mandatory fields

        model_update = IndexUpdate(object_update.obj, op=op , idxs=idxs, uid=uid)
        self.pending_updates[object_update.uid] = model_update
        del object_update # Make sure we dont keep references to the object

    def get_pending_updates(self):
        """ return updates that have not been sent to the index """
        return self.pending_updates.values()

    def get_indexed_updates(self):
        return self.indexed_updates.values()

    def get_updates_to_finish_transaction(self):
        #
        self.commits_metric.append(len(self.pending_updates))
        # Get all updates
        final_updates = {}
        for uid, update in self.indexed_updates.iteritems():
            # update the uid and tx_state
            if update.op == INDEX:
                update.spec.set_field_value(UID_FIELD, uid)
                update.spec.set_field_value(TX_STATE_FIELD, 0)
            final_updates[uid] = update
        # now update overwriting in case we had a new update for any
        # of the already indexed objects
        final_updates.update(self.pending_updates)
        return final_updates.values()

    def are_there_pending_updates(self):
        return len(self.pending_updates) > 0

    def are_there_indexed_updates(self):
        return len(self.indexed_updates) > 0

    def mark_pending_updates_as_indexed(self, indexed_uids):
        """
        @param indexed_uids: temporary uids we indexed the docs with
        """
        self.commits_metric.append(len(self.pending_updates))
        self.temp_indexed_uids = self.temp_indexed_uids | indexed_uids
        self.indexed_updates.update(self.pending_updates)
        self.pending_updates = {} # clear pending updates
        log.warn("SEARCH TRIGGERED TEMP INDEXING. {0}".format(traceback.format_stack()))   # @TODO TEMP LOGGING


class ModelCatalogDataManager(object):
    """ Class that interfaces with the modelindex package to interact with solr """

    implements(IDataManager)

    def __init__(self, solr_servers):
        self.model_index = zope.component.createObject('ModelIndex', solr_servers)
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

    def _process_pending_updates(self, tx_state):
        updates = tx_state.get_pending_updates()
        # we are going to index all pending updates adding
        # the tid to the uid field and setting tx_state field
        # to the tid
        tweaked_updates = []
        indexed_uids = set()
        for update in updates:
            tid = tx_state.tid
            temp_uid = self._mid_transaction_uid(update.uid, tx_state)

            # We only unindex docs that have been already modified
            # unmodified docs marked for removal are not a problem since
            # we blacklist them from searchs
            if update.op == UNINDEX:
                if temp_uid not in tx_state.temp_indexed_uids:
                    continue
                else:
                    update.uid = temp_uid
            else:
                # Index the object with a special uid
                update.spec.set_field_value(UID_FIELD, temp_uid)
                update.spec.set_field_value(TX_STATE_FIELD, tid)
                indexed_uids.add(temp_uid)
            tweaked_updates.append(update)

        # send and commit indexed docs to solr
        self.model_index.process_batched_updates(tweaked_updates)
        # marked docs as indexed
        tx_state.mark_pending_updates_as_indexed(indexed_uids)

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
        dirty_uids = temp_indexed_uids = set()
        if tweak_results:
            dirty_uids = set(tx_state.indexed_updates.keys())  # uids without TX_SEPARATOR
            temp_indexed_uids = tx_state.temp_indexed_uids     # uids with TX_SEPARATOR

        for result in catalog_results.results:
            if tweak_results:
                if result.uid in dirty_uids:
                    continue  # outdated result
                elif result.uid in temp_indexed_uids: # object has been updated mid transaction
                    result.uid = result.uid.split(TX_SEPARATOR)[0]
            brain = ModelCatalogBrain(result)
            brain = brain.__of__(context.dmd)
            yield brain

    def _do_search(self, search_params, context):
        """
        @param  context object to hook brains up to acquisition
        """
        try:
            catalog_results = self.model_index.search(search_params)
        except SearchException as e:
            log.error("EXCEPTION: {0}".format(e.message))
            self.raise_model_catalog_error()

        brains = self._parse_catalog_results(catalog_results, context)
        # this count might occasionally be wrong if there are mid tx updated objects
        # Since we should avoid mid transaction searches we will use it
        #
        count = catalog_results.total_count
        return SearchResults(brains, total=count, hash_=str(count))

    def _do_mid_transaction_commit(self):
        """
        When commit_dirty is True, objects that have been modified as a part of a transaction
        that has not been commited yet, will be commited with tx_state = tid so they can be searched.
        These "dirty" objects will remain in the catalog until transaction.abort is called,
        which will remove them from the catalog, or transaction.commit is called, which will remove
        them as a "dirty" object, then add them to the catalog with tx_state = 0.
        """
        tx_state = self._get_tx_state()
        # Lets add tx_state filters
        if tx_state and tx_state.are_there_pending_updates():
            # Temporarily index updated objects so the search is accurate
            self._process_pending_updates(tx_state)

    def _mid_transaction_uid(self, uid, tx_state):
        return "{0}{1}{2}".format(uid, TX_SEPARATOR, tx_state.tid)

    def _tweak_mid_transaction_search_params(self, search_params, tx_state):
        """
        Updates the search params in a transaction with mid transaction objects
        committed to solr if the query is searching for an uid that has been
        updated mid transaction.

        Ex: In transacton 1111 object uid_1 has had mid transaction changes. The latest version
            of the object is under doc uid_1@=@1111. If we get a query {"uid": "uid_1"} we need to
            transform it to {"uid": "uid_1@=@111"}

        """
        if isinstance(search_params.query, dict):
            uid = search_params.query.get("uid")
            if uid and uid in tx_state.indexed_updates:
                search_params.query["uid"] = self._mid_transaction_uid(uid, tx_state)
        elif not isinstance(search_params.query, basestring) and \
             "uid" in str(search_params.query):
            # AdvancedQuery
            queries = [ search_params.query ]
            while queries:
                q = queries.pop()
                if isinstance(q, Eq) and q._idx == "uid":
                    if q._term in tx_state.indexed_updates:
                        q._term = self._mid_transaction_uid(q._term, tx_state)
                elif isinstance(q, And) or isinstance(q, Or):
                    for sq in q._subqueries:
                        queries.append(sq)
                elif isinstance(q, Not):
                    queries.append(q._query)
                elif isinstance(q, In) and q._idx == "uid":
                    new_uid_values = []
                    for uid in q._term:
                        if uid in tx_state.indexed_updates:
                            new_uid_values.append(self._mid_transaction_uid(uid, tx_state))
                        else:
                            new_uid_values.append(uid)
                    q._term = new_uid_values
        #@TODO add support for lucene queries
        return search_params

    def search(self, search_params, context, commit_dirty=False):
        """
        Searches for objects that satisfy search_params in the catalog associated with context.
        """
        tx_state = self._get_tx_state()
        if commit_dirty:
            self._do_mid_transaction_commit()
        if tx_state and tx_state.indexed_updates:
            # If we have done a mid transaction commit we may need to tweak some params
            search_params = self._tweak_mid_transaction_search_params(search_params, tx_state)
        return self._do_search(search_params, context)

    def search_brain(self, uid, context, fields=None, commit_dirty=False):
        """ """
        tx_state = self._get_tx_state()

        if commit_dirty:
            self._do_mid_transaction_commit()

        # if the object has been updated mid transaction, get the latest version
        if tx_state and uid in tx_state.indexed_updates:
            uid = self._mid_transaction_uid(uid, tx_state)

        query = Eq(UID_FIELD, uid)
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
                log.fatal("Exception trying to abort current transaction. {0} / {1}".format(e, e.message))
                raise ModelCatalogError("Model Catalog error trying to abort transaction")

    def abort(self, tx):
        try:
            self._delete_temporary_tx_documents()
        finally:
            self.reset_tx_state(tx)

    def tpc_begin(self, transaction):
        pass

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
                    # @TODO TEMP LOGGING
                    log.warn("COMMIT_METRIC: {0}. MID-TX COMMITS? {1}".format(tx_state.commits_metric, dirty_tx))
                except Exception as e:
                    log.exception("Exception in tcp_finish: {0} / {1}".format(e, e.message))
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

    def __init__(self, solr_servers):
        super(ModelCatalogTestDataManager, self).__init__(solr_servers)

    def tpc_finish(self, transaction):
        super(ModelCatalogTestDataManager, self).abort(transaction)

    def commit(self, transaction):
        super(ModelCatalogTestDataManager, self).abort(transaction)

    def abort(self, tx):
        super(ModelCatalogTestDataManager, self).abort(transaction)

    def search(self, search_params, context, commit_dirty=True):
        return super(ModelCatalogTestDataManager, self).search(search_params, context, commit_dirty=True)

    def search_brain(self, path, context, fields=None, commit_dirty=True):
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
                self._v_temp_model_catalog_client = ModelCatalogClient(self.solr_url)
            catalog_client = self._v_temp_model_catalog_client
        else:
            #
            # context is a persistent object. Create/retrieve the catalog client
            # from the zodb connection object. We store the client in the zodb
            # connection object so we are certain that each zope thread has its own
            catalog_client = getattr(zodb_conn, 'model_catalog_client', None)
            if catalog_client is None:
                zodb_conn.model_catalog_client = ModelCatalogClient(self.solr_url)
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

def get_solr_config():
    config = getGlobalConfiguration()
    return config.get('solr-servers', 'localhost:8983')


def register_model_catalog():
    """
    Register the model catalog as an utility
    To get the utility we will use this code:
        >>> from Products.Zuul.catalog.interfaces import IModelCatalog
        >>> from zope.component import getUtility
        >>> getUtility(IModelCatalog)
    """
    model_catalog = ModelCatalog(get_solr_config())
    getGlobalSiteManager().registerUtility(model_catalog, IModelCatalog)


def register_data_manager_factory(test=False):
    if not test:
        factory = Factory(ModelCatalogDataManager, "Default Model Catalog Data Manager")
    else:
        factory = Factory(ModelCatalogTestDataManager, "Test Model Catalog Data Manager")
    getGlobalSiteManager().registerUtility(factory, IFactory, 'ModelCatalogDataManager')

register_data_manager_factory()
register_model_catalog()
