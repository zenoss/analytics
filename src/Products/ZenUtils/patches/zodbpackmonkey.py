##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
This module patches relstorage.adapters.packundo.HistoryFreePackUndo to prevent
the creation of POSKey errors during the execution of zodbpack.

Patched methods in HistoryFreePackUndo:
    def _pre_pack_main(self, conn, cursor, pack_tid, get_references)
    def pack(self, pack_tid, sleep=None, packed_func=None)
    def fill_object_refs(self, conn, cursor, get_references)

Patched methods in PackUndo:
    def _traverse_graph(self, cursor)

"""

from relstorage.adapters.connections import LoadConnection, PrePackConnection
from Products.ZenUtils.Utils import monkeypatch
from collections import defaultdict, deque
from itertools import groupby
from operator import itemgetter

import logging
import multiprocessing
import os
import pickle
import time

def set_up_logger():
    log_format = "%(asctime)s [%(name)s] %(levelname)s %(message)s"
    logging.basicConfig(filename='/opt/zenoss/log/zenossdbpack.log', filemode='a', level=logging.INFO, format=log_format)
    #set up logging to console for root logger
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(log_format))
    logging.getLogger('').addHandler(console)


log = logging.getLogger("zenoss.zodbpack.monkey")

GLOBAL_OPTIONS = {}

def set_external_option(option, value=True):
    """
    Supported options:
        "BUILD_TABLES_ONLY"
        "N_WORKERS"
        "MINIMIZE_MEMORY_USAGE"
    """
    GLOBAL_OPTIONS[option] = value


class ZodbPackMonkeyHelper(object):

    VERSION = '1.3'
    REF_TABLE_NAME = 'object_ref'
    REVERSE_REF_INDEX = 'reverse_ref_index'
    PICKLE_FILENAME = 'zodbpack_skipped_oids.pickle'
    ROLLBACK_OIDS_FILENAME = 'zodbpack_rollback_oids.txt'

    class ReferencesMap(object):
        def __init__(self):
            self.refs_to = defaultdict(set) # list of objects a specific oid references to
            self.refs_from = defaultdict(set) # list of objects that reference a specific oid

        def add_reference(self, ref, log=False):
            """
            @param ref: tuple (zoid, to_zoid)
            """
            oid, to_oid = ref
            self.refs_to[oid].add(to_oid)
            self.refs_from[to_oid].add(oid)

        def get_references(self, oid):
            """ returns objects that are at distance 1 from oid  """
            return self.refs_to[oid] | self.refs_from[oid]

    def create_reverse_ref_index(self, store_connection):
        """
        Checks if the reverser reference index exists on the
        reference table and creates the index if it does not exist
        """
        sql = """ SHOW INDEX FROM {0} WHERE key_name='{1}'; """.format(self.REF_TABLE_NAME, self.REVERSE_REF_INDEX)
        cursor = store_connection.cursor
        cursor.execute(sql)
        if cursor.rowcount == 0:
            log.info("Creating reverse reference index on %s", self.REF_TABLE_NAME)
            start = time.time()
            index_sql = """ CREATE INDEX {0} ON {1} (to_zoid); """.format(self.REVERSE_REF_INDEX, self.REF_TABLE_NAME)
            cursor.execute(index_sql)
            log.info("Reverse reference index creation took %s seconds.", time.time()-start)

    def get_current_database(self, cursor):
        sql = """SELECT DATABASE();"""
        cursor.execute(sql)
        return cursor.fetchall()[0][0]

    def delete_batch(self, cursor, batch):
        sql = """ DELETE FROM object_state WHERE zoid = %s AND tid = %s """
        count = cursor.executemany(sql, batch)
        return count

    def log_exception(self, e, info=''):
        log.error("Monkey patch for zodbpack raised and exception: %s: %s", info, e)

    def unmark_rolledback_oids(self, conn, cursor, oids):
        """
        Unmark the oids from pack_object so _pack_cleanup wont remove them from object_refs_added and object_ref
        """
        batch_size=10000
        to_remove = oids[:]
        while to_remove:
            batch = to_remove[:batch_size]
            del to_remove[:batch_size]
            values = ','.join( str(zoid) for zoid, tid in batch )
            sql = """UPDATE pack_object SET keep = TRUE WHERE zoid IN ({0});""".format(values)
            cursor.execute(sql)
        conn.commit()

    def _get_references(self, cursor, batch):
        """
        @param batch: list of oids
        Returns all references where oid is in zoid or to_zoid
        """
        values = ','.join(str(zoid) for zoid, tid in batch)
        sql = """ SELECT zoid, to_zoid FROM {0} WHERE zoid!=to_zoid AND (zoid IN ({1}) OR to_zoid IN ({1}))""".format(self.REF_TABLE_NAME, values)
        cursor.execute(sql)
        result = cursor.fetchall()
        return result

    def _get_oid_references(self, cursor, oids):
        """
        Builds a 'ReferencesMap' containing all references from and to each oid in oids
        """
        references_map = ZodbPackMonkeyHelper.ReferencesMap()
        zoids = oids[:]
        batch_size = 10000
        while zoids:
            start = time.time()
            batch = zoids[:batch_size]
            del zoids[:batch_size]
            references = self._get_references(cursor, batch)
            for r in references:
                references_map.add_reference(r)
        return references_map

    def _get_connected_oids_to(self, oid, references, visited):
        """ returns objects that are at distance 1 from oid and have not been already visited """
        objects = references.get_references(oid)
        return [ oid for oid in objects if visited.get(oid) is not None ]

    def _get_connected_oids(self, initial_oid, references, visited):
        """ breadth-first search to find all reachable oids from 'initial_oid' """
        connected_oids = []
        queue = {initial_oid}
        while queue:
            current_oid = queue.pop()
            del visited[current_oid]
            connected_oids.append(current_oid)
            queue.update(self._get_connected_oids_to(current_oid, references, visited))
        return connected_oids

    def _validate_group(self, group, to_remove, references):
        """
        For some reason, zodbpack sometimes marks objects for removal even if those objects are
        still referenced by objects that have not been marked for removal. We need to check that all objects to be removed
        are only referenced by other objects that have also been marked for removal.
        If we detect an oid that is referenced by an oid not marked for removal, we will just not delete it.
        """
        valid = True
        for oid in group:
            refs = references.refs_from[oid]
            if not all( r in to_remove for r in refs):
                valid = False
                break
        return valid

    def group_oids(self, cursor, to_remove):
        """
        Return a list of grouped oids. Each group represents oids that are part
        of the same 'zenoss object'. All oids in a group have to be deleted in a
        transactional way to avoid PKE (todos o ninguno)
        """
        references = self._get_oid_references(cursor, to_remove)
        oids_to_remove = { oid for (oid, tid) in to_remove }  # Let's work only with oids to make code more readable
        visited = { oid:False for oid in oids_to_remove }

        # Group connected oids
        grouped_oids = []
        while visited:
            oid, vis = visited.popitem()
            visited[oid] = vis
            connected_oids = self._get_connected_oids(oid, references, visited)
            grouped_oids.append(connected_oids)

        # For each group, check that it is safe to delete it and add the tid to the oids
        oid_tid_mapping = dict(to_remove)
        grouped_oids_with_tid = []
        skipped_oids = []
        to_remove = []
        for group in grouped_oids:
            group_with_tid = []
            for oid in group:
                group_with_tid.append((oid, oid_tid_mapping[oid]))

            if self._validate_group(group, oids_to_remove, references):
                grouped_oids_with_tid.append(group_with_tid)
                to_remove.extend(group_with_tid)
            else:
                skipped_oids.extend(group_with_tid)

        return (grouped_oids_with_tid, to_remove, skipped_oids)

    def _get_count_in_table(self, cursor, oids_to_check, table_name, select_fields, where_fields):
        """ method to perform queries needed for tests """
        oids = list(oids_to_check)
        count = 0
        batch_size = 10000
        if isinstance(select_fields, list):
            select_fields = ", ".join(select_fields)
        if isinstance(where_fields, list):
            where_fields =  ", ".join(where_fields)
        while oids:
            batch = oids[:batch_size]
            del oids[:batch_size]
            values = ", ".join(batch)
            sql = """ SELECT COUNT({0}) FROM {1} WHERE {2} IN ({3});""".format(select_fields, table_name, where_fields, values)
            cursor.execute(sql)
            count = count + cursor.fetchall()[0][0]
        return count

    def _print_test_result(self, text, passed):
        text = text.ljust(50, '.')
        result = "PASSED"
        if not passed:
            result = "FAILED"
        log.info("%s%s", text, result.rjust(8))

    def run_post_pack_tests(self, cursor, marked_for_removal, to_remove, oids_not_removed):
        """
        Checks that the db tables have been left in a consistent state
        """
        if len(to_remove) == 0:
            log.info("Validating results: No oids were deleted")
            return

        to_remove = set([ str(oid) for oid, tid in to_remove ])
        not_removed = set([ str(oid) for oid, tid in oids_not_removed])
        removed = to_remove - to_remove.intersection(not_removed)
        log.info("Validating results: %s oids marked for removal / %s oids removed / %s oids skipped.",
                 marked_for_removal, len(to_remove), len(not_removed))

        # Check tables state, deleted oids must not be in any of the tables and
        # not deleted oids must be in all tables
        #
        tables = [ "object_state", "object_refs_added" ]
        for table in tables:
            removed_count = self._get_count_in_table(cursor, removed, table, "zoid", "zoid")
            not_removed_count = self._get_count_in_table(cursor, not_removed, table, "zoid", "zoid")
            passed = ( removed_count==0 and not_removed_count==len(not_removed) )
            self._print_test_result("Validating {0}".format(table), passed)

        # removed objects must not have any references from or to in the references tables
        # for references tables check that removed oids are not in the tables
        table = 'object_ref'
        r_from = self._get_count_in_table(cursor, removed, table, "zoid", "zoid")
        r_to = self._get_count_in_table(cursor, removed, table, "zoid", "to_zoid")
        passed = ( r_from==0 and r_to==0 )
        self._print_test_result("Validating {0}".format(table), passed)

    def create_pickle(self, skipped_oids, path, filename):
        """
        Creates a pickle of the (oids,tid) that have not been
        packed bc the object changed between pre pack and pack
        phases. This can be useful to find out what orphan oids
        changed during zodbpack.
        """
        try:
            pfile = open(filename, "wb")
            pickle.dump(skipped_oids, pfile)
            pfile.close()
            log.info("Not deleted oids pickled to file: %s", filename)
        except Exception as e:
            self.log_exception(e, "Failed to create pickle with skipped oids")

    def _get_rolledback_oids(self, cursor, skipped_oids):
        if skipped_oids:
            batch_size=10000
            skipped = skipped_oids[:]
            object_state_data = []
            while skipped:
                batch = skipped[:batch_size]
                del skipped[:batch_size]
                values = ','.join( str(oid) for oid, tid in batch )
                sql = """SELECT zoid, tid FROM object_state WHERE zoid IN ({0})""".format(values)
                cursor.execute(sql)
                object_state_data.extend(cursor.fetchall())

            data = set(object_state_data) - set(skipped_oids)
            return [ str(oid) for oid, tid in data ]

    def export_rolledback_oids_to_file(self, cursor, skipped_oids, filename):
        """ Export to a file the oids that changed between prepack and pack phases """
        try:
            pfile = open(filename, "w")
            rolledback_oids = self._get_rolledback_oids(cursor, skipped_oids)
            pfile.write('-'*75)
            pfile.write('\nThe oids below were marked for deletion by zenossdbpack but a later');
            pfile.write('\ntransaction updated the object before it was deleted.');
            pfile.write('\nTo find out the type of the objects, paste the following code in zendmd:\n');
            pfile.write('-'*75)
            pfile.write('\nfrom ZODB.utils import p64');
            values = ",".join([ oid for oid in rolledback_oids ])
            pfile.write('\nfor oid in [{0}]: print dmd._p_jar[p64(oid)]\n'.format(values));
            pfile.write('-'*75)
            pfile.write('\n')
            pfile.write('\n'.join(rolledback_oids));
            log.info("Mofified oids between pre_pack and pack dumped to file: %s", filename)
        except Exception as e:
            self.log_exception(e, "Failed to create file with skipped oids")

    def export_rolledback_oids(self, cursor, skipped_oids):
        """ """
        try:
            db = self.get_current_database(cursor)
            zenhome = os.environ.get('ZENHOME', os.path.join('opt', 'zenoss'))
            path = os.path.join(zenhome, 'log')

            filename = os.path.join(path, '{0}_{1}'.format(db, self.PICKLE_FILENAME))
            self.create_pickle(skipped_oids, path, filename)

            filename = os.path.join(path, '{0}_{1}'.format(db, self.ROLLBACK_OIDS_FILENAME))
            self.export_rolledback_oids_to_file(cursor, skipped_oids, filename)

        except Exception as e:
            self.log_exception(e, "Failed to export skipped oids")

MONKEY_HELPER = ZodbPackMonkeyHelper()


def duration_to_pretty_text(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "%dh:%02dm:%02ds" % (h, m, s)

'''
#========================================================================
#                      RELSTORAGE MONKEY PATCHES
#========================================================================
'''
try:

    from relstorage.adapters.packundo import PackUndo
    from relstorage.adapters.packundo import HistoryFreePackUndo
    from persistent.TimeStamp import TimeStamp # pylint:disable=import-error
    from ZODB.POSException import ReadOnlyError
    from ZODB.utils import u64
    from ZODB.utils import p64

    @monkeypatch('relstorage.adapters.packundo.HistoryFreePackUndo')
    def pre_pack(self, pack_tid, get_references):
        """Decide what the garbage collector should delete.

        Objects created or modified after pack_tid will not be
        garbage collected.

        get_references is a function that accepts a pickled state and
        returns a set of OIDs that state refers to.

        The self.options.pack_gc flag indicates whether to run garbage
        collection.  If pack_gc is false, this method does nothing.
        """
        if not self.options.pack_gc:
            log.warning("pre_pack: garbage collection is disabled on a "
                        "history-free storage, so doing nothing")
            return

        load_connection = LoadConnection(self.connmanager)
        store_connection = PrePackConnection(self.connmanager)
        try:
            try:
                self._pre_pack_main(load_connection, store_connection, pack_tid, get_references)
            except Exception:
                log.exception("pre_pack: failed")
                store_connection.rollback_quietly()
                raise
            else:
                store_connection.commit()
                log.info("pre_pack: finished successfully")
        finally:
            load_connection.drop()
            store_connection.drop()

    @monkeypatch('relstorage.adapters.packundo.HistoryFreePackUndo')
    def _pre_pack_main(self, load_connection, store_connection, pack_tid, get_references):
        """
        Determine what to garbage collect.
        """
        ################################
        ### BEGIN ZENOSS CUSTOM CODE ###
        ################################

        log.info("Running with the following options: %s", GLOBAL_OPTIONS)
        # Create reverse ref index
        MONKEY_HELPER.create_reverse_ref_index(store_connection)

        ##############################
        ### END ZENOSS CUSTOM CODE ###
        ##############################

        log.info("pre_pack: filling the pack_object table")
        # Fill the pack_object table with all known OIDs.
        stmt = """
        %(TRUNCATE)s pack_object;

        INSERT INTO pack_object (zoid, keep, keep_tid)
        SELECT zoid, CASE WHEN tid > %(pack_tid)s THEN %(TRUE)s ELSE %(FALSE)s END, tid
        FROM object_state;

        -- Also keep the root
        UPDATE pack_object
        SET keep = %(TRUE)s
        WHERE zoid = 0;
        """

        self.runner.run_script(store_connection.cursor, stmt, {'pack_tid': pack_tid})
        store_connection.commit()
        log.info("pre_pack: Filled the pack_object table")

        # Chase down all the references using a consistent snapshot, including
        # only the objects that were visible in ``pack_object``.
        self.fill_object_refs(load_connection, store_connection, get_references)

        # Traverse the graph, setting the 'keep' flags in pack_object
        self._traverse_graph(load_connection, store_connection)

    #------------------ Functions related to pack method ---------------------


    def get_grouped_oids(cursor, oids_to_remove):
        """ Groups oids to be removed in groups of connected objects """
        group_start = time.time()

        try:
            result = MONKEY_HELPER.group_oids(cursor, oids_to_remove)
        except Exception as e:
            MONKEY_HELPER.log_exception(e, "Exception while grouping oids")
            raise e

        explore_references_time = time.time() - group_start
        if explore_references_time > 1:
            explore_references_time = str(explore_references_time).split('.')[0]
            log.info("Exploring oid connections took %s seconds.", explore_references_time)

        return result


    @monkeypatch('relstorage.adapters.packundo.HistoryFreePackUndo')
    def remove_isolated_oids(self, conn, cursor, grouped_oids, packed_func, total, oids_processed):
        """
        objects that not connected to other objects can be safely removed.
        """
        # We'll report on progress in at most .1% step increments
        reportstep = max(total / 1000, 1)
        if oids_processed == 0:
            lastreport = 0
        else:
            lastreport = oids_processed / reportstep * reportstep

        isolated_oids = []
        for oids_group in grouped_oids:
            if len(oids_group) == 1:
                isolated_oids.extend(oids_group)

        packed_list = []
        batch_size = 100
        start = time.time()
        while isolated_oids:
            batch = isolated_oids[:batch_size]
            del isolated_oids[:batch_size]

            MONKEY_HELPER.delete_batch(cursor, batch)

            oids_processed = oids_processed + len(batch)

            if time.time() >= start + self.options.pack_batch_timeout:
                conn.commit()
                if packed_func is not None:
                    for oid, tid in packed_list:
                        packed_func(oid, tid)
                    del packed_list[:]
                counter = oids_processed
                if counter >= lastreport + reportstep:
                    log.info("pack: processed %d (%.1f%%) state(s)",
                        counter, counter/float(total)*100)
                    lastreport = counter / reportstep * reportstep
                start = time.time()

        if packed_func is not None:
            for oid, tid in packed_list:
                packed_func(oid, tid)
        conn.commit()
        self.locker.release_commit_lock(cursor)

        return oids_processed


    @monkeypatch('relstorage.adapters.packundo.HistoryFreePackUndo')
    def remove_connected_oids(self, conn, cursor, grouped_oids, packed_func, total, oids_processed):
        """
        connected oids must be removed all or none
        """
        # We'll report on progress in at most .1% step increments
        reportstep = max(total / 1000, 1)
        if oids_processed == 0:
            lastreport = 0
        else:
            lastreport = oids_processed / reportstep * reportstep

        batch_size = 1000 # some batches can be huge and we are holding the commit lock
        prevent_pke_oids = [] # oids that have not been deleted to prevent pkes
        rollbacks = 0
        start = time.time()
        for oids_group in grouped_oids:
            if len (oids_group) == 1:
                # isolated oids are processed by other method
                continue
            rollback = False
            oid_batches = oids_group[:]
            while oid_batches and not rollback:
                batch = oid_batches[:batch_size]
                del oid_batches[:batch_size]
                count = MONKEY_HELPER.delete_batch(cursor, batch)
                # Check that no objects have been modified between deleting batches
                if count != len(batch):
                    rollback = True
                    break
            if rollback:
                conn.rollback()
                rollbacks = rollbacks + 1
                prevent_pke_oids.extend(oids_group)
            else:
                conn.commit()
                if packed_func is not None:
                    for oid, tid in oids_group:
                        packed_func(oid, tid)

            oids_processed = oids_processed + len(oids_group)
            if time.time() >= start + self.options.pack_batch_timeout:
                counter = oids_processed
                if counter >= lastreport + reportstep:
                    log.info("pack: processed %d (%.1f%%) state(s)",
                        counter, counter/float(total)*100)
                    lastreport = counter / reportstep * reportstep
                start = time.time()

        if prevent_pke_oids:
            log.info("%s oid groups were skipped. (%s oids)", rollbacks, len(prevent_pke_oids))
            # unmark the oids from pack_object so _pack_cleanup wont remove them from object_refs_added and object_ref
            MONKEY_HELPER.unmark_rolledback_oids(conn, cursor, prevent_pke_oids)
            """
            # This is one useful during debugging and testing only
            try:
                MONKEY_HELPER.export_rolledback_oids(cursor, prevent_pke_oids)
            except Exception as e:
                MONKEY_HELPER.log_exception(e, "Exception while exporting skipped oids.")
            """
        return prevent_pke_oids


    @monkeypatch('relstorage.adapters.packundo.HistoryFreePackUndo')
    def pack(self, pack_tid, packed_func=None):
        """ Run garbage collection. Requires the information provided by pre_pack. """

        if "BUILD_TABLES_ONLY" in GLOBAL_OPTIONS:
            log.info("pack: Skipping pack phase.")
            return

        # Read committed mode is sufficient.
        conn, cursor = self.connmanager.open_for_store()
        try:
            try:
                stmt = """
                SELECT zoid, keep_tid
                FROM pack_object
                WHERE keep = %(FALSE)s
                ORDER BY zoid
                """
                self.runner.run_script_stmt(cursor, stmt)
                to_remove = list(cursor)
                marked_for_removal = len(to_remove)
                log.info("pack: %d object(s) marked to be removed", marked_for_removal)

                if marked_for_removal > 0:
                    log.info("Grouping connected oids... (may take a while)")

                    grouped_oids, to_remove, skipped_oids = get_grouped_oids(cursor, to_remove)

                    if skipped_oids:
                        log.info("%s oids will be skipped.", len(skipped_oids))
                        MONKEY_HELPER.unmark_rolledback_oids(conn, cursor, skipped_oids)

                    total = len(to_remove)
                    log.info("pack: will remove %d object(s)", total)

                    if total:
                        # Hold the commit lock while packing to prevent deadlocks.
                        # Pack in small batches of transactions only after we are able
                        # to obtain a commit lock in order to minimize the
                        # interruption of concurrent write operations.
                        log.info("Removing objects...")

                        oids_processed = self.remove_isolated_oids(conn, cursor, grouped_oids, packed_func, total, 0)

                        prevent_pke_oids = self.remove_connected_oids(conn, cursor, grouped_oids, packed_func, total, oids_processed)

                        store_connection = PrePackConnection(self.connmanager)

                        self._pack_cleanup(store_connection=store_connection)

                        try:
                            if skipped_oids:
                                prevent_pke_oids.extend(skipped_oids)
                            MONKEY_HELPER.run_post_pack_tests(cursor, marked_for_removal, to_remove, prevent_pke_oids)
                        except Exception as e:
                            MONKEY_HELPER.log_exception(e, "Execption while running tests.")

            except Exception:
                log.exception("pack: failed")
                conn.rollback()
                raise
            else:
                log.info("pack: finished successfully")
                conn.commit()
        finally:
            self.connmanager.close(conn, cursor)

    @monkeypatch('relstorage.adapters.packundo.HistoryFreePackUndo')
    def _add_refs_for_oids(self, load_batcher, store_batcher, oids, get_references):

        """
        Fill object_refs with the states for some objects.

        Returns the number of references added.
        """
        # oids should be a slice of an ``OidList``, which may be an
        # ``array.array``; those are relatively slow to iterate.

        # The batcher always does deletes before inserts, which is
        # exactly what we want.
        # In the past, we performed all deletes and then all inserts;
        # now, things to batching, they could be interleaved, but
        # because we process OID-by-OID, that should be fine.
        # In the past, we also DELETED from object_refs_added and object_ref
        # everything found in the ``oids`` parameter; now we only do a delete if
        # we get back a row from object_state; again, that shouldn't matter, rows
        # should be found in object_state.
        object_ref_schema = store_batcher.row_schema_of_length(3)
        object_refs_added_schema = store_batcher.row_schema_of_length(2)

        # Use the batcher to get efficient ``= ANY()``
        # queries, but go ahead and collect into a list at once
        rows = list(load_batcher.select_from(
            ('zoid', 'tid', 'state'),
            'object_state',
            suffix=' ORDER BY zoid ',
            zoid=oids
        ))

        num_refs_found = 0

        for from_oid, tid, state in rows:
            state = self.driver.binary_column_as_state_type(state)
            row = (from_oid, tid)
            # Check if the row already exists
            existing_row = store_batcher.select_from(
                'object_refs_added',
                ('zoid',),
                zoid=from_oid
            )

            # We monkey-patched this method to add the check below (everything else is the same as the original
            # relstorage.adapters.packundo.HistoryFreePackUndo._add_refs_for_oids).
            # This check helps avoid an IntegrityError,
            # which started occurring after upgrading RelStorage to version 3.5.0.
            # Previously, before inserting the zoid, it was first deleted from the object_refs_added table.
            if not existing_row:
                store_batcher.insert_into(
                    'object_refs_added (zoid, tid)',
                    object_refs_added_schema,
                    row,
                    row,
                    size=2
                )

            store_batcher.delete_from(
                'object_refs_added',
                zoid=from_oid
            )
            store_batcher.delete_from(
                'object_ref',
                zoid=from_oid
            )

            if state:
                try:
                    to_oids = get_references(state)
                except:
                    log.exception(
                        "pre_pack: can't unpickle "
                        "object %d in transaction %d; state length = %d",
                        from_oid, tid, len(state)
                    )
                    raise

                for to_oid in to_oids:
                    row = (from_oid, tid, to_oid)
                    num_refs_found += 1
                    store_batcher.insert_into(
                        'object_ref (zoid, tid, to_zoid)',
                        object_ref_schema,
                        row,
                        row,
                        size=3
                    )

        return num_refs_found


    '''
    Methods added to support packing systems that have not been packed for a long time
    and that cause zenossdbpack to crash with an OOM error
    '''

    REPORT_PERIOD = 60
    OIDS_PER_TASK = 1000

    class RefTableWorker(multiprocessing.Process):
        def __init__(self, tasks_queue, results_queue, load_connection,
                    store_connection, context, get_references):
            multiprocessing.Process.__init__(self)
            self.tasks_queue = tasks_queue
            self.results_queue = results_queue
            self.context = context
            self.get_references = get_references
            self.oids_processed = 0
            self.load_connection = load_connection
            self.store_connection = store_connection

        def run(self):
            last_report = time.time()
            task_dequeued = False
            while True:
                try:
                    task = self.tasks_queue.get()
                    task_dequeued = True
                    if task is None:
                        break # poison pill
                    else:
                        self.context._add_refs_for_oids(self.load_connection, self.store_connection, task, self.get_references)
                        self.store_connection.commit()
                        self.oids_processed = self.oids_processed + len(task)
                        now = time.time()
                        if now > last_report + REPORT_PERIOD:
                            last_report = now
                            self.results_queue.put( (self.name, self.oids_processed) )
                except (KeyboardInterrupt, Exception) as e:
                    if isinstance(e, KeyboardInterrupt):
                        log.info("%s: Stopping worker...", self.name)
                    else:
                        log.exception("%s: Exception in worker while building ref tables. %s", self.name, e)
                    self.store_connection.rollback()
                    break
                finally:
                    if task_dequeued:
                        self.tasks_queue.task_done()
                        task_dequeued = False
            self.load_connection.drop()
            self.store_connection.drop()


    def _log_ref_tables_progress(processed, total, proccessed_last_report):
        proccessed_since_last_report = processed - proccessed_last_report
        progress = float((processed*100) / float(total))
        txt_percentage = "{0:.2f}%".format(progress)
        txt_progress = "Progress: {0} completed".format(txt_percentage.rjust(7))
        txt_processed = str(processed).rjust(9)
        txt_remaining = str(total - processed).rjust(9)
        txt_proccessed_since_last_report = str(proccessed_since_last_report).rjust(8)
        log.info(
            "%s  | Processed: %s | Remaining: %s | Processed since last report: %s",
            txt_progress, txt_processed, txt_remaining, txt_proccessed_since_last_report,
        )

    def _get_n_workers(total_oids):
        if "N_WORKERS" in GLOBAL_OPTIONS and GLOBAL_OPTIONS["N_WORKERS"] > 0:
            n_workers = GLOBAL_OPTIONS["N_WORKERS"]
        else:
            n_workers = multiprocessing.cpu_count() * 2
            batches_needed = int(total_oids / OIDS_PER_TASK) + 1
            if batches_needed < n_workers:
                n_workers = batches_needed
            n_workers = min(n_workers, 16)  # max of 16 workers
        return n_workers

    def _get_tasks(oids):
        """ Group oids in tasks of OIDS_PER_TASK oids. @return deque """
        start = time.time()
        tasks = deque()
        for step in xrange(0, len(oids), OIDS_PER_TASK):
            task = oids[step:step+OIDS_PER_TASK]
            tasks.append(task)
        return tasks

    #need to look whether we need connectios in args
    @monkeypatch('relstorage.adapters.packundo.HistoryFreePackUndo')
    def workerized_ref_tables_builder(self, oids, load_connection, store_connection, get_references):
        """
        Use multiple workers to build ref tables
        """
        start = time.time()
        total_oids = len(oids)
        n_workers = _get_n_workers(total_oids)
        log.info("Starting %s workers to build ref tables...", n_workers)
        # Get tasks
        tasks = _get_tasks(oids)
        oids = None # free some mem
        # Create work queues
        tasks_queue = multiprocessing.JoinableQueue()
        results_queue = multiprocessing.Queue()
        # Start workers
        workers = []
        for i in range(n_workers):
            worker = RefTableWorker(tasks_queue,
                                    results_queue,
                                    load_connection,
                                    store_connection,
                                    self,
                                    get_references
                                    )
            worker.start()
            workers.append(worker)
        time.sleep(2)
        try:
            reports = {}
            last_report = 0
            processed = 0
            queueing_done = False
            while True:
                """ Give work to workers """
                if not queueing_done:
                    for _ in xrange(2*len(workers)): # make sure workers have enough stuff to do
                        if not tasks:
                            break
                        task = tasks.popleft()
                        try:
                            tasks_queue.put_nowait(task)  # task is a batch of OIDS_PER_TASK oids
                        except multiprocessing.Queue.Full: # queue is full
                            tasks.appendleft(task)
                            log.info("Main process: sleeping 60 seconds. Tasks queue is full...")
                            time.sleep(60)

                    if not tasks and not queueing_done:
                        queueing_done = True
                        for worker in workers:
                            tasks_queue.put(None) # poison pill

                """ Process reports from workers """
                while not results_queue.empty(): # Process messages from workers
                    try:
                        result = results_queue.get(block=False)
                        reports[result[0]] = result[1]  # {worker_id: oids_processed so far}
                    except multiprocessing.Queue.Empty:
                        break # No items ready in queue event though results_queue.empty said otherwise

                """ Report status """
                if time.time() > last_report + REPORT_PERIOD:  # Report
                    new_processed = sum(reports.values())
                    _log_ref_tables_progress(new_processed, total_oids, processed)
                    last_report = time.time()
                    processed = new_processed

                """ Check if workers are done, otherwise take a nap """
                workers = [ w for w in workers if w.is_alive() ]
                if workers:
                    if queueing_done:
                        log.debug("Waiting for workers to finish")
                        time.sleep(1) # sleep a little, workers are busy
                else:
                    if queueing_done:
                        break # we are done!
                    else: # oh oh, workers are dead
                        raise Exception("Workers are dead")

        except (Exception, KeyboardInterrupt) as e:
            if isinstance(e, KeyboardInterrupt):
                log.warn("Building reference tables interrupted.")
            else:
                log.exception("Exception while building ref tables. %s", e)
            while not results_queue.empty():
                results_queue.get(block=False)
            for worker in workers:
                worker.terminate()
                worker.join()
            tasks_queue.close()
            results_queue.close()
            raise e
        else:
            tasks_queue.close()
            tasks_queue.join()
            results_queue.close()
            for worker in workers:
                worker.join()


    @monkeypatch('relstorage.adapters.packundo.HistoryFreePackUndo')
    def patched_fill_object_refs(self, load_connection, store_connection, get_references):
        """ Patched version that uses workers if analyzing a large number of oids """

        HEADER = "ref-tables-builder"
        log.info("%s: Looking for updated objects...", HEADER)

        start = time.time()

        stmt = """
        SELECT object_state.zoid FROM object_state
            LEFT JOIN object_refs_added
                ON (object_state.zoid = object_refs_added.zoid)
        WHERE object_refs_added.tid IS NULL
            OR object_refs_added.tid != object_state.tid
        """
        self.runner.run_script_stmt(load_connection.cursor, stmt)
        oids = [ oid for (oid,) in load_connection.cursor ]

        duration = duration_to_pretty_text(time.time()-start)
        log.info("%s: Looking for updated objects took %s. %s objects found",
                 HEADER, duration, len(oids))

        if len(oids) > 0:
            start = time.time()
            log.info("%s: Building reference tables...", HEADER)
            self.workerized_ref_tables_builder(oids, load_connection, store_connection, get_references)
            duration = duration_to_pretty_text(time.time()-start)
            log.info("%s: Build reference tables took %s.", HEADER, duration)


    @monkeypatch('relstorage.adapters.packundo.HistoryFreePackUndo')
    def fill_object_refs(self, load_connection, store_connection, get_references):
        """ Update the object_refs table by analyzing new object states. """
        if "BUILD_TABLES_ONLY" in GLOBAL_OPTIONS and "N_WORKERS" in GLOBAL_OPTIONS:
            # Lets build ref tables with workers
            self.patched_fill_object_refs(load_connection, store_connection, get_references)
        else:
            original(self, load_connection, store_connection, get_references)


    @monkeypatch('relstorage.adapters.packundo.PackUndo')
    def _patched_traverse_graph(self, load_connection, store_connection):
        """Visit the entire object graph to find out what should be kept.

        Sets the pack_object.keep flags.
        """
        log.info("pre_pack: downloading pack_object and object_ref.")

        # Download the list of root objects to keep from pack_object.
        keep_set = set()  # set([oid])
        stmt = """
        SELECT zoid
        FROM pack_object
        WHERE keep = %(TRUE)s
        """
        self.runner.run_script_stmt(load_connection.cursor, stmt)
        for from_oid, in load_connection.cursor:
            keep_set.add(from_oid)

        # Note the Oracle optimizer hints in the following statement; MySQL
        # and PostgreSQL ignore these. Oracle fails to notice that pack_object
        # is now filled and chooses the wrong execution plan, completely
        # killing this query on large RelStorage databases, unless these hints
        # are included.
        stmt = """
        SELECT
            /*+ FULL(object_ref) */
            /*+ FULL(pack_object) */
            object_ref.zoid, object_ref.to_zoid
        FROM object_ref
            JOIN pack_object ON (object_ref.zoid = pack_object.zoid)
        WHERE object_ref.tid >= pack_object.keep_tid
            AND object_ref.zoid IN ({0})
        ORDER BY object_ref.zoid
        """

        # Traverse the object graph.  Add all of the reachable OIDs
        # to keep_set.
        log.info("pre_pack: traversing the object graph "
            "to find reachable objects.")
        parents = set()
        parents.update(keep_set)
        pass_num = 0
        while parents:
            pass_num += 1
            children = set()

            # NOTE(viktors): For a some reasons, mysql don't like ~10^6 rows in
            # IN statement, so let's split a big `parrents` array into a
            # smaller ones.
            # FIXME: It can be a bad idea - to create one more huge (10^6 rows)
            # list from the same set. It would be nice to optimize it.
            parents_list = list(parents)
            limit = 3000
            for step in xrange(0, len(parents_list), limit):
                limited_list = parents_list[step:step+limit]

                # FIXME: Don't use string parameters interpolation (%) to pass
                # variables to a SQL query string
                execute_stmt = stmt.format(', '.join([str(p) for p in limited_list]))
                self.runner.run_script_stmt(load_connection.cursor, execute_stmt)
                # Grouped by object_ref.zoid, store all object_ref.to_zoid in sets
                for from_oid, rows in groupby(load_connection.cursor, itemgetter(0)):
                    children.update(set(row[1] for row in rows))

                log.debug("pre_pack: %d items left", len(parents_list)-step)

            parents = children.difference(keep_set)
            keep_set.update(parents)
            log.debug("pre_pack: found %d more referenced object(s) in "
                "pass %d", len(parents), pass_num)

        keep_list = list(keep_set)
        keep_list.sort()
        log.info("pre_pack: marking objects reachable: %d", len(keep_list))
        batch = []

        def upload_batch():
            oids_str = ','.join(str(oid) for oid in batch)
            del batch[:]
            stmt = """
            UPDATE pack_object SET keep = %%(TRUE)s, visited = %%(TRUE)s
            WHERE zoid IN (%s) 
            """ % oids_str
            self.runner.run_script_stmt(store_connection.cursor, stmt)

        for oid in keep_list:
            batch.append(oid)
            if len(batch) >= 1000:
                upload_batch()
        if batch:
            upload_batch()


    @monkeypatch('relstorage.adapters.packundo.PackUndo')
    def _traverse_graph(self, load_connection, store_connection):
        if "MINIMIZE_MEMORY_USAGE" in GLOBAL_OPTIONS:
            self._patched_traverse_graph(load_connection, store_connection)
        else:
            original(self, load_connection, store_connection)


except ImportError as e:
    raise e
