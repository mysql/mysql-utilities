#
# Copyright (c) 2014, 2016 Oracle and/or its affiliates. All rights
# reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#

"""
This file contains the multi-source replication utility. It is used to setup
replication among a slave and multiple masters.
"""

import os
import sys
import time
import logging

from mysql.utilities.exception import FormatError, UtilError, UtilRplError
from mysql.utilities.common.daemon import Daemon
from mysql.utilities.common.format import print_list
from mysql.utilities.common.ip_parser import hostname_is_ip
from mysql.utilities.common.messages import (ERROR_USER_WITHOUT_PRIVILEGES,
                                             ERROR_MIN_SERVER_VERSIONS,
                                             HOST_IP_WARNING)
from mysql.utilities.common.options import parse_user_password
from mysql.utilities.common.server import connect_servers, get_server_state
from mysql.utilities.common.replication import Replication, Master, Slave
from mysql.utilities.common.topology import Topology
from mysql.utilities.common.user import User
from mysql.utilities.common.messages import USER_PASSWORD_FORMAT


_MIN_SERVER_VERSION = (5, 6, 9)
_GTID_LISTS = ["Transactions executed on the servers:",
               "Transactions purged from the servers:",
               "Transactions owned by another server:"]
_GEN_UUID_COLS = ["host", "port", "role", "uuid"]
_GEN_GTID_COLS = ["host", "port", "role", "gtid"]


