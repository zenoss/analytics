##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
This script removes a number of zodb objects taken as a parameter
(by default 1 million) using workers.
The object to be removed are extracted from the zenossdbpack internal tables,
thus it is critical that the tables are up-to-date.
"""

import argparse
import logging
import multiprocessing
import socket
import sys
import time

from collections import deque

import MySQLdb

from Products.ZenUtils.GlobalConfig import getGlobalConfiguration

DISCLAIMER = """

------------------------------------------------------------------------------
IMPORTANT NOTE: This script should only be run following the following steps:
------------------------------------------------------------------------------
 1) Change pack_object, object_ref, object_refs_added table engines to innodb
 2) Make sure zenossdbpack version is 1.3 or higher (zenossdbpack -v)
 3) Build zenossdbpack internal tables using workers and minimizing mem usage:
        zenossdbpack -e session -tw 8 -m
 4) Build zenossdbpack internal tables again without workers. Do not skip this
    step, it is very important.
    If possible, stop all zenoss components that use zodb to prevent
    POSKeyErrors
        zenossdbpack -e session -t -m
 5) Rename pack tools to prevent accidental call to pack (ie cron jobs etc):
        mv /opt/zenoss/bin/zodbpack /opt/zenoss/bin/_zodbpack
        mv /opt/zenoss/bin/zenossdbpack /opt/zenoss/bin/_zenossdbpack
 6) Run this script as many times as needed until the database reaches desired
    size
        cd /opt/zenoss
        ./bin/zenhackdbpack -w WORKERS -n NUMBER_OF_OBJECTS_TO_REMOVE -i NUMBER_OF_ITERATIONS
Once the database has desired size:
 1) Undo changes done in step 6
 2) Truncate object_ref, object_refs_added, pack_object
 3) Build zenossdbpack internal tables using workers:
        zenossdbpack -e session -tw 8
 4) Run zenossdbpack
        zenossdbpack -e session
 5) Use Zenoss toolbox to ensure zodb is in a good state

Improper use of this script could lead to unrecoverable data loss

