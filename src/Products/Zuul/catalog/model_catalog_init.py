##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Queue
import multiprocessing
import sys
import time
import transaction
import traceback
import argparse
import logging
import ctypes
import zope.component
from zExceptions import NotFound
from collections import deque
from contextlib import contextmanager

from OFS.ObjectManager import ObjectManager
from Products.AdvancedQuery import And, Not, MatchGlob, Eq, MatchRegexp, In, Or
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.ToManyContRelationship import ToManyContRelationship
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.Zuul.catalog.global_catalog import GlobalCatalog
from Products.Zuul.catalog.model_catalog import get_solr_config
from Products.Zuul.utils import dottedname
from zenoss.modelindex.constants import ZENOSS_MODEL_COLLECTION_NAME
from zenoss.modelindex.model_index import IndexUpdate, INDEX, UNINDEX, SearchParams
from Products.ZenUtils.AutoGCObjectReader import gc_cache_every

log = logging.getLogger('zenoss.model_catalog_reindexer')
log.setLevel(logging.INFO)

TERMINATE_SENTINEL = 'xxTERMINATExx'
MODEL_INDEX_BATCH_SIZE = 10000
INDEX_SIZE = 5000
QUEUE_TIMEOUT = 60


@contextmanager
def worker_context(worker):
    yield
    # notify parent one last time before exiting
    worker.notify_parent()
    log.info("Worker %s exiting", worker.idx)


def checkLogging(evt):
    if evt:
        loglevel = logging.DEBUG if evt.is_set() else logging.INFO
        if log.getEffectiveLevel() != loglevel:
            log.setLevel(loglevel)


class ReindexProcess(multiprocessing.Process):
    def __init__(self, error_queue, idx, worker_count, parent_queue, counter, semaphore, cond, cancel, terminator,
                 fields=None, logtoggle=None):
        super(ReindexProcess, self).__init__()

        self.error_queue = error_queue
        self.idx = idx
        self.worker_count = worker_count
        self.parent_queue = parent_queue
        self.counter = counter

        self.semaphore = semaphore
        self.cond = cond
        self.cancel = cancel
        self.terminator = terminator
        self.fields = fields
        self.logtoggle = logtoggle

        self.semaphore_acquired = False

        self._batch = []

        zsb = ZenScriptBase(connect=True, should_log=False)
        self.dmd = zsb.dmd
        self._db = zsb.db
        self.index_client = zope.component.createObject('ModelIndex', get_solr_config())

    def get_work(self):
        """
        Returns a uid for the current process to operate on.
        Should be implemented by a subclass.
        """
        raise NotImplementedError

    def batch_update(self, batch, commit=False):
        """
        Uses a Solr index client to perform a batch update of batch.
        """
        self.index_client.process_batched_updates(
            [IndexUpdate(node, op=INDEX, idxs=self.fields) for node in batch],
            commit=commit)

    def index(self, commit=False):
        if self._batch:
            self.batch_update(self._batch, commit)
            self._batch[:] = []

    def handle_exception(self):
        """
        Pass an error to the parent.
        """
        exc = sys.exc_info()
        self.error_queue.put((self.idx, traceback.format_exception(*exc)))
        self.notify_parent()

    def notify_parent(self, wait=False):
        """
	    Signal to the parent process that a worker has become idle or has
        encountered an exception.
        """
        with self.cond:
            self.cond.notify_all()
            if wait:
                self.cond.wait(timeout=QUEUE_TIMEOUT)

    def schedule_index(self, node):
        """
        Add a node to the batch. If the batch passes a threshold, index it.
        """
        self._batch.append(node)
        if len(self._batch) >= INDEX_SIZE:
            self.index(True)

    def process(self, uid):
        """
        Process a single uid.
        """
        raise NotImplementedError

    def acquire_semaphore(self):
        if not self.semaphore_acquired:
            self.semaphore.acquire(True)
            self.semaphore_acquired = True

    def release_semaphore(self):
        if self.semaphore_acquired:
            self.semaphore.release()
            self.semaphore_acquired = False

    def get_work_from_parent(self):
        try:
            # We hold the semaphore while we are waiting on the queue
            # This is safe to call multiple times
            self.acquire_semaphore()
            new_work = self.parent_queue.get(timeout=QUEUE_TIMEOUT)
            self.release_semaphore()
            return new_work
        except Queue.Empty:
            return None

    def run(self):
        """
        Operates on uids/nodes from get_work until exhausted.
        """
        with worker_context(self):
            with gc_cache_every(1000, self._db):
                count = 0
                while True:
                    if self.cancel.is_set() or self.terminator.is_set():
                        return
                    for uid in self.get_work():
                        if self.terminator.is_set():
                            # If terminator is set, we exit immediately, leaving data behind
                            return

                        checkLogging(self.logtoggle)

                        if uid == TERMINATE_SENTINEL:
                            log.debug('Worker %s found sentinel', self.idx)
                            self.cancel.set()
                            self.notify_parent(True)
                            break
                        try:
                            self.process(uid)
                        except Exception:
                            self.handle_exception()
                            continue
                        count += 1
                        # update our counter every so often (less lock usage)
                        if count >= 1000:
                            with self.counter.get_lock():
                                self.counter.value += count
                            count = 0
                            log.debug('Worker %s notifying parent of count update', self.idx)
                            self.notify_parent()
                    # Flush the index batch dregs
                    self.index(True)
                    if count:
                        with self.counter.get_lock():
                            self.counter.value += count
                        count = 0
                    # Should we die? Or wait for more work from the parent?
                    if self.cancel.is_set() or self.terminator.is_set():
                        return
                    log.debug('Worker %s notifying parent it is out of work', self.idx)
                    self.notify_parent(True)


