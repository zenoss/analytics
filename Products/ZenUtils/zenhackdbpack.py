
DISCLAIMER = """

---------------------------------------------------------------------------------------------------------------
                IMPORTANT NOTE: This script should only be run following the following steps:
---------------------------------------------------------------------------------------------------------------
 1) Change pack_object, object_ref, object_refs_added table engines to innodb
 2) Make sure zenossdbpack version is 1.2.1 or higher
 3) Build zenossdbpack internal tables using workers:
        zenossdbpack -e session -t -w 16
 4) Build zenossdbpack internal tables again without workers. Do not skip this step, it is very important.
    If possible, stop all zenoss components that use zodb to prevent POSKeyErrors
        zenossdbpack -e session -t
 5) Rename pack tools to prevent accidental call to pack (ie cron jobs etc):
        mv /opt/zenoss/bin/zodbpack /opt/zenoss/bin/_zodbpack
        mv /opt/zenoss/bin/zenossdbpack /opt/zenoss/bin/_zenossdbpack
 6) Edit this script to modify the db settings
 7) Run this script as many times as needed until the database reaches desired size

Once the database has desired size:
 1) Undo changes done in step 6
 2) Truncate object_ref, object_refs_added, object_pack
 3) Build zenossdbpack internal tables using workers:
        zenossdbpack -e session -t -w 16
 4) Run zenossdbpack
        zenossdbpack -e session
 5) Use Zenoss toolbox to ensure zodb is in a good state

Improper use of this script could lead to unrecoverable data loss

For any questions please contact Zenoss Support 
---------------------------------------------------------------------------------------------------------------

"""
from collections import deque

import argparse
import cPickle
import logging
import multiprocessing
import MySQLdb
import time

def set_up_logger():
    log_format = "%(asctime)s [%(name)s] %(levelname)s %(message)s"
    logging.basicConfig(filename='/opt/zenoss/log/pack_hack.log', filemode='a', level=logging.INFO, format=log_format)
    #logging.basicConfig(level=logging.INFO, format=log_format)
    #set up logging to console for root logger
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(log_format))
    logging.getLogger('').addHandler(console)

set_up_logger()

log = logging.getLogger("zenoss.hack.zodbpack")


""" ---------------------------- """
"""   ZENDS CONFIG PARAMETERS    """
""" ---------------------------- """
HOST='127.0.0.1'
PORT=13306
USER='root'
PASSWORD=''
DB='zodb'
""" ---------------------------- """

DEFAULT_REPORT_PERIOD = 60

class BCOLORS:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'


def get_zodb_connection():
    return MySQLdb.connect(host=HOST, port=PORT, user=USER, passwd=PASSWORD, db=DB)