For any questions please contact Zenoss Support 
------------------------------------------------------------------------------
"""  # noqa: E501


def set_up_logger():
    log_format = "%(asctime)s [%(name)s] %(levelname)s %(message)s"
    logging.basicConfig(
        filename="/opt/zenoss/log/zenhackdbpack.log",
        filemode="a",
        level=logging.INFO,
        format=log_format,
    )
    # logging.basicConfig(level=logging.INFO, format=log_format)
    # set up logging to console for root logger
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(log_format))
    logging.getLogger("").addHandler(console)


set_up_logger()
log = logging.getLogger("zenoss.hack.zodbpack")


class BCOLORS:
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"


def assert_not_running():
    """Only one instance of this process is allowed to run"""
    global LOCK
    LOCK = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        LOCK.bind("\0zenhackdbpack_lock")
    except socket.error:
        print(
            "\n{0}ERROR: Another instance of this script is already "
            "running. Aborting....{1}\n".format(BCOLORS.RED, BCOLORS.ENDC)
        )
        sys.exit(0)


assert_not_running()


def load_db_config():
    """Load zodb config from global.conf"""
    global_conf = getGlobalConfiguration()
    db_conf = {}
    db_conf["HOST"] = global_conf.get("zodb-host", "127.0.0.1")
    if db_conf["HOST"] == "localhost":
        db_conf["HOST"] = "127.0.0.1"
    db_conf["PORT"] = int(global_conf.get("zodb-port", 13306))
    db_conf["USER"] = global_conf.get("zodb-user", "zenoss")
    db_conf["PASSWORD"] = global_conf.get("zodb-password", "zenoss")
    db_conf["DB"] = global_conf.get("zodb-db", "zodb")
    return db_conf


def get_zodb_connection(db_config):
    return MySQLdb.connect(
        host=db_config.get("HOST"),
        port=db_config.get("PORT"),
        user=db_config.get("USER"),
        passwd=db_config.get("PASSWORD"),
        db=db_config.get("DB"),
    )


def duration_to_pretty_text(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "%dh:%02dm:%02ds" % (h, m, s)


DEFAULT_REPORT_PERIOD = 60


class WorkersDeadException(Exception):
    pass


class HackWorker(multiprocessing.Process):
    def __init__(
        self,
        db_config,
        tasks_queue,
        results_queue,
        report_period=DEFAULT_REPORT_PERIOD,
    ):
        multiprocessing.Process.__init__(self)
        self.tasks_queue = tasks_queue
        self.results_queue = results_queue
        self.conn = get_zodb_connection(db_config)
        self.cursor = self.conn.cursor()
        self.oids_processed = 0
        self.report_period = report_period

    def _do_work(self, task):
        # start = time.time()
        try:
            # Delete from object state
            self.cursor.executemany(
                "DELETE FROM object_state WHERE zoid = %s AND tid = %s", task
            )
            self.cursor.executemany(
                "DELETE FROM pack_object WHERE zoid = %s AND keep_tid = %s",
                task,
            )
            self.conn.commit()
        except MySQLdb.Error as e:
            log.exception("%s: Exception removing objects: %s.", self.name, e)
            self.conn.rollback()
            raise

    def run(self):
        """ """
        last_report = time.time()
        task_dequeued = False
        while True:
            try:
                task = self.tasks_queue.get()
                task_dequeued = True
                if task is None:  # poison pill
                    self.results_queue.put(
                        (self.name, self.oids_processed)
                    )  # report progress before exit
                    break
                else:
                    # do work
                    self._do_work(task)
                    self.oids_processed = self.oids_processed + len(task)
                    now = time.time()
                    if now > last_report + self.report_period:
                        last_report = now
                        self.results_queue.put(
                            (self.name, self.oids_processed)
                        )
            except (KeyboardInterrupt, Exception) as e:
                if isinstance(e, KeyboardInterrupt):
                    log.info("%s: Stopping worker...", self.name)
                else:
                    log.exception("%s: Exception in worker: %s", self.name, e)
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

    def __init__(
        self, db_config, n_oids, n_workers, report_period=DEFAULT_REPORT_PERIOD
    ):
        """ """
        self.db_config = db_config
        self.n_workers = n_workers
        self.n_oids_to_remove = n_oids
        self.queued = 0
        self.report_period = report_period
        try:
            self.conn = get_zodb_connection(self.db_config)
            self.cursor = self.conn.cursor()
        except MySQLdb.Error:
            log.error(
                "Could not connect to database: "
                "Please check config parameters."
            )
            raise

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
        retrieve self.OIDS_PER_SELECT oids grouped in tasks of size
        OIDS_PER_TASK
        @return collections.deque
        """
        get_task_start = time.time()
        log.debug("Retrieving %s objects...", self.n_oids_to_remove)
        sql = (
            "SELECT zoid, keep_tid "
            "FROM pack_object "
            "WHERE {0} keep=0 "
            "ORDER BY zoid {1};"
        )
        zoid_query = ""
        if last_zoid:
            zoid_query = " zoid>{0} AND ".format(last_zoid)
        limit_query = ""
        if limit:
            limit_query = " LIMIT {0} ".format(limit)
        log.debug(sql.format(zoid_query, limit_query))
        self.cursor.execute(sql.format(zoid_query, limit_query))
        oids = self.cursor.fetchall()
        last_zoid = None
        if oids:
            last_zoid = oids[-1][0]
        tasks = deque()
        for step in xrange(0, len(oids), self.OIDS_PER_TASK):
            task = oids[step : step + self.OIDS_PER_TASK]
            tasks.append(task)
        duration = time.time() - get_task_start
        log.debug(
            "Retrieving oids took %s.", duration_to_pretty_text(duration)
        )
        if duration > self.report_period:
            log.warn(
                "Retrieving oids is taking too long (%s).",
                duration_to_pretty_text(duration),
            )
        return (deque(tasks), last_zoid)

    def _log_progress(self, reports, proccessed_last_report):
        processed = sum(reports.values())
        proccessed_since_last_report = processed - proccessed_last_report
        progress = float((processed * 100) / float(self.n_oids_to_remove))
        txt_percentage = "{0:.2f}%".format(progress)
        txt_progress = "Progress: {0}{1}{2} completed".format(
            BCOLORS.GREEN, txt_percentage.rjust(7), BCOLORS.ENDC
        )
        txt_processed = str(processed).rjust(9)
        txt_remaining = str(self.n_oids_to_remove - processed).rjust(9)
        txt_proccessed_since_last_report = str(
            proccessed_since_last_report
        ).rjust(8)
        log.info(
            "%s  | Processed: %s | Remaining: %s | Processed since last report: %s",
            txt_progress,
            txt_processed,
            txt_remaining,
            txt_proccessed_since_last_report,
        )

    def _pack(self):
        """ """
        tasks, last_zoid = self._get_tasks(limit=self.OIDS_PER_SELECT)
        if not tasks:
            log.warning(
                "Nothing to pack. Please make sure zenossdbpack "
                "internal tables are up-to-date."
            )
            return
        log.info(
            "Starting %s workers to pack %s objects...",
            self.n_workers,
            self.n_oids_to_remove,
        )
        # Create work queues
        tasks_queue = multiprocessing.JoinableQueue()
        results_queue = multiprocessing.Queue()
        # Start workers
        workers = []
        for _ in range(self.n_workers):
            worker = HackWorker(self.db_config, tasks_queue, results_queue)
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
                    for _ in xrange(self.n_workers):
                        if not tasks:
                            break
                        task = tasks.popleft()
                        try:
                            if self.queued + len(task) > self.n_oids_to_remove:
                                index = self.n_oids_to_remove - self.queued
                                task = task[:index]
                            tasks_queue.put_nowait(
                                task
                            )  # task is a batch of OIDS_PER_TASK oids
                            self.queued = self.queued + len(task)
                        except multiprocessing.Queue.Full:  # queue is full
                            tasks.appendleft(task)
                            log.info(
                                "Main process: sleeping 60 seconds. "
                                "Tasks queue is full..."
                            )
                            time.sleep(60)

                    if (
                        not tasks and self.queued < self.n_oids_to_remove
                    ):  # Lets get more data
                        tasks, last_zoid = self._get_tasks(
                            limit=self.OIDS_PER_SELECT, last_zoid=last_zoid
                        )

                    if not tasks and not queueing_done:
                        queueing_done = True
                        for _ in workers:
                            tasks_queue.put(None)  # poison pill

                """ Process reports from workers """
                while (
                    not results_queue.empty()
                ):  # Process messages from workers
                    try:
                        result = results_queue.get(block=False)
                        reports[result[0]] = result[
                            1
                        ]  # {worker_id: oids_processed so far}
                    except multiprocessing.Queue.Empty:
                        # No items ready in queue event though
                        # results_queue.empty said otherwise.
                        break

                """ Report status """
                if time.time() > last_report + self.report_period:  # Report
                    self._log_progress(reports, processed)
                    processed = sum(reports.values())
                    last_report = time.time()

                """ Check if workers are done, otherwise take a nap """
                workers = [w for w in workers if w.is_alive()]
                if workers:
                    if queueing_done:
                        log.debug("waiting for workers to finish")
                        time.sleep(1)  # sleep a little, workers are busy
                else:
                    if queueing_done:
                        self._log_progress(reports, processed)
                        break  # we are done!
                    else:  # oh oh, workers are dead
                        raise WorkersDeadException("Workers are dead")

        except (Exception, KeyboardInterrupt) as e:
            if isinstance(e, KeyboardInterrupt):
                log.warn("Hack interrupted.")
            else:
                log.exception("Exception while packing. %s", e)
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

    def pack(self, user_confirmation=True):
        """Remove self.n_oids_to_remove oids from object_state using workers"""
        if user_confirmation:
            log.info("Calculating total number of unreferenced objects...")
            to_remove, to_keep = self.check_pack_object_table()
            log.info(
                "Detected %s%s%s stale objects in your system.",
                BCOLORS.YELLOW,
                to_remove,
                BCOLORS.ENDC,
            )
            # Ask for user confirmation
            u_sure = raw_input(
                "{0}Are you sure to continue? {1} objects will be "
                "removed.{2}\nPress Enter to continue: ".format(
                    BCOLORS.YELLOW, self.n_oids_to_remove, BCOLORS.ENDC
                )
            )
            if u_sure.lower() not in ["", "y", "yes"]:
                return
        pack_start = time.time()
        self._pack()
        duration = duration_to_pretty_text(time.time() - pack_start)
        log.info(
            "%sRemoving %s objects using %s workers took %s%s",
            BCOLORS.GREEN,
            self.queued,
            self.n_workers,
            duration,
            BCOLORS.ENDC,
        )