class HardReindex(ReindexProcess):
    """
    A ReindexProcess which uses a tree splitting strategy to share work.

    General flow for a single HardReindex process is:
    If deque is empty, get node from parent queue.
    Else get node from right side of deque.
    Push node's children to right side of deque (if applicable).
    Add node to list of items to be indexed.
    Index all items in list if fit.
    If parent queue is empty, pop a node from left side of deque and push to parent queue.
    Repeat.
    """

    def __init__(self, *args, **kwargs):
        super(HardReindex, self).__init__(*args, **kwargs)
        if self.fields:
            raise Exception("Atomic updates not supported by hard reindexer")

        self.deque = deque()

    def get_work(self):
        while True:
            while self.deque:
                yield self.deque.pop()

            new_work = self.get_work_from_parent()
            if new_work:
                yield new_work

            # If we've gotten here and the deque is empty, we have nothing to do
            if not self.deque:
                log.debug("Worker %s is effectively idle", self.idx)
                return

    def process(self, uid):
        try:
            current_node = self.dmd.unrestrictedTraverse(uid)
            self._push_children(current_node)
            if self._include_node(current_node):
                self.schedule_index(current_node)
        finally:
            self._reconcile()

    def _get_children(self, node):
        if isinstance(node, ObjectManager):
            for ob in node.objectValues():
                if isinstance(ob, ZenModelRM):
                    yield ob
                elif isinstance(ob, ToManyContRelationship):
                    for o in ob.objectValuesGen():
                        yield o

    def _push_children(self, node):
        for child in self._get_children(node):
            self.deque.append("/".join(child.getPhysicalPath()))

    def _include_node(self, node):
        return isinstance(node, ZenModelRM) and not isinstance(node, GlobalCatalog)

    def _reconcile(self):
        try:
            if self.parent_queue.empty():
                idle = self.worker_count - self.semaphore.get_value()
                log.debug(
                    "Worker %s putting %s into parent queue. Remaining: %s",
                    self.idx, idle, len(self.deque))
                for _ in xrange(idle):
                    self.parent_queue.put(self.deque.popleft())
        except IndexError:
            pass