def duration_to_pretty_text(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "%dh:%02dm:%02ds" % (h, m, s)


class WorkersDeadException(Exception):
    pass


class HackWorker(multiprocessing.Process):

    def __init__(self, tasks_queue, results_queue, report_period=DEFAULT_REPORT_PERIOD):
        multiprocessing.Process.__init__(self)
        self.tasks_queue = tasks_queue
        self.results_queue = results_queue
        self.conn = get_zodb_connection()
        self.cursor = self.conn.cursor()
        self.oids_processed = 0
        self.report_period = report_period
    
    def _do_work(self, task):
        #start = time.time()
        try:
            # Delete from object state
            sql = """ DELETE FROM object_state WHERE zoid = %s AND tid = %s """
            self.cursor.executemany(sql, task)
            sql = """ DELETE FROM pack_object WHERE zoid = %s AND keep_tid = %s """
            self.cursor.executemany(sql, task)
            self.conn.commit()
        except MySQLdb.Error as e:
            log.exception("{0}: Exception removing objects: {1}.".format(self.name, e))
            self.conn.rollback()
            raise e
        #print "{0}: Processing batch took {1} seconds".format(self.name, time.time()-start)

    def run(self):
        """ """
        last_report = time.time()
        task_dequeued = False
        while True:
            try:
                task = self.tasks_queue.get()
                task_dequeued = True
                if task is None: # poison pill
                    self.results_queue.put( (self.name, self.oids_processed) ) # report progress before exit
                    break
                else:
                    # do work
                    self._do_work(task)
                    self.oids_processed = self.oids_processed + len(task)
                    now = time.time()
                    if now > last_report + self.report_period:
                        last_report = now
                        self.results_queue.put( (self.name, self.oids_processed) )
            except (KeyboardInterrupt, Exception) as e:
                if isinstance(e, KeyboardInterrupt):
                    log.info("{0}: Stopping worker...".format(self.name))
                else:
                    log.exception("{0}: Exception in worker: {1}".format(self.name, e))
                self.conn.rollback()
                break
            finally:
                if task_dequeued:
                    self.tasks_queue.task_done()
                    task_dequeued = False
        self.cursor.close()
        self.conn.close()


class ZodbPackHack(object):

    OIDS_PER_TASK = 1000

    OIDS_PER_SELECT = 250000

    def __init__(self, n_oids, n_workers, report_period=DEFAULT_REPORT_PERIOD):
        """ """
        self.n_workers = n_workers
        self.n_oids_to_remove = n_oids
        self.no_questions = False
        self.queued = 0
        self.report_period = report_period
        try:
            self.conn = get_zodb_connection()
            self.cursor = self.conn.cursor()
        except MySQLdb.Error as e:
            log.error("Could not connect to database: Please check config parameters.")
            raise e

    def check_pack_object_table(self):
        sql = """ SELECT count(1) FROM pack_object WHERE keep={0} """
        # oids to pack
        self.cursor.execute(sql.format(0))
        to_remove = self.cursor.fetchone()[0]
        # oids to keep
        self.cursor.execute(sql.format(1))
        to_keep = self.cursor.fetchone()[0]
        return (to_remove, to_keep)

    def _get_tasks(self, limit=None, last_zoid=None):
        """
        retrieve self.OIDS_PER_SELECT oids grouped in tasks of size OIDS_PER_TASK 
        @return collections.deque
        """
        get_task_start = time.time()
        log.debug("Retrieving {0} objects...".format(self.n_oids_to_remove))
        sql = """ SELECT zoid, keep_tid FROM pack_object WHERE {0} keep=0 ORDER BY zoid {1}; """
        zoid_query = ""
        if last_zoid:
            zoid_query = " zoid>{0} AND ".format(last_zoid)
        limit_query = ""
        if limit:
            limit_query = " LIMIT {0} ".format(limit)
        log.debug( sql.format(zoid_query, limit_query) )
        self.cursor.execute(sql.format(zoid_query, limit_query))
        oids = self.cursor.fetchall()
        last_zoid = None
        if oids:
            last_zoid = oids[-1][0]
        tasks = []
        while oids:
            tasks.append(oids[:self.OIDS_PER_TASK])
            oids = oids[self.OIDS_PER_TASK:]
        duration = time.time()-get_task_start
        log.debug("Retrieving oids took {0}.".format(duration_to_pretty_text(duration)))
        if duration > self.report_period:
            log.warn("Retrieving oids is taking too long ({0}).".format(duration_to_pretty_text(duration)))
        return (deque(tasks), last_zoid)

    def _log_progress(self, reports, proccessed_last_report):
        processed = sum(reports.values())
        proccessed_since_last_report = processed - proccessed_last_report
        progress = float((processed*100) / float(self.n_oids_to_remove)) 
        txt_percentage = "{0:.2f}%".format(progress)
        txt_progress = "Progress: {0}{1}{2} completed".format(BCOLORS.GREEN, txt_percentage.rjust(6), BCOLORS.ENDC)
        txt_processed = str(processed).rjust(9)
        txt_remaining = str(self.n_oids_to_remove - processed).rjust(9)
        txt_proccessed_since_last_report = str(proccessed_since_last_report).rjust(8)
        log_text = "{0}  | Processed: {1} | Remaining: {2} | Processed since last report: {3}"
        log.info(log_text.format(txt_progress, txt_processed, txt_remaining, txt_proccessed_since_last_report))

    def _pack(self):
        """ """
        log.info("Starting {0} workers to pack {1} objects...".format(self.n_workers, self.n_oids_to_remove))
        # Create work queues
        tasks_queue = multiprocessing.JoinableQueue()
        results_queue = multiprocessing.Queue()        
        # Start workers
        workers = []
        for i in range(self.n_workers):
            worker = HackWorker(tasks_queue, results_queue)
            worker.start()
            workers.append(worker)
        time.sleep(2)
        try:
            reports = {}
            last_report = 0
            processed = 0
            queueing_done = False            
            tasks, last_zoid = self._get_tasks(limit=self.OIDS_PER_SELECT)
            while True:
                """ Give work to workers """
                if not queueing_done:
                    for _ in xrange(self.n_workers):
                        if not tasks:
                            break
                        task = tasks.popleft()
                        try:
                            if self.queued + len(task) > self.n_oids_to_remove:
                                index = self.n_oids_to_remove - self.queued
                                task = task[:index]
                            tasks_queue.put_nowait(task)  # task is a batch of OIDS_PER_TASK oids
                            self.queued = self.queued + len(task)
                        except multiprocessing.Queue.Full: # queue is full
                            tasks.appendleft(task)
                            log.info("Main process: sleeping 60 seconds. Tasks queue is full...")
                            time.sleep(60)

                    if not tasks and self.queued<self.n_oids_to_remove: # Lets get more data
                        tasks, last_zoid = self._get_tasks(limit=self.OIDS_PER_SELECT, last_zoid=last_zoid)

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

                """ log report """
                if time.time() > last_report + self.report_period:  # Report
                    self._log_progress(reports, processed)
                    processed = sum(reports.values())
                    last_report = time.time()

                """ check if workers are done, otherwise take a nap """
                workers = [ w for w in workers if w.is_alive() ]
                if workers:
                    if queueing_done:
                        log.debug("waiting for workers to finish")
                        time.sleep(1) # sleep a little, workers are busy
                else:
                    if queueing_done:
                        self._log_progress(reports, processed)
                        break # we are done!
                    else: # oh oh, workers are dead
                        raise WorkersDeadException("Workers are dead")

        except (Exception, KeyboardInterrupt) as e:
            if isinstance(e, KeyboardInterrupt):
                log.warn("Hack interrupted.")
            else:
                log.exception("Exception while packing. {0}".format(e))
            while not results_queue.empty():
                results_queue.get(block=False)
            for worker in workers:
                worker.terminate()
                worker.join()
            tasks_queue.close()
            results_queue.close()
        else:
            tasks_queue.close()
            tasks_queue.join()
            results_queue.close()
            for worker in workers:
                worker.join()

    def pack(self):
        """ Remove self.n_oids_to_remove oids from object_state using workers """
        if not self.no_questions:
            log.info("Calculating total number of unreferenced objects...")
            to_remove, to_keep = self.check_pack_object_table()
            log.info("{0}Detected {1} stale objects in your system{2}".format(BCOLORS.YELLOW, to_remove, BCOLORS.ENDC))
            # Ask for user confirmation
            msg = "{0}Are you sure to continue? {1} objects will be removed.{2}\nPress Enter to continue: "
            u_sure = raw_input(msg.format(BCOLORS.YELLOW, self.n_oids_to_remove, BCOLORS.ENDC))
            if u_sure.lower() not in ["", "y", "yes"]:
                return
        pack_start = time.time()
        self._pack()
        duration = duration_to_pretty_text(time.time()-pack_start)
        log.info("{0}Removing {1} objects using {2} workers took {3}{4}".format(BCOLORS.GREEN, self.queued, self.n_workers, duration, BCOLORS.ENDC))

    def check_db(self):
        db_ok = False
        sql = """ SELECT zoid FROM object_state LIMIT 1"""
        try:
            self.cursor.execute(sql)
            self.cursor.fetchall()
            db_ok = True
        except Exception:
            pass
        return db_ok

    def check_pack_table_engine(self):
        """ return true if pack_object engine is innodb """
        sql = """ SELECT LOWER(ENGINE) FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME = "pack_object"; """
        engine_ok = False
        try:
            self.cursor.execute(sql)
            if "innodb" in self.cursor.fetchall()[0]:
                engine_ok = True
        except MySQLdb.Error:
            log.error("Exception retrieving pack_object engine")
        return engine_ok


def parse_options():
    """Defines command-line options for script """
    parser = argparse.ArgumentParser(version="1.0", description="Hack to remove objects from object_state")
    parser.add_argument("-w", "--workers", dest="n_workers", action="store", default=2*multiprocessing.cpu_count(), type=int,
                        help="Number of workers used to pack objects.")
    parser.add_argument("-n", "--n_objects", dest="n_oids", action="store", default=1000000, type=int,
                        help="Number of objects to pack")
    parser.add_argument("-y", "--no_questions", dest="no_questions", action="store_true", default=False,
                        help="Do not ask for user confirmation.")
    return vars(parser.parse_args())


def banner():
    msg = '''{0}{1}{2}'''
    print msg.format(BCOLORS.RED, DISCLAIMER, BCOLORS.ENDC)


def main():
    banner()
    cli_options = parse_options()
    hack = ZodbPackHack(cli_options.get("n_oids"), cli_options.get("n_workers"))
    if hack.check_db():
        if hack.check_pack_table_engine():
            hack.no_questions = cli_options.get("no_questions")
            hack.pack()
        else:
            log.error("zodb.pack_object table engine must be set to 'innodb' to run this script. Aborting...")
    else:
        log.error("Error accessing DB: Please check config parameters in this script.")


if __name__ == "__main__":
    main()