class ReplicationMultiSource(Daemon):
    """Setup replication among a slave and multiple masters.

    This class implements a multi-source replication using a round-robin
    scheduling for setup replication among all masters and slave.

    This class also implements a POSIX daemon.
    """
    def __init__(self, slave_vals, masters_vals, options):
        """Constructor.

        slave_vals[in]     Slave server connection dictionary.
        master_vals[in]    List of master server connection dictionaries.
        options[in]        Options dictionary.
        """
        pidfile = options.get("pidfile", None)
        if pidfile is None:
            pidfile = "./rplms_daemon.pid"
        super(ReplicationMultiSource, self).__init__(pidfile)

        self.slave_vals = slave_vals
        self.masters_vals = masters_vals
        self.options = options
        self.quiet = self.options.get("quiet", False)
        self.logging = self.options.get("logging", False)
        self.rpl_user = self.options.get("rpl_user", None)
        self.verbosity = options.get("verbosity", 0)
        self.interval = options.get("interval", 15)
        self.switchover_interval = options.get("switchover_interval", 60)
        self.format = self.options.get("format", False)
        self.topology = None
        self.report_values = [
            report.lower() for report in
            self.options["report_values"].split(",")
        ]

        # A sys.stdout copy, that can be used later to turn on/off stdout
        self.stdout_copy = sys.stdout
        self.stdout_devnull = open(os.devnull, "w")

        # Disable stdout when running --daemon with start, stop or restart
        self.daemon = options.get("daemon")
        if self.daemon:
            if self.daemon in ("start", "nodetach"):
                self._report("Starting multi-source replication daemon...",
                             logging.INFO, False)
            elif self.daemon == "stop":
                self._report("Stopping multi-source replication daemon...",
                             logging.INFO, False)
            else:
                self._report("Restarting multi-source replication daemon...",
                             logging.INFO, False)

            # Disable stdout
            sys.stdout = self.stdout_devnull
        else:
            self._report("# Starting multi-source replication...",
                         logging.INFO)
            print("# Press CTRL+C to quit.")

        # Check server versions
        try:
            self._check_server_versions()
        except UtilError as err:
            raise UtilRplError(err.errmsg)

        # Check user privileges
        try:
            self._check_privileges()
        except UtilError as err:
            msg = "Error checking user privileges: {0}".format(err.errmsg)
            self._report(msg, logging.CRITICAL, False)
            raise UtilRplError(err.errmsg)

    @staticmethod
    def _reconnect_server(server, pingtime=3):
        """Tries to reconnect to the server.

        This method tries to reconnect to the server and if connection fails
        after 3 attemps, returns False.

        server[in]      Server instance.
        pingtime[in]    Interval between connection attempts.
        """
        if server and server.is_alive():
            return True
        is_connected = False
        i = 0
        while i < 3:
            try:
                server.connect()
                is_connected = True
                break
            except UtilError:
                pass
            time.sleep(pingtime)
            i += 1
        return is_connected

    def _get_slave(self):
        """Get the slave server instance.

        Returns a Server instance of the slave from the replication topology.
        """
        return self.topology.slaves[0]["instance"]

    def _get_master(self):
        """Get the current master server instance.

        Returns a Server instance of the current master from the replication
        topology.
        """
        return self.topology.master

    def _check_server_versions(self):
        """Checks the server versions.
        """
        if self.verbosity > 0:
            print("# Checking server versions.\n#")

        # Connection dictionary
        conn_dict = {
            "conn_info": None,
            "quiet": True,
            "verbose": self.verbosity > 0,
        }

        # Check masters version
        for master_vals in self.masters_vals:
            conn_dict["conn_info"] = master_vals
            master = Master(conn_dict)
            master.connect()
            if not master.check_version_compat(*_MIN_SERVER_VERSION):
                raise UtilRplError(
                    ERROR_MIN_SERVER_VERSIONS.format(
                        utility="mysqlrplms",
                        min_version=".".join([str(val) for val in
                                              _MIN_SERVER_VERSION]),
                        host=master.host,
                        port=master.port
                    )
                )
            master.disconnect()

        # Check slave version
        conn_dict["conn_info"] = self.slave_vals
        slave = Slave(conn_dict)
        slave.connect()
        if not slave.check_version_compat(*_MIN_SERVER_VERSION):
            raise UtilRplError(
                ERROR_MIN_SERVER_VERSIONS.format(
                    utility="mysqlrplms",
                    min_version=".".join([str(val) for val in
                                          _MIN_SERVER_VERSION]),
                    host=slave.host,
                    port=slave.port
                )
            )
        slave.disconnect()

    def _check_privileges(self):
        """Check required privileges to perform the multi-source replication.

        This method check if the used users for the slave and masters have
        the required privileges to perform the multi-source replication.
        The following privileges are required:
            - on slave: SUPER, SELECT, INSERT, UPDATE, REPLICATION
                        SLAVE AND GRANT OPTION;
            - on the master: SUPER, SELECT, INSERT, UPDATE, REPLICATION SLAVE
                             AND GRANT OPTION.
        An exception is thrown if users doesn't have enough privileges.
        """
        if self.verbosity > 0:
            print("# Checking users privileges for replication.\n#")

        # Connection dictionary
        conn_dict = {
            "conn_info": None,
            "quiet": True,
            "verbose": self.verbosity > 0,
        }

        # Check privileges for master.
        master_priv = [('SUPER',), ('SELECT',), ('INSERT',), ('UPDATE',),
                       ('REPLICATION SLAVE',), ('GRANT OPTION',)]
        master_priv_str = ("SUPER, SELECT, INSERT, UPDATE, REPLICATION SLAVE "
                           "AND GRANT OPTION")

        for master_vals in self.masters_vals:
            conn_dict["conn_info"] = master_vals
            master = Master(conn_dict)
            master.connect()

            user_obj = User(master, "{0}@{1}".format(master.user, master.host))
            for any_priv_tuple in master_priv:
                has_privilege = any(
                    [user_obj.has_privilege('*', '*', priv)
                     for priv in any_priv_tuple]
                )
                if not has_privilege:
                    msg = ERROR_USER_WITHOUT_PRIVILEGES.format(
                        user=master.user, host=master.host, port=master.port,
                        operation='perform replication',
                        req_privileges=master_priv_str
                    )
                    self._report(msg, logging.CRITICAL, False)
                    raise UtilRplError(msg)
            master.disconnect()

        # Check privileges for slave
        slave_priv = [('SUPER',), ('SELECT',), ('INSERT',), ('UPDATE',),
                      ('REPLICATION SLAVE',), ('GRANT OPTION',)]
        slave_priv_str = ("SUPER, SELECT, INSERT, UPDATE, REPLICATION SLAVE "
                          "AND GRANT OPTION")

        conn_dict["conn_info"] = self.slave_vals
        slave = Slave(conn_dict)
        slave.connect()

        user_obj = User(slave, "{0}@{1}".format(slave.user, slave.host))
        for any_priv_tuple in slave_priv:
            has_privilege = any(
                [user_obj.has_privilege('*', '*', priv)
                 for priv in any_priv_tuple]
            )
            if not has_privilege:
                msg = ("User '{0}' on '{1}@{2}' does not have sufficient "
                       "privileges to perform replication (required: {3})."
                       "".format(slave.user, slave.host, slave.port,
                                 slave_priv_str))
                self._report(msg, logging.CRITICAL, False)
                raise UtilRplError(msg)
        slave.disconnect()

    def _check_host_references(self):
        """Check to see if using all host or all IP addresses.

        Returns bool - True = all references are consistent.
        """
        uses_ip = hostname_is_ip(self.topology.master.host)
        slave = self._get_slave()
        host_port = slave.get_master_host_port()
        host = None
        if host_port:
            host = host_port[0]
        if (not host or uses_ip != hostname_is_ip(slave.host) or
                uses_ip != hostname_is_ip(host)):
            return False
        return True

    def _setup_replication(self, master_vals, use_rpl_setup=True):
        """Setup replication among a master and a slave.

        master_vals[in]      Master server connection dictionary.
        use_rpl_setup[in]    Use Replication.setup() if True otherwise use
                             switch_master() on the slave. This is used to
                             control the first pass in the masters round-robin
                             scheduling.
        """
        conn_options = {
            "src_name": "master",
            "dest_name": "slave",
            "version": "5.0.0",
            "unique": True,
        }
        (master, slave,) = connect_servers(master_vals, self.slave_vals,
                                           conn_options)
        rpl_options = self.options.copy()
        rpl_options["verbosity"] = self.verbosity > 0

        # Start from beginning only on the first pass
        if rpl_options.get("from_beginning", False) and not use_rpl_setup:
            rpl_options["from_beginning"] = False

        # Create an instance of the replication object
        rpl = Replication(master, slave, rpl_options)

        if use_rpl_setup:
            # Check server ids
            errors = rpl.check_server_ids()
            for error in errors:
                self._report(error, logging.ERROR, True)

            # Check for server_id uniqueness
            errors = rpl.check_server_uuids()
            for error in errors:
                self._report(error, logging.ERROR, True)

            # Check InnoDB compatibility
            errors = rpl.check_innodb_compatibility(self.options)
            for error in errors:
                self._report(error, logging.ERROR, True)

            # Checking storage engines
            errors = rpl.check_storage_engines(self.options)
            for error in errors:
                self._report(error, logging.ERROR, True)

            # Check master for binary logging
            errors = rpl.check_master_binlog()
            if errors != []:
                raise UtilRplError(errors[0])

            # Setup replication
            if not rpl.setup(self.rpl_user, 10):
                msg = "Cannot setup replication."
                self._report(msg, logging.CRITICAL, False)
                raise UtilRplError(msg)
        else:
            # Parse user and password (support login-paths)
            try:
                (r_user, r_pass,) = parse_user_password(self.rpl_user)
            except FormatError:
                raise UtilError(USER_PASSWORD_FORMAT.format("--rpl-user"))

            # Switch master and start slave
            slave.switch_master(master, r_user, r_pass)
            slave.start({'fetch': False})

        # Disconnect from servers
        master.disconnect()
        slave.disconnect()

    def _switch_master(self, master_vals, use_rpl_setup=True):
        """Switches replication to a new master.

        This method stops replication with the old master if exists and
        starts the replication with a new one.

        master_vals[in]      Master server connection dictionary.
        use_rpl_setup[in]    Used to control the first pass in the masters
                             round-robin scheduling.
        """
        if self.topology:
            # Stop slave
            master = self._get_master()
            if master.is_alive():
                master.disconnect()
            slave = self._get_slave()
            if not slave.is_alive() and not self._reconnect_server(slave):
                msg = "Failed to connect to the slave."
                self._report(msg, logging.CRITICAL, False)
                raise UtilRplError(msg)
            slave.stop()
            slave.disconnect()

        self._report("# Switching to master '{0}:{1}'."
                     "".format(master_vals["host"],
                               master_vals["port"]), logging.INFO, True)

        try:
            # Setup replication on the new master
            self._setup_replication(master_vals, use_rpl_setup)

            # Create a Topology object
            self.topology = Topology(master_vals, [self.slave_vals],
                                     self.options)
        except UtilError as err:
            msg = "Error while switching master: {0}".format(err.errmsg)
            self._report(msg, logging.CRITICAL, False)
            raise UtilRplError(err.errmsg)

        # Only works for GTID_MODE=ON
        if not self.topology.gtid_enabled():
            msg = ("Topology must support global transaction ids and have "
                   "GTID_MODE=ON.")
            self._report(msg, logging.CRITICAL, False)
            raise UtilRplError(msg)

        # Check for mixing IP and hostnames
        if not self._check_host_references():
            print("# WARNING: {0}".format(HOST_IP_WARNING))
            self._report(HOST_IP_WARNING, logging.WARN, False)

    def _report(self, message, level=logging.INFO, print_msg=True):
        """Log message if logging is on.

        This method will log the message presented if the log is turned on.
        Specifically, if options['log_file'] is not None. It will also
        print the message to stdout.

        message[in]      Message to be printed.
        level[in]        Level of message to log. Default = INFO.
        print_msg[in]    If True, print the message to stdout. Default = True.
        """
        # First, print the message.
        if print_msg and not self.quiet:
            print(message)
        # Now log message if logging turned on
        if self.logging:
            logging.log(int(level), message.strip("#").strip(" "))

    def _format_health_data(self):
        """Return health data from topology.

        Returns tuple - (columns, rows).
        """
        if self.topology:
            try:
                health_data = self.topology.get_health()
                current_master = self._get_master()

                # Get data for the remaining masters
                for master_vals in self.masters_vals:
                    # Discard the current master
                    if master_vals["host"] == current_master.host and \
                       master_vals["port"] == current_master.port:
                        continue

                    # Connect to the master
                    conn_dict = {
                        "conn_info": master_vals,
                        "quiet": True,
                        "verbose": self.verbosity > 0,
                    }
                    master = Master(conn_dict)
                    master.connect()

                    # Get master health
                    rpl_health = master.check_rpl_health()

                    master_data = [
                        master.host,
                        master.port,
                        "MASTER",
                        get_server_state(master, master.host, 3,
                                         self.verbosity > 0),
                        master.supports_gtid(),
                        "OK" if rpl_health[0] else ", ".join(rpl_health[1]),
                    ]

                    # Get master status
                    master_status = master.get_status()
                    if len(master_status):
                        master_log, master_log_pos = master_status[0][0:2]
                    else:
                        master_log = None
                        master_log_pos = 0

                    # Show additional details if verbosity is turned on
                    if self.verbosity > 0:
                        master_data.extend([master.get_version(), master_log,
                                            master_log_pos, "", "", "", "", "",
                                            "", "", "", ""])
                    health_data[1].append(master_data)
                return health_data
            except UtilError as err:
                msg = "Cannot get health data: {0}".format(err)
                self._report(msg, logging.ERROR, False)
                raise UtilRplError(msg)
        return ([], [])

    def _format_uuid_data(self):
        """Return the server's uuids.

        Returns tuple - (columns, rows).
        """
        if self.topology:
            try:
                return (_GEN_UUID_COLS, self.topology.get_server_uuids())
            except UtilError as err:
                msg = "Cannot get UUID data: {0}".format(err)
                self._report(msg, logging.ERROR, False)
                raise UtilRplError(msg)
        return ([], [])

    def _format_gtid_data(self):
        """Return the GTID information from the topology.

        Returns tuple - (columns, rows).
        """
        if self.topology:
            try:
                return (_GEN_GTID_COLS, self.topology.get_gtid_data())
            except UtilError as err:
                msg = "Cannot get GTID data: {0}".format(err)
                self._report(msg, logging.ERROR, False)
                raise UtilRplError(msg)
        return ([], [])

    def _log_data(self, title, labels, data, print_format=True):
        """Helper method to log data.

        title[in]     Title to log.
        labels[in]    List of labels.
        data[in]      List of data rows.
        """
        self._report("# {0}".format(title), logging.INFO)
        for row in data:
            msg = ", ".join(
                ["{0}: {1}".format(*col) for col in zip(labels, row)]
            )
            self._report("# {0}".format(msg), logging.INFO, False)
        if print_format:
            print_list(sys.stdout, self.format, labels, data)

    def _log_master_status(self, master):
        """Logs the master information.

        master[in]    Master server instance.

        This method logs the master information from SHOW MASTER STATUS.
        """
        # If no master present, don't print anything.
        if master is None:
            return

        print("#")
        self._report("# {0}:".format("Current Master Information"),
                     logging.INFO)

        try:
            status = master.get_status()[0]
        except UtilError:
            msg = "Cannot get master status"
            self._report(msg, logging.ERROR, False)
            raise UtilRplError(msg)

        cols = ("Binary Log File", "Position", "Binlog_Do_DB",
                "Binlog_Ignore_DB")
        rows = (status[0] or "N/A", status[1] or "N/A", status[2] or "N/A",
                status[3] or "N/A")

        print_list(sys.stdout, self.format, cols, [rows])

        self._report("# {0}".format(
            ", ".join(["{0}: {1}".format(*item) for item in zip(cols, rows)]),
        ), logging.INFO, False)

        # Display gtid executed set
        master_gtids = []
        for gtid in status[4].split("\n"):
            if gtid:
                # Add each GTID to a tuple to match the required format to
                # print the full GRID list correctly.
                master_gtids.append((gtid.strip(","),))

        try:
            if len(master_gtids) > 1:
                gtid_executed = "{0}[...]".format(master_gtids[0][0])
            else:
                gtid_executed = master_gtids[0][0]
        except IndexError:
            gtid_executed = "None"

        self._report("# GTID Executed Set: {0}".format(gtid_executed),
                     logging.INFO)

    def stop_replication(self):
        """Stops multi-source replication.

        Stop the slave if topology is available.
        """
        if self.topology:
            # Get the slave instance
            slave = self._get_slave()
            # If slave is not connected, try to reconnect and stop replication
            if self._reconnect_server(slave):
                slave.stop()
                slave.disconnect()
        if self.daemon:
            self._report("Multi-source replication daemon stopped.",
                         logging.INFO, False)
        else:
            print("")
            self._report("# Multi-source replication stopped.",
                         logging.INFO, True)

    def stop(self):
        """Stops the daemon.

        Stop slave if topology is available and then stop the daemon.
        """
        self.stop_replication()
        super(ReplicationMultiSource, self).stop()

    def run(self):
        """Run the multi-source replication using the round-robin scheduling.

        This method implements the multi-source replication by using time
        slices for each master.
        """
        num_masters = len(self.masters_vals)
        use_rpl_setup = True

        # pylint: disable=R0101
        while True:
            # Round-robin scheduling on the masters
            for idx in range(num_masters):
                # Get the new master values and switch for the next one
                try:
                    master_vals = self.masters_vals[idx]
                    self._switch_master(master_vals, use_rpl_setup)
                except UtilError as err:
                    msg = ("Error while switching master: {0}"
                           "".format(err.errmsg))
                    self._report(msg, logging.CRITICAL, False)
                    raise UtilRplError(msg)

                # Get the new master and slave instances
                master = self._get_master()
                slave = self._get_slave()

                switchover_timeout = time.time() + self.switchover_interval

                while switchover_timeout > time.time():
                    # If servers not connected, try to reconnect
                    if not self._reconnect_server(master):
                        msg = ("Failed to connect to the master '{0}:{1}'."
                               "".format(master_vals["host"],
                                         master_vals["port"]))
                        self._report(msg, logging.CRITICAL, False)
                        raise UtilRplError(msg)

                    if not self._reconnect_server(slave):
                        msg = "Failed to connect to the slave."
                        self._report(msg, logging.CRITICAL, False)
                        raise UtilRplError(msg)

                    # Report
                    self._log_master_status(master)
                    if "health" in self.report_values:
                        (health_labels, health_data,) = \
                            self._format_health_data()
                        if health_data:
                            print("#")
                            self._log_data("Health Status:", health_labels,
                                           health_data)
                    if "gtid" in self.report_values:
                        (gtid_labels, gtid_data,) = self._format_gtid_data()
                        for i, row in enumerate(gtid_data):
                            if row:
                                print("#")
                                self._log_data("GTID Status - {0}"
                                               "".format(_GTID_LISTS[i]),
                                               gtid_labels, row)

                    if "uuid" in self.report_values:
                        (uuid_labels, uuid_data,) = self._format_uuid_data()
                        if uuid_data:
                            print("#")
                            self._log_data("UUID Status:", uuid_labels,
                                           uuid_data)

                    # Disconnect servers
                    master.disconnect()
                    slave.disconnect()

                    # Wait for reporting interval
                    time.sleep(self.interval)

            # Use Replication.setup() only for the first round
            use_rpl_setup = False