class SoftReindex(ReindexProcess):
    """
    A ReindexProcess which uses a workerpool style strategy to work.

    General flow for a single SoftReindex process is:
    Get node from parent queue.
    Add node to list of items to be indexed.
    Index all items in list if fit.
    Repeat.
    """

    def get_work(self):
        """
        Returns items from the parent queue until signaled to stop.
        """
        while True:
            new_work = self.get_work_from_parent()
            if new_work:
                yield new_work
            else:
                return

    def process(self, uid):
        current_node = self.dmd.unrestrictedTraverse(uid)
        self.schedule_index(current_node)


def get_uids(index_client, root="", types=()):
    start = 0
    need_results = True
    query = [Eq("tx_state", 0)]
    if root:
        root = root.rstrip('/')
        query.append(Or(Eq("uid", "{}".format(root)), MatchGlob("uid", "{}/*".format(root))))

    if not isinstance(types, (tuple, list)):
        types = (types,)

    if types:
        query.append(In("objectImplements", [dottedname(t) for t in types]))

    while need_results:
        search_results = index_client.search(SearchParams(
            query=And(*query),
            start=start,
            limit=MODEL_INDEX_BATCH_SIZE,
            order_by="uid",
            fields=["uid"]))
        start += MODEL_INDEX_BATCH_SIZE
        for result in search_results.results:
            yield result.uid
        need_results = start < search_results.total_count


def collection_exists(collection_name=ZENOSS_MODEL_COLLECTION_NAME):
    index_client = zope.component.createObject('ModelIndex', get_solr_config(), collection_name)
    return collection_name in index_client.get_collections()


def init_model_catalog(collection_name=ZENOSS_MODEL_COLLECTION_NAME):
    index_client = zope.component.createObject('ModelIndex', get_solr_config(), collection_name)
    config = {}
    config["collection_name"] = collection_name
    config["collection_config_name"] = collection_name
    config["num_shards"] = 1
    index_client.init(config)
    return index_client


def run(processor_count=8, hard=False, root="", indexes=None, types=(), terminator=None, toggle_debug=None):
    if hard and (root or indexes or types):
        raise Exception("Root node, indexes, and types can only be specified during soft re-index")

    log.info("Beginning %s redindexing with %s child processes.",
             "hard" if hard else "soft", processor_count)

    start = time.time()

    log.info("Initializing model database and Solr model catalog...")
    dmd = ZenScriptBase(connect=True).dmd
    index_client = init_model_catalog()

    processes = []
    error_queue = multiprocessing.Queue()
    parent_queue = multiprocessing.Queue()
    counter = multiprocessing.Value(ctypes.c_uint32)
    semaphore = multiprocessing.Semaphore(processor_count)
    cond = multiprocessing.Condition()

    if not terminator:
        terminator = multiprocessing.Event()

    cancel = multiprocessing.Event()

    processes_remaining = 0
    work = []
    Worker = None

    proc_start = time.time()

    def hard_index_is_done():
        return terminator.is_set() or (semaphore.get_value() == 0 and parent_queue.empty())

    def soft_index_is_done():
        return cancel.is_set() or terminator.is_set()

    # In the case of early termination, we only want to wait up to 30 seconds
    # In the case of straggler processes, we wait up to an hour
    def get_timeout():
        if terminator.is_set():
            return 30
        return 3600

    if hard:
        log.info("Clearing Solr data")
        index_client.clear_data()
        work.append("/zport")
        Worker = HardReindex
        is_done = hard_index_is_done
    else:
        log.info("Reading uids from Solr")
        work = get_uids(index_client, root, types)
        Worker = SoftReindex
        is_done = soft_index_is_done

    log.info("Starting child processes")
    for n in range(processor_count):
        p = Worker(error_queue, n, processor_count, parent_queue, counter, semaphore, cond, cancel, terminator, indexes,
                   toggle_debug)
        processes.append(p)
        p.start()

    for uid in work:
        parent_queue.put(uid)

    if not hard:
        # Put the terminate sentinel at the end of the queue
        parent_queue.put(TERMINATE_SENTINEL)

    log.info("Waiting for processes to finish")

    lastcount = 0
    last = start
    while True:
        with cond:
            # soft_index_is_done is actually appropriate in both cases
            if soft_index_is_done():
                log.info("Terminating condition met. Done!")
                cancel.set()
                # In case we were terminated before we were waiting
                cond.notify_all()
                break
            cond.wait()

            checkLogging(toggle_debug)

            try:
                # Print any errors we've built up
                while not error_queue.empty():
                    try:
                        idx, exc = error_queue.get_nowait()
                    except Queue.Empty:
                        pass  # This shouldn't happen, but just in case there's a race somehow
                    else:
                        log.error("Indexing process %s encountered an exception: %s", idx, exc)
                # Print status
                with counter.get_lock():
                    delta = counter.value - lastcount
                    if delta > MODEL_INDEX_BATCH_SIZE:
                        now = time.time()
                        persec = delta / (now - last)
                        last, lastcount = now, counter.value
                        log.info("Indexed %s objects (%s/sec)", lastcount, persec)
                # Check to see if we're done
                log.debug("%s workers still busy", semaphore.get_value())
                log.debug("parent queue is %sempty", "" if parent_queue.empty() else "not ")
                if is_done():
                    # All workers are idle and there's no more work to do, so the end
                    log.info("Terminating condition met. Done!")
                    cancel.set()
                    break
            finally:
                # Pass the ball back to the child that notified
                cond.notify_all()
    log.info("Indexing complete, waiting for workers to clean up")
    for proc in processes:
        log.debug("Joining proc %s", proc.idx)
        proc.join(get_timeout())
        if proc.is_alive():
            log.warn("Worker %s did not exit within timeout, terminating...", proc.idx)
            proc.terminate()
    end = time.time()
    log.info("Total time: %s", end - start)
    log.info("Time to initialize: %s", proc_start - start)
    log.info("Time to process and reindex: %s", end - proc_start)
    log.info("Number of objects indexed: %s", counter.value)


