##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os

from backports.functools_lru_cache import lru_cache


class _EnviromentVariables(object):
    _CONSUMER_URL = "CONTROLPLANE_CONSUMER_URL"
    _HOST_ID = "CONTROLPLANE_HOST_ID"
    _HOST_IPS = "CONTROLPLANE_HOST_IPS"
    _IMAGE_ID = "SERVICED_SERVICE_IMAGE"
    _INSTANCE_ID = "CONTROLPLANE_INSTANCE_ID"
    _LOG_ADDRESS = "SERVICED_LOG_ADDRESS"
    _MASTER_IP = "SERVICED_MASTER_IP"
    _MAX_RPC_CLIENTS = "SERVICED_MAX_RPC_CLIENTS"
    _MUX_PORT = "SERVICED_MUX_PORT"
    _RPC_PORT = "SERVICED_RPC_PORT"
    _RUN = "CONTROLPLANE"
    _SERVICE_ID = "CONTROLPLANE_SERVICED_ID"
    _SHELL = "SERVICED_IS_SERVICE_SHELL"
    _TENANT_ID = "CONTROLPLANE_TENANT_ID"
    _UI_PORT = "SERVICED_UI_PORT"
    _VERSION = "SERVICED_VERSION"
    _VIRTUAL_ADDRESS_SUBNET = "SERVICED_VIRTUAL_ADDRESS_SUBNET"

    @staticmethod
    def _get(name):
        return os.environ.get(name, "")

    @property
    @lru_cache(maxsize=1)
    def is_serviced(self):
        return self._get(self._RUN) == "1"

    @property
    @lru_cache(maxsize=1)
    def is_serviced_shell(self):
        return self._get(self._SHELL) == "true"

    @property
    @lru_cache(maxsize=1)
    def consumer_url(self):
        return self._get(self._CONSUMER_URL)

    @property
    @lru_cache(maxsize=1)
    def host_id(self):
        return self._get(self._HOST_ID)

    @property
    @lru_cache(maxsize=1)
    def instance_id(self):
        return self._get(self._INSTANCE_ID)

    @property
    @lru_cache(maxsize=1)
    def service_id(self):
        return self._get(self._SERVICE_ID)

    @property
    @lru_cache(maxsize=1)
    def tenant_id(self):
        return self._get(self._TENANT_ID)

    @property
    @lru_cache(maxsize=1)
    def version(self):
        return self._get(self._VERSION)

    @property
    @lru_cache(maxsize=1)
    def image_id(self):
        return self._get(self._IMAGE_ID)

    @property
    @lru_cache(maxsize=1)
    def host_ips(self):
        return tuple(
            ip.strip() for ip in self._get(self._HOST_IPS).split(" ") if ip
        )

    @property
    @lru_cache(maxsize=1)
    def log_address(self):
        return self._get(self._LOG_ADDRESS)

    @property
    @lru_cache(maxsize=1)
    def master_ip(self):
        return self._get(self._MASTER_IP)

    @property
    @lru_cache(maxsize=1)
    def max_rpc_clients(self):
        return self._get(self._MAX_RPC_CLIENTS)

    @property
    @lru_cache(maxsize=1)
    def mux_port(self):
        return self._get(self._MUX_PORT)

    @property
    @lru_cache(maxsize=1)
    def rpc_port(self):
        return self._get(self._RPC_PORT)

    @property
    @lru_cache(maxsize=1)
    def ui_port(self):
        return self._get(self._UI_PORT)

    @property
    @lru_cache(maxsize=1)
    def virtual_address_subnet(self):
        return self._get(self._VIRTUAL_ADDRESS_SUBNET)


configuration = _EnviromentVariables()
