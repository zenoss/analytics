##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import contextlib
import os

import transaction
import ZODB.config

from AccessControl.SecurityManagement import (
    newSecurityManager,
    noSecurityManager,
)
from Products.CMFCore.utils import getToolByName
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.BaseRequest import RequestContainer

from Products.ZenRelations.ZenPropertyManager import setDescriptors
from Products.ZenUtils.path import zenPath
from Products.ZenUtils.Utils import getObjByPath

_zodb_config_template = """\
%import relstorage
<zodb>
  cache-size {zodb-cachesize}

  <relstorage>
    cache-local-mb {zodb-max-cache-mb}
    cache-local-object-max {zodb-cache-max-object-size}
    keep-history false
    <mysql>
      host   {zodb-host}
      port   {zodb-port}
      user   {zodb-user}
      passwd {zodb-password}
      db     {zodb-db}
    </mysql>
  </relstorage>
</zodb>
"""

_default_config_file = os.path.join(zenPath("etc"), "zodb.conf")


class _ZODBConnectionDefaults:
    host = "localhost"
    user = "zenoss"
    password = "zenoss"  # noqa: S105
    db = "zodb"
    port = 3306
    cachesize = 1000
    cache_max_object_size = 1048576
    commit_lock_timeout = 30
    max_cache_mb = 512


def add_zodb_arguments(parser):
    """Add ZODB CLI arguments to `parser`."""
    group = parser.add_argument_group("ZODB Options")
    group.add_argument(
        "--zodb-config-file",
        default=_default_config_file,
        help="ZODB connection config file"
    )
    group.add_argument(
        "--zodb-cachesize",
        default=_ZODBConnectionDefaults.cachesize,
        type=int,
        help="Maximum number of objects kept in the cache",
    )
    group.add_argument(
        "--zodb-host",
        default=_ZODBConnectionDefaults.host,
        help="Hostname of the MySQL server for ZODB",
    )
    group.add_argument(
        "--zodb-port",
        type=int,
        default=_ZODBConnectionDefaults.port,
        help="Port of the MySQL server for ZODB",
    )
    group.add_argument(
        "--zodb-user",
        default=_ZODBConnectionDefaults.user,
        help="User of the MySQL server for ZODB",
    )
    group.add_argument(
        "--zodb-password",
        default=_ZODBConnectionDefaults.password,
        help="Password of the MySQL server for ZODB",
    )
    group.add_argument(
        "--zodb-db",
        default=_ZODBConnectionDefaults.db,
        help="Name of database for MySQL object store",
    )
    group.add_argument(
        "--zodb-cache-max-object-size",
        default=_ZODBConnectionDefaults.cache_max_object_size,
        type=int,
        help="Maximum size of an object stored in the cache (bytes)",
    )
    group.add_argument(
        "--zodb-commit-lock-timeout",
        default=_ZODBConnectionDefaults.commit_lock_timeout,
        type=float,
        help=(
            "Specify the number of seconds a database connection will "
            "wait to acquire a database 'commit' lock before failing."
        ),
    )
    group.add_argument(
        "--zodb-max-cache-mb",
        default=_ZODBConnectionDefaults.max_cache_mb,
        type=int,
        help="Maximum size of the cache (megabytes)"
    )


@contextlib.contextmanager
def zodb(config):
    """
    Context manager managing the connection to ZODB.

    @type config: dict
    """
    with contextlib.closing(getDB(config)) as db:
        with contextlib.closing(db.open()) as session:
            try:
                with dataroot(session) as dmd:
                    yield (db, session, dmd)
            finally:
                transaction.abort()


def getDB(config):
    """
    Returns a connection to the ZODB database.

    If specified, the 'zodb-config-file' key in `config` should name a
    file containing the ZODB connection configuration in the ZConfig format.

    :param config: Contains configuration data for ZODB connection
    :type config: dict
    :rtype: :class:`ZODB.DB.DB`
    """
    configfile = config.get("zodb-config-file")
    if configfile and os.path.isfile(configfile):
        url = "file://%s" % configfile
        return ZODB.config.databaseFromURL(url)
    zodb_config = _getConfigString(config)
    return ZODB.config.databaseFromString(zodb_config)


@contextlib.contextmanager
def dataroot(session):
    """
    Context manager returning the root Zenoss ZODB object from the session.

    The data root is commonly known as the "dmd" object.

    :param session: An active ZODB connection (session) object.
    :type session: :class:`ZODB.Connection.Connection`
    :rtype: :class:`Products.ZenModel.DataRoot.DataRoot`
    """
    root = session.root()
    application = _getContext(root["Application"])
    dataroot = getObjByPath(application, "/zport/dmd")
    _ = _login(dataroot)
    setDescriptors(dataroot)
    try:
        yield dataroot
    finally:
        noSecurityManager()


def _getConfigString(config):
    """
    Returns a ZConfig string to connect to ZODB.

    :rtype: str
    """
    return _zodb_config_template.format(**config)


def _getContext(app):
    resp = HTTPResponse(stdout=None)
    env = {
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "8080",
        "REQUEST_METHOD": "GET",
    }
    req = HTTPRequest(None, env, resp)
    return app.__of__(RequestContainer(REQUEST=req))


_default_user = "zenoss_system"


def _login(context, userid=_default_user):
    """Authenticate user and configure credentials."""
    if userid is None:
        userid = _default_user

    user = _getUser(context, userid)
    newSecurityManager(None, user)
    return user


def _getUser(context, userid):
    root = context.getPhysicalRoot()
    tool = getToolByName(root, "acl_users")

    user = tool.getUserById(userid)
    if user is None:
        # Try a different tool.
        tool = getToolByName(root.zport, "acl_users")
        user = tool.getUserById(userid)

        if user is None:
            user = tool.getUserById(_default_user)

    if not hasattr(user, "aq_base"):
        user = user.__of__(tool)

    return user


__all__ = ("zodb", "getDB", "dataroot")