class ConfigChecker(object):
    def __init__(self, db_config):
        self.db_config = db_config

    def _check_db(self, cursor):
        db_ok = False
        sql = """ SELECT zoid FROM object_state LIMIT 1"""
        try:
            cursor.execute(sql)
            cursor.fetchall()
            db_ok = True
        except Exception:
            pass
        return db_ok

    def _check_pack_table_engine(self, cursor):
        """return true if pack_object engine is innodb"""
        sql = (
            'SELECT LOWER(ENGINE) '
            'FROM information_schema.TABLES '
            'WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME = "pack_object";'
        )
        engine_ok = False
        try:
            cursor.execute(sql)
            if "innodb" in cursor.fetchall()[0]:
                engine_ok = True
        except MySQLdb.Error:
            log.error("Exception retrieving pack_object engine")
        return engine_ok

    def check(self):
        all_good = False
        conn = get_zodb_connection(self.db_config)
        cursor = conn.cursor()

        if not self._check_db(cursor):
            log.error(
                "Error accessing DB: Please check config parameters "
                "in global.conf."
            )
        elif not self._check_pack_table_engine(cursor):
            log.error(
                "zodb.pack_object table engine must be set to 'innodb' "
                "to run this script. Aborting..."
            )
        else:
            all_good = True
        cursor.close()
        conn.close()
        return all_good


