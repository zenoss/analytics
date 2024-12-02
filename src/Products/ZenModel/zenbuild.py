##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""zenbuild

Build the zentinel portal object and the dmd database

"""

from __future__ import absolute_import, print_function

import os
import sys

import transaction

from Products.PluggableAuthService import plugins

from Products import ZenModel
from Products.ZenUtils import Security
from Products.ZenUtils.AccountLocker.AccountLocker import (
    setup as account_locker_setup,
)
from Products.ZenUtils.CmdBase import CmdBase
from Products.ZenUtils.Utils import zenPath


class zenbuild(CmdBase):
    sitename = "zport"

    def connect(self):
        zopeconf = zenPath("etc", "zope.conf")
        import Zope2

        Zope2.configure(zopeconf)
        self.app = Zope2.app()

    def buildOptions(self):
        CmdBase.buildOptions(self)
        self.parser.add_option(
            "--xml",
            dest="fromXml",
            action="store_true",
            default=False,
            help="Load data from XML files instead of SQL",
        )
        self.parser.add_option(
            "-s",
            "--evthost",
            default="127.0.0.1",
            help="events database hostname",
        )
        self.parser.add_option(
            "-u",
            "--evtuser",
            default="root",
            help="username used to connect to the events database",
        )
        self.parser.add_option(
            "-p",
            "--evtpass",
            default="",
            help="password used to connect to the events database",
        )
        self.parser.add_option(
            "-d", "--evtdb", default="events", help="name of events database"
        )
        self.parser.add_option(
            "-t",
            "--evtport",
            type="int",
            default=3306,
            help="port used to connect to the events database",
        )
        self.parser.add_option("--smtphost", default="", help="smtp host")
        self.parser.add_option(
            "--smtpport", default=25, type="int", help="smtp port"
        )

        self.parser.add_option(
            "--pagecommand", default="", help="page command"
        )
        # amqp stuff
        self.parser.add_option(
            "--amqphost", default="localhost", help="AMQP Host Location"
        )
        self.parser.add_option(
            "--amqpport", default=5672, type="int", help="AMQP Server Port"
        )
        self.parser.add_option(
            "--amqpvhost", default="/zenoss", help="Default Virtual Host"
        )
        self.parser.add_option(
            "--amqpuser", default="zenoss", help="AMQP User Name"
        )
        self.parser.add_option(
            "--amqppassword", default="zenoss", help="AMQP Password"
        )

        from zope.component import getUtility
        from Products.ZenUtils.ZodbFactory import IZodbFactoryLookup

        connectionFactory = getUtility(IZodbFactoryLookup).get()
        connectionFactory.buildOptions(self.parser)
        self.connectionFactory = connectionFactory

    def zodbConnect(self):
        """
        Used to connect to ZODB (without going through the entire ZOPE
        initialization process. This allows us to get a lightweight
        connection to the database to test to see if the database is already
        initialized.
        """
        from zope.component import getUtility
        from Products.ZenUtils.ZodbFactory import IZodbFactoryLookup

        connectionFactory = getUtility(IZodbFactoryLookup).get()
        self.db, self.storage = connectionFactory.getConnection(
            **self.options.__dict__
        )

    def build(self):
        self._assert_not_already_built()
        if self.options.fromXml:
            self._build_from_xmlfiles()
        else:
            self._build_from_sqlfile()

        # Load reports
        from Products.ZenReports.ReportLoader import ReportLoader

        rl = ReportLoader(noopts=True, app=self.app)
        rl.loadDatabase()

    def _build_from_xmlfiles(self):
        self.connect()

        from Products.ZenModel.ZentinelPortal import (
            manage_addZentinelPortal,
        )

        manage_addZentinelPortal(self.app, self.sitename)
        site = self.app._getOb(self.sitename)

        # build index_html
        if self.app.hasObject("index_html"):
            self.app._delObject("index_html")

        from Products.PythonScripts.PythonScript import (
            manage_addPythonScript,
        )

        manage_addPythonScript(self.app, "index_html")
        newIndexHtml = self.app._getOb("index_html")
        text = 'container.REQUEST.RESPONSE.redirect("/zport/dmd/")\n'
        newIndexHtml.ZPythonScript_edit("", text)

        # build standard_error_message
        if self.app.hasObject("standard_error_message"):
            self.app._delObject("standard_error_message")

        messagefilepath = os.path.join(
            os.path.dirname(__file__), "dtml", "standard_error_message.dtml"
        )
        with open(messagefilepath) as fp:
            text = fp.read()

        import OFS.DTMLMethod

        OFS.DTMLMethod.addDTMLMethod(
            self.app, id="standard_error_message", file=text
        )

        # Convert the acl_users folder at the root to a PAS folder and
        # update the login form to use the Zenoss login form
        Security.replaceACLWithPAS(self.app, deleteBackup=True)
        account_locker_setup(self.app)

        # Add groupManager to zport.acl
        acl = site.acl_users
        if not hasattr(acl, "groupManager"):
            plugins.ZODBGroupManager.addZODBGroupManager(acl, "groupManager")
        acl.groupManager.manage_activateInterfaces(["IGroupsPlugin"])

        trans = transaction.get()
        trans.note("Initial ZentinelPortal load by zenbuild.py")
        trans.commit()
        print("ZentinelPortal loaded at %s" % self.sitename)

        # build dmd
        from Products.ZenModel.DmdBuilder import DmdBuilder

        dmdBuilder = DmdBuilder(
            site,
            self.options.evthost,
            self.options.evtuser,
            self.options.evtpass,
            self.options.evtdb,
            self.options.evtport,
            self.options.smtphost,
            self.options.smtpport,
            self.options.pagecommand,
        )
        dmdBuilder.build()
        transaction.commit()

        # Load XML Data
        from Products.ZenModel.XmlDataLoader import XmlDataLoader

        dl = XmlDataLoader(noopts=True, app=self.app)
        dl.loadDatabase()

    def _build_from_sqlfile(self):
        cmd = "gunzip -c  %s | /opt/zenoss/bin/zendb --usedb=zodb" % (
            os.path.join(
                os.path.dirname(ZenModel.__file__), "data", "zodb.sql.gz"
            )
        )
        returncode = os.system(cmd)  # noqa: S605
        if returncode:
            print(
                "There was a problem creating the database from "
                "the sql dump.",
                file=sys.stderr,
            )
            sys.exit(1)

        # Relstorage may have already loaded items into the cache in the
        # initial connection to the database. We have to expire everything
        # in the cache in order to prevent errors with overlapping
        # transactions from the model which was just imported above.
        if self.options.zodb_cacheservers:
            self.flush_memcached(self.options.zodb_cacheservers.split())

        self.connect()

        # Set all the attributes
        site = getattr(self.app, self.sitename, None)
        site.dmd.smtpHost = self.options.smtphost
        site.dmd.smtpPort = self.options.smtpport
        site.dmd.pageCommand = self.options.pagecommand
        site.dmd.uuid = None
        site.dmd._rq = False
        for evmgr in (site.dmd.ZenEventManager, site.dmd.ZenEventHistory):
            evmgr.username = self.options.evtuser
            evmgr.password = self.options.evtpass
            evmgr.database = self.options.evtdb
            evmgr.host = self.options.evthost
            evmgr.port = self.options.evtport
        transaction.commit()

    def flush_memcached(self, cacheservers):
        import memcache

        mc = memcache.Client(cacheservers, debug=0)
        mc.flush_all()
        mc.disconnect_all()

    def _assert_not_already_built(self):
        self.db = None
        self.storage = None
        try:
            self.zodbConnect()
            conn = self.db.open()
            root = conn.root()
            app = root.get("Application")
            if app and getattr(app, self.sitename, None) is not None:
                print("zport portal object exists; exiting.")
                sys.exit(0)
        except self.connectionFactory.exceptions.OperationalError:
            print("zenbuild: Database does not exist.")
            sys.exit(1)
        finally:
            if conn:
                conn.close()
            if self.db:
                self.db.close()
                self.db = None
            if self.storage:
                self.storage.close()
                self.storage = None


if __name__ == "__main__":
    zb = zenbuild(args=sys.argv)
    zb.build()
