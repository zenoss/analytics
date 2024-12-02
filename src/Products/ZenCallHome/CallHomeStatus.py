##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017-2022, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import cPickle as pickle
import logging
import time

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

log = logging.getLogger("zen.callhome")


class CallHomeStatus(object):
    REDIS_RECONNECTION_INTERVAL = 3
    STATUS = {"FAILED": -1, "RUNNING": 0, "FINISHED": 1, "PENDING": 2}
    REQUEST_CALLHOME = "Request to CallHome server"
    START_CALLHOME = "CallHome start"
    UPDATE_REPORT = "Update report"
    COLLECT_CALLHOME = "CallHome Collect"
    GPROTOCOL = "GatherProtocol"

    def __init__(self):
        self.redis_url = self.get_redis_url()
        self._redis_client = None
        self._redis_last_connection_attemp = 0

    @staticmethod
    def get_redis_url():
        return getRedisUrl()

    @staticmethod
    def create_redis_client(redis_url):
        client = None
        try:
            client = getRedisClient(redis_url)
            client.config_get()  # test the connection
        except Exception:
            client = None
        return client

    def _connected_to_redis(self):
        """ensures we have a connection to redis"""
        if self._redis_client is None:
            now = time.time()
            if (
                now - self._redis_last_connection_attemp
                > self.REDIS_RECONNECTION_INTERVAL
            ):
                log.debug("Trying to reconnect to redis")
                self._redis_last_connection_attemp = now
                self._redis_client = self.create_redis_client(self.redis_url)
                if self._redis_client:
                    log.debug("Connected to redis")
                else:
                    log.warning("Could not connect to redis")
        return self._redis_client is not None

    def push_to_redis(self, data, k="CallHomeStatus"):
        # Is redis up?
        if not self._connected_to_redis():
            return
        try:
            self._redis_client.set(k, data)
            log.debug("Success pushed to Redis")
        except Exception as e:
            log.warning("Exception trying to push metric to redis: %s", e)
            self._redis_client = None
            return

    def load_from_redis(self, k="CallHomeStatus"):
        # Is redis up?
        if not self._connected_to_redis():
            return
        try:
            log.debug("Success recived data from Redis")
            return self._redis_client.get(k)
        except Exception as e:
            log.warning("Exception trying to recive data from redis: %s", e)
            self._redis_client = None
            return

    def updateStat(self, param, value):
        data = self._pickleLoadRedis()
        data[param] = value
        self.push_to_redis(pickle.dumps(data))

    def getStat(self, param):
        data = self._pickleLoadRedis()
        return data.get(param)

    def getStatUI(self):
        """Returns status informations to UI"""
        data = self._pickleLoadRedis()
        stats = [
            {
                "id": "lastsuccess",
                "description": "Last success",
                "value": data.get("lastSuccess"),
                "type": "date",
            },
            {
                "id": "lastrun",
                "description": "Last run was",
                "value": data.get("startedAt"),
                "type": "date",
            },
            {
                "id": "lastupdtook",
                "description": "Last updating took",
                "value": data.get("lastTook"),
                "type": "duration",
            },
        ]
        err = "No errors"
        for key, val in data.iteritems():
            if isinstance(val, dict):
                if val.get("status") == "FAILED":
                    err = "Failed: " + val.get("error")
        stats.append(
            {
                "id": "updresult",
                "description": "Updating result",
                "value": err,
                "type": "text",
            }
        )
        return stats

    def _pickleLoadRedis(self):
        data = self.load_from_redis()
        return pickle.loads(data) if data is not None else dict()

    def _init(self):
        """Sets empty data for CallHomeStatus before run"""
        data = self._pickleLoadRedis()
        stages = (
            "Request to CallHome server",
            "CallHome start",
            "Update report",
            "CallHome Collect",
            "GatherProtocol",
        )
        for v in stages:
            data[v] = {
                "description": v,
                "status": "PENDING",
                "error": "",
                "stime": "-1",
            }
        log.debug("Setted empty data for CallHomeStatus")
        data = pickle.dumps(data)
        self.push_to_redis(data)

    def stage(self, stage, status="RUNNING", err=""):
        """Usage: obj.stage(Stage name, Stage Status, Stage error message)"""
        try:
            if stage == "Update report" and status == "RUNNING":
                self._init()
                self.updateStat("startedAt", int(time.time()))
            data = self._pickleLoadRedis()
            if not data:
                self._init()
            if stage == "Update report" and status == "FINISHED":
                self.updateStat(
                    "lastTook", int(time.time()) - int(data[stage]["stime"])
                )
            if status == "RUNNING":
                stime = int(time.time())
            else:
                stime = int(time.time()) - int(data[stage]["stime"])
            data[stage] = {
                "description": stage,
                "status": status,
                "error": err,
                "stime": stime,
            }
            self.push_to_redis(pickle.dumps(data))
        except Exception as e:
            log.warning("Failed to update stage in the report: %s", e)

    def status(self):
        stats = list()
        data = dict()
        try:
            data = self._pickleLoadRedis()
        except Exception as e:
            log.warning("Failed to load pickle loads: %s", e)
        for key, val in data.iteritems():
            if isinstance(val, dict):
                if val["status"] != "FINISHED":
                    val["stime"] = -1
                stats.append(val)
        return stats