def parse_options():
    """Defines command-line options for script"""
    parser = argparse.ArgumentParser(
        version="1.0", description="Hack to remove objects from object_state"
    )
    parser.add_argument(
        "-w",
        "--workers",
        dest="n_workers",
        action="store",
        default=2 * multiprocessing.cpu_count(),
        type=int,
        help="Number of workers used to pack objects.",
    )
    parser.add_argument(
        "-n",
        "--n_objects",
        dest="n_oids",
        action="store",
        default=1000000,
        type=int,
        help="Number of objects to pack",
    )
    parser.add_argument(
        "-i",
        "--n_iterations",
        dest="n_iterations",
        action="store",
        default=1,
        type=int,
        help="Number iterations to run. Only first iteration asks "
        "for user confirmation.",
    )
    return vars(parser.parse_args())


def banner():
    msg = """{0}{1}{2}"""
    print(msg.format(BCOLORS.RED, DISCLAIMER, BCOLORS.ENDC))


def run_hack(db_config, cli_options):
    n_workers = cli_options.get("n_workers")
    n_iterations = cli_options.get("n_iterations")
    n_oids = cli_options.get("n_oids")
    user_confirmation = True

    for i in xrange(n_iterations):
        log_msg = "Starting iteration {0} out of {1}".format(
            i + 1, n_iterations
        )
        log.info("%s%s%s", BCOLORS.BLUE, log_msg, BCOLORS.ENDC)
        hack = ZodbPackHack(db_config, n_oids, n_workers)
        hack.pack(user_confirmation)
        user_confirmation = False  # ask for confirmation only first time
        if i + 1 < n_iterations:
            log.info("Sleeping 30 seconds until next iteration...")
            time.sleep(30)


def main():
    banner()
    db_config = load_db_config()
    cli_options = parse_options()

    if ConfigChecker(db_config).check():
        run_hack(db_config, cli_options)
