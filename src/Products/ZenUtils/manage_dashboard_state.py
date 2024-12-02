#!/usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

description = '''

Save and restore dashboards' states to/from files.

When saving a dashboard's state, the portlets' state for the dashboard owner is saved.

When specifying a subset of dashboards, the full dashboard path must be passed.

Examples:

    # List available dashboards:

        - List available dashboards in Zenoss
            >>> python manage_dashboard_state.py list
                Available Dashboards:
                    /zport/dmd/ZenUsers/dashboards/hola
                    /zport/dmd/ZenUsers/dashboards/default
                    /zport/dmd/ZenUsers/zenoss/dashboards/d1

        - List available dashboards in Zenoss and the users with access to each one
            >>> python manage_dashboard_state.py list-users
                Available Dashboards:
                    /zport/dmd/ZenUsers/dashboards/default
                        admin, zenoss, zenoss_system

        - List available dashboards in a file:
            >>> python manage_dashboard_state.py list -f my_dashboards.pickle
                Available Dashboards in file my_dashboards.pickle:
                    /zport/dmd/ZenUsers/dashboards/hola

    # Save dashboards:

        - Save all dashboards to file
            >>> python manage_dashboard_state.py save
                Saving ALL dashboards...
                    /zport/dmd/ZenUsers/dashboards/default
                    /zport/dmd/ZenUsers/dashboards/hola
                    /zport/dmd/ZenUsers/zenoss/dashboards/d1
                Dashboard's states saved to file ./dashboards_states.20170306-18:17:51.pickle

        - Save all dashboards to file hello.dashboards
            >>> python manage_dashboard_state.py save -f hello.dashboards
                Saving ALL dashboards...
                    /zport/dmd/ZenUsers/dashboards/default
                    /zport/dmd/ZenUsers/dashboards/hola
                    /zport/dmd/ZenUsers/zenoss/dashboards/d1
                Dashboard's states saved to file hello.dashboards

        - Save specific dashboards to file hello.dashboards
            >>> python manage_dashboard_state.py save -d /zport/dmd/ZenUsers/dashboards/default /bla/bla/unexistent_dashboard -f hello.dashboards
                Saving Selected dashboards...
                    /bla/bla/unexistent_dashboard...............................NOT FOUND
                    /zport/dmd/ZenUsers/dashboards/default......................OK
                Dashboard's states saved to file hello.dashboards

    # Restore dashboard's states

        - Restore all user's dashboard's states to the dashboard's onwner's state
            >>> python manage_dashboard_state.py restore
                Setting hola's dashboard state for user (zenoss)
                Setting hola's dashboard state for user (zenoss_system)
                Setting default's dashboard state for user (zenoss)
                Setting default's dashboard state for user (zenoss_system)
                Changes committed

        - Restore all user's "default" dashboard state to a state saved in a file
            >>> python manage_dashboard_state.py restore -d /zport/dmd/ZenUsers/dashboards/default -f dashboards_states.20170306-18:17:16.pickle
                Setting default's dashboard state for user (admin)
                Setting default's dashboard state for user (zenoss)
                Setting default's dashboard state for user (zenoss_system)
                Changes committed

        - Restore admin user "default" dashboard state to a state saved in a file
            >>> python manage_dashboard_state.py restore -d /zport/dmd/ZenUsers/dashboards/default -f dashboards_states.20170306-18:17:16.pickle -u admin
                Setting default's dashboard state for user (admin)
                Changes committed
'''


import argparse
import cPickle as pickle
import json
import logging

from collections import defaultdict
from datetime import datetime
from transaction import commit

from Persistence import PersistentMapping
from Products.ZenModel.ZenossSecurity import ZEN_MANAGE_DMD


def set_up_logger():
    log_format = "%(asctime)s [%(name)s] %(levelname)s %(message)s"
    log_format = "%(message)s"
    logging.basicConfig(level=logging.WARN, format=log_format)
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(log_format))
    log = logging.getLogger('zenoss.DashboardStateManager')
    log.addHandler(console)
    log.setLevel(logging.INFO)
    log.propagate = False
    return log

log = set_up_logger()


class DashboardState(object):
    """ Dashboard data that we want to save/restore for dashboards """
    def __init__(self, dashboard_state="", portlet_states=None):
        self.portlet_states = {} if portlet_states is None else portlet_states
        self.dashboard_state = dashboard_state