def reindex_model_catalog(dmd, root="/zport", idxs=None, types=()):
    """
    Performs a single threaded soft reindex
    """
    start = time.time()
    log.info("Performing soft reindex on model_catalog. Params = root:'%s' / idxs:'%s' / types:'%s'", root, idxs, types)
    modelindex = init_model_catalog()
    uids = get_uids(modelindex, root=root, types=types)
    if uids:
        index_updates = []
        for uid in uids:
            try:
                obj = dmd.unrestrictedTraverse(uid)
            except (KeyError, NotFound):
                log.warn("Stale object found in Solr: %s", uid)
                index_updates.append(IndexUpdate(None, op=UNINDEX, uid=uid))
            else:
                index_updates.append(IndexUpdate(obj, op=INDEX, idxs=idxs))
            if len(index_updates) % 1000 == 0:
                modelindex.process_batched_updates(index_updates, commit=False)
                index_updates = []
        if index_updates:
            modelindex.process_batched_updates(index_updates, commit=True)
        else:
            modelindex.commit()
    log.info("Reindexing took %s seconds.", time.time() - start)


def main():
    parser = argparse.ArgumentParser(description="Reindex Solr against ZODB.")
    parser.add_argument("-f", "--hard", action="store_true",
                        help="wipe Solr data and traverse the entire ZODB tree")
    parser.add_argument("-p", "--procs", type=int, default=8,
                        help="use n child processes (default 8)")
    parser.add_argument("-r", "--root", type=str, default="",
                        help="root of subtree to reindex (soft-reindex only)")
    parser.add_argument("-i", "--indexes", type=str, nargs='+', default=[],
                        help="list of fields to update (soft-reindex only)")
    parser.add_argument("-t", "--types", type=str, nargs='+', default=[],
                        help="list of object types to re-index (soft-reindex only)")
    args = parser.parse_args()
    # Something else seems to want to parse our args, so reset them
    sys.argv = sys.argv[:1]
    run(args.procs, args.hard, args.root, args.indexes, args.types)