class DashboardStateManager(object):

    DEFAULT_PICKLE_FILENAME = './dashboards_states.{}.pickle'

    def __init__(self, dmd):
        self._dmd = dmd
        self._dashboards = {}
        self._dashboard_users = defaultdict(set)
        if dmd:
            self.load_available_dashboards()

    @property
    def dashboards(self):
        return self._dashboards

    @property
    def dashboard_users(self):
        return self._dashboard_users

    def _get_user_groups(self, user):
        group_names = []
        try:
            user_id = user.getId()
            ap = self._dmd.zport.acl_users.manage_getUserRolesAndPermissions(user_id)
            if ZEN_MANAGE_DMD in ap.get('allowed_permissions', {}):
                group_names = user.getAllGroupSettingsNames()
            else:
                group_names = user.getUserGroupSettingsNames()
        except Exception as e:
            log.warn("Could not retrieve user %s's groups: %s", user, e)
        return group_names

    def load_available_dashboards(self):
        self._dashboards = {}
        self._dashboard_users = defaultdict(set)

        if not hasattr(self._dmd.ZenUsers, "dashboards"): # Dashboard ZP not installed
            log.error("Dashboard ZenPack not installed")
            return

        for user in self._dmd.ZenUsers.getAllUserSettings():
            user_dashboards = []
            # 1. Global Dashboards
            user_dashboards.extend(self._dmd.ZenUsers.dashboards())
            # 2. user dashboards
            user_dashboards.extend(user.dashboards())
            # 3. Dashboards defined on user groups or all groups (if I'm manager)
            group_names = self._get_user_groups(user)
            for name in group_names:
                group = self._dmd.ZenUsers.getGroupSettings(name)
                user_dashboards.extend(group.dashboards())
            # Add the user to the dashboards he has access
            for dashboard in user_dashboards:
                d_path = "/".join(dashboard.getPrimaryPath())
                self._dashboard_users[d_path].add(user.id)
                if d_path not in self._dashboards:
                    self._dashboards[d_path] = dashboard

    def get_user_session_data(self, user_name):
        """ Given a user name, it returns his session state data """
        state = {}
        user_settings = getattr(self._dmd.ZenUsers, user_name)
        state_container = getattr(user_settings, '_browser_state', None)
        if state_container and state_container.get('state'):
            state = json.loads(state_container.get('state'))
        return state

    def get_dashboard_state_ids(self, dashboard):
        """ return the ids of the dashboard components we save state for """
        ids = []
        if dashboard.state:
            for col in json.loads(dashboard.state):
                if col.get("items"):
                    for item in col.get("items"):
                        if item.get("config") and item["config"].get("stateId"):
                            ids.append(item["config"]["stateId"])
        return ids

    def save_dashboards(self, filename=None, dashboard_names=None):
        """
        Save the requested dashboards states to a pickle file. If no
        dashboard names are passed, all the dashboard states are taken
        """
        if not filename:
            now = datetime.now().strftime('%Y%m%d-%H:%M:%S')
            filename = self.DEFAULT_PICKLE_FILENAME.format(now)
        dashboards_states = self.get_dashboard_states_from_zodb(dashboard_names)
        with open(filename, "wb") as f:
            pickle.dump(dashboards_states, f)
        saved = set(dashboards_states.keys())
        not_found = set() if not dashboard_names else set(dashboard_names) - saved
        log.debug("Dashboard's states saved to file: %s", filename)
        return filename, saved, not_found

    def get_dashboard_states_from_file(self, filename, dashboard_names=None):
        """ Get the requested dashboards states from file """
        dashboards_states = {}
        try:
            with open(filename, "rb") as f:
                dashboards_states = pickle.load(f)
                if dashboard_names:
                    dashboards_states = { k:v for k,v in dashboards_states.iteritems() if k in dashboard_names }
        except Exception:
            log.error("Error loading dashboard's states from file: %s", filename)
        return dashboards_states

    def get_dashboard_states_from_zodb(self, dashboard_names=None):
        """ Get the requested dashboards states from zodb """
        dashboards_states = {}
        if not dashboard_names:
            dashboard_names = sorted(self.dashboards.keys())
        for d_name in dashboard_names:
            dashboard = self.dashboards.get(d_name)
            if dashboard:
                dashboard_state_ids = self.get_dashboard_state_ids(dashboard)
                owner_state = self.get_user_session_data(dashboard.owner)
                portlet_states = {}
                for s_id in dashboard_state_ids:
                    if s_id in owner_state:
                        portlet_states[s_id] = owner_state[s_id]
                dashboard_state = getattr(dashboard, "state", "")
                dashboards_states[d_name] = DashboardState(dashboard_state, portlet_states)
        return dashboards_states

    def load_dashboard_states(self, filename=None, dashboard_names=None):
        """
        Loads dashboards states from either a file or the current state in zenoss
        """
        if filename:
            dashboards_states = self.get_dashboard_states_from_file(filename, dashboard_names)
        else:
            dashboards_states = self.get_dashboard_states_from_zodb(dashboard_names)
        return dashboards_states

    def _get_dashboard_users(self, dashboard, user_names=None):
        """
        Returns a list of user names that have access to the dashboard.
        If a subset of user names is passed, it will filter them based
        on if they have access to the dashboard or not
        """
        dashboard_path = "/".join(dashboard.getPrimaryPath())
        dashboard_users = self._dashboard_users.get(dashboard_path, [])
        if user_names:
            return set(dashboard_users) & set(user_names)
        else:
            return set(dashboard_users)

    def _save_user_state(self, user_name, user_state):
        """ Saves the state for the passed user to the session database """
        if user_state:
            user_state_json = json.dumps(user_state)
            user_settings = getattr(self._dmd.ZenUsers, user_name)
            state_container = getattr(user_settings, '_browser_state', None)
            if isinstance(state_container, basestring) or state_container is None:
                state_container = PersistentMapping()
                user_settings._browser_state = state_container
            if user_state_json != state_container.get('state', ''):
                state_container['state'] = user_state_json

    def _get_user_state(self, user_name):
        """ Returns the state for the passed user from the session database """
        state = {}
        user_settings = getattr(self._dmd.ZenUsers, user_name)
        state_container = getattr(user_settings, '_browser_state', None)
        if state_container and state_container.get('state'):
            state = json.loads(state_container.get('state'))
        return state

    def restore_dashboards(self, filename, dashboard_names=None, user_names=None):
        dashboard_states = self.load_dashboard_states(filename, dashboard_names)
        # for each dashboard set the passed users state to the one we just loaded
        # if not users were passed, set the state to all users with access to the dashboard
        changed = False
        for d_path, d_state in dashboard_states.iteritems():
            dashboard = self.dashboards.get(d_path)
            if not dashboard:
                log.warn("Dashboard not available: %s", d_path)
            else:
                affected_users = self._get_dashboard_users(dashboard, user_names)
                for user_name in affected_users:
                    if not filename and user_name == dashboard.owner:
                        continue # Do not set onwer state unless we are loading for file
                    log.info("Restoring dashboard %s state for user (%s)", dashboard.id, user_name)
                    user_state = self._get_user_state(user_name)
                    user_state.update(d_state.portlet_states)
                    self._save_user_state(user_name, user_state)
                    changed = True
                # Save the dashboard state
                if getattr(dashboard, 'state', "") != d_state.dashboard_state:
                    setattr(dashboard, 'state', d_state.dashboard_state)
                    changed = True
        if changed:
            commit()
            log.info("Changes committed")


def save_dashboards(options, dashboard_manager):
    dd_msg = "ALL"
    if options.dashboard_names:
        dd_msg = "Selected"
    print "Saving {} dashboards...".format(dd_msg)
    filename, saved, not_found = dashboard_manager.save_dashboards(options.file, options.dashboard_names)
    all_dd = saved | not_found
    for d_name in sorted(all_dd):
        if options.dashboard_names:
            ok_msg = "OK" if d_name in saved else "NOT FOUND"
            print "\t{}{}".format(d_name.ljust(60, "."), ok_msg)
        else:
            print "\t{}".format(d_name)
    print "Dashboard's states saved to file {}".format(filename)


def restore_dashboards(options, dashboard_manager):
    """ Load dashboards states """
    dashboard_manager.restore_dashboards(options.file, options.dashboard_names, options.user_names)


def list_dashboards(options, dashboard_manager, show_users=False):
    """ List dashboard available either in zenoss or in a file """
    if not options.file: # list available dashboards in Zenoss
        print "Available Dashboards:"
        for d_path, users in dashboard_manager.dashboard_users.iteritems():
            print "\t{}".format(d_path)
            if show_users:
                print "\t\t{}".format(", ".join(users))
    else: # list available dashboard states included in the file
        dashboars_states = dashboard_manager.load_dashboard_states(options.file)
        print "Available Dashboards in file {}:".format(options.file)
        for d_path in dashboars_states.keys():
            print " \t{}".format(d_path)


def get_zodb_connection():
    print("Connecting to zodb...")
    from Products.ZenUtils.ZenScriptBase import ZenScriptBase
    return ZenScriptBase(connect=True).dmd


def zodb_connection_needed(options):
    needed = True
    if options.action == 'list' and options.file:
        needed = False
    return needed


def main(options):
    dmd = None if not zodb_connection_needed(options) else get_zodb_connection()
    dashboard_manager = DashboardStateManager(dmd)
    if options.action == 'save':
        save_dashboards(options, dashboard_manager)
    elif options.action == 'restore':
        restore_dashboards(options, dashboard_manager)
    elif options.action == 'list':
        list_dashboards(options, dashboard_manager)
    elif options.action == 'list-users':
        list_dashboards(options, dashboard_manager, show_users=True)


def parse_options():
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("action", type=str, choices=['save','restore', 'list', 'list-users'], help="Action to perform")
    parser.add_argument("-f", "--file", type=str, help="Full path of file to save/restore dashboard states", default="")
    parser.add_argument("-d", "--dashboards", dest="dashboard_names", type=str, help="Names of dashboards to save/load", nargs='*')
    parser.add_argument("-u", "--users", dest="user_names", type=str, help="Names of the users to load the dashboards states", nargs='*')
    return parser.parse_args()


if __name__ == "__main__":
    import sys
    options = parse_options()
    print("{} called with options {}\n".format(sys.argv[0], options))
    sys.argv = sys.argv[:1] # clean up the cli args so ZenScriptBase does not bark
    main(options)

