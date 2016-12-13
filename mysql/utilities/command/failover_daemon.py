#
# Copyright (c) 2013, 2016, Oracle and/or its affiliates. All rights reserved.
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
This file contains the automatic failover daemon. It contains the daemon
mechanism for the automatic failover feature for replication.
"""

import os
import sys
import time
import logging

from mysql.utilities.common.daemon import Daemon
from mysql.utilities.common.tools import ping_host, execute_script
from mysql.utilities.common.messages import HOST_IP_WARNING
from mysql.utilities.exception import UtilRplError


_GTID_LISTS = ["Transactions executed on the servers:",
               "Transactions purged from the servers:",
               "Transactions owned by another server:"]
_GEN_UUID_COLS = ["host", "port", "role", "uuid"]
_GEN_GTID_COLS = ["host", "port", "role", "gtid"]

_DROP_FC_TABLE = "DROP TABLE IF EXISTS mysql.failover_console"
_CREATE_FC_TABLE = ("CREATE TABLE IF NOT EXISTS mysql.failover_console "
                    "(host char(255), port char(10))")
_SELECT_FC_TABLE = ("SELECT * FROM mysql.failover_console WHERE host = '{0}' "
                    "AND port = '{1}'")
_INSERT_FC_TABLE = "INSERT INTO mysql.failover_console VALUES ('{0}', '{1}')"
_DELETE_FC_TABLE = ("DELETE FROM mysql.failover_console WHERE host = '{0}' "
                    "AND port = '{1}'")
_FAILOVER_ERROR = ("{0}Check server for errors and run the mysqlrpladmin "
                   "utility to perform manual failover.")
_FAILOVER_ERRNO = 911
_ERRANT_TNX_ERROR = "Errant transaction(s) found on slave(s)."


class FailoverDaemon(Daemon):
    """Automatic Failover Daemon

    This class implements a POSIX daemon, that logs information about the
    master and the replication health for the topology.
    """
    def __init__(self, rpl, umask=0, chdir="/", stdin=None, stdout=None,
                 stderr=None):
        """Constructor

        rpl[in]     a RplCommands class instance
        umask[in]   posix umask
        chdir[in]   working directory
        stdin[in]   standard input object
        stdout[in]  standard output object
        stderr[in]  standard error object
        """
        pidfile = rpl.options.get("pidfile", None)
        if pidfile is None:
            pidfile = "./failover_daemon.pid"
        super(FailoverDaemon, self).__init__(pidfile)

        self.rpl = rpl
        self.options = rpl.options
        self.interval = int(self.options.get("interval", 15))
        self.pingtime = int(self.options.get("pingtime", 3))
        self.force = self.options.get("force", False)
        self.mode = self.options.get("failover_mode", "auto")
        self.old_mode = None

        # Dictionary that holds the current warning messages
        self.warnings_dic = {}

        # Callback methods for reading data
        self.master = self.rpl.topology.master
        self.get_health_data = self.rpl.topology.get_health
        self.get_gtid_data = self.rpl.topology.get_gtid_data
        self.get_uuid_data = self.rpl.topology.get_server_uuids
        self.list_data = None

        self.master_gtids = []
        self.report_values = [
            report.lower() for report in
            self.options["report_values"].split(",")
        ]

    def _report(self, message, level=logging.INFO, print_msg=True):
        """Log message if logging is on.

        This method will log the message presented if the log is turned on.
        Specifically, if options['log_file'] is not None. It will also
        print the message to stdout.

        message[in]    message to be printed
        level[in]      level of message to log. Default = INFO
        print_msg[in]  if True, print the message to stdout. Default = True
        """
        # First, print the message.
        if print_msg and not self.rpl.quiet:
            print(message)
        # Now log message if logging turned on
        if self.rpl.logging:
            logging.log(int(level), message.strip("#").strip(" "))

    def _print_warnings(self):
        """Print current warning messages.

        This method displays current warning messages if they exist.
        """
        # Only do something if warnings exist.
        if self.warnings_dic:
            for msg in self.warnings_dic.itervalues():
                print("# WARNING: {0}".format(msg))

    def _format_health_data(self):
        """Return health data from topology.

        Returns tuple - (columns, rows)
        """
        if self.get_health_data is not None:
            try:
                return self.get_health_data()
            except Exception as err:
                msg = "Cannot get health data: {0}".format(err)
                self._report(msg, logging.ERROR)
                raise UtilRplError(msg)
        return ([], [])

    def _format_uuid_data(self):
        """Return the server's uuids.

        Returns tuple - (columns, rows)
        """
        if self.get_uuid_data is not None:
            try:
                return (_GEN_UUID_COLS, self.get_uuid_data())
            except Exception as err:
                msg = "Cannot get UUID data: {0}".format(err)
                self._report(msg, logging.ERROR)
                raise UtilRplError(msg)
        return ([], [])

    def _format_gtid_data(self):
        """Return the GTID information from the topology.

        Returns tuple - (columns, rows)
        """
        if self.get_gtid_data is not None:
            try:
                return (_GEN_GTID_COLS, self.get_gtid_data())
            except Exception as err:
                msg = "Cannot get GTID data: {0}".format(err)
                self._report(msg, logging.ERROR)
                raise UtilRplError(msg)
        return ([], [])

    def _log_master_status(self):
        """Logs the master information

        This method logs the master information from SHOW MASTER STATUS.
        """
        # If no master present, don't print anything.
        if self.master is None:
            return

        logging.info("Master Information")

        try:
            status = self.master.get_status()[0]
        except:
            msg = "Cannot get master status"
            self._report(msg, logging.ERROR)
            raise UtilRplError(msg)

        cols = ("Binary Log File", "Position", "Binlog_Do_DB",
                "Binlog_Ignore_DB")
        rows = (status[0] or "N/A", status[1] or "N/A", status[2] or "N/A",
                status[3] or "N/A")

        logging.info(
            ", ".join(["{0}: {1}".format(*item) for item in zip(cols, rows)])
        )

        # Display gtid executed set
        self.master_gtids = []
        for gtid in status[4].split("\n"):
            if gtid:
                # Add each GTID to a tuple to match the required format to
                # print the full GRID list correctly.
                self.master_gtids.append((gtid.strip(","),))

        try:
            if len(self.master_gtids) > 1:
                gtid_executed = "{0}[...]".format(self.master_gtids[0][0])
            else:
                gtid_executed = self.master_gtids[0][0]
        except IndexError:
            gtid_executed = "None"

        logging.info("GTID Executed Set: {0}".format(gtid_executed))

    @staticmethod
    def _log_data(title, labels, data):
        """Helper method to log data.

        title[in]     title to log
        labels[in]    list of labels
        data[in]      list of data rows
        """
        logging.info(title)
        for row in data:
            msg = ", ".join(
                ["{0}: {1}".format(*col) for col in zip(labels, row)]
            )
            logging.info(msg)

    def _reconnect_master(self, pingtime=3):
        """Tries to reconnect to the master

        This method tries to reconnect to the master and if connection fails
        after 3 attempts, returns False.
        """
        if self.master and self.master.is_alive():
            return True
        is_connected = False
        i = 0
        while i < 3:
            try:
                self.master.connect()
                is_connected = True
                break
            except:
                pass
            time.sleep(pingtime)
            i += 1
        return is_connected

    def add_warning(self, warning_key, warning_msg):
        """Add a warning message to the current dictionary of warnings.

        warning_key[in]    key associated with the warning message to add.
        warning_msg[in]    warning message to add to the current dictionary of
                           warnings.
        """
        self.warnings_dic[warning_key] = warning_msg

    def del_warning(self, warning_key):
        """Remove a warning message from the current dictionary of warnings.

        warning_key[in]    key associated with the warning message to remove.
        """
        if warning_key in self.warnings_dic:
            del self.warnings_dic[warning_key]

    def check_instance(self):
        """Check registration of the console

        This method unregisters existing instances from slaves and attempts
        to register the instance on the master. If there is already an
        instance on the master, failover mode will be changed to 'fail'.
        """
        # Unregister existing instances from slaves
        self._report("Unregistering existing instances from slaves.",
                     logging.INFO, False)
        self.unregister_slaves(self.rpl.topology)

        # Register instance
        self._report("Registering instance on master.", logging.INFO, False)
        old_mode = self.mode
        failover_mode = self.register_instance(self.force)
        if failover_mode != old_mode:
            # Turn on sys.stdout
            sys.stdout = self.rpl.stdout_copy

            msg = ("Multiple instances of failover daemon found for master "
                   "{0}:{1}.".format(self.master.host, self.master.port))
            self._report(msg, logging.WARN)
            print("If this is an error, restart the daemon with --force.")
            print("Failover mode changed to 'FAIL' for this instance.")
            print("Daemon will start in 10 seconds.")
            sys.stdout.flush()
            i = 0
            while i < 9:
                time.sleep(1)
                sys.stdout.write(".")
                sys.stdout.flush()
                i += 1
            print("starting Daemon.")
            # Turn off sys.stdout
            sys.stdout = self.rpl.stdout_devnull
            time.sleep(1)

    def register_instance(self, clear=False, register=True):
        """Register the daemon as running on the master.

        This method will attempt to register the daemon as running against
        the master for failover modes auto or elect. If another daemon is
        already registered, this instance becomes blocked resulting in the
        mode change to 'fail' and failover will not occur when this instance
        of the daemon detects failover.

        clear[in]      if True, clear the sentinel database entries on the
                       master. Default is False.
        register[in]   if True, register the daemon on the master. If False,
                       unregister the daemon on the master. Default is True.

        Returns string - new mode if changed
        """
        # We cannot check disconnected masters and do not need to check if
        # we are doing a simple fail mode.
        if self.master is None or self.mode == "fail":
            return self.mode

        # Turn binary log off first
        self.master.toggle_binlog("DISABLE")

        host_port = (self.master.host, self.master.port)
        # Drop the table if specified
        if clear:
            self.master.exec_query(_DROP_FC_TABLE)

        # Register the daemon
        if register:
            res = self.master.exec_query(_CREATE_FC_TABLE)
            res = self.master.exec_query(_SELECT_FC_TABLE.format(*host_port))
            # COMMIT to close session before enabling binlog.
            self.master.commit()
            if res != []:
                # Someone beat us there. Drat.
                self.old_mode = self.mode
                self.mode = "fail"
            else:
                # We're first! Yippee.
                res = self.master.exec_query(
                    _INSERT_FC_TABLE.format(*host_port))
        # Unregister the daemon if our mode was changed
        elif self.old_mode != self.mode:
            res = self.master.exec_query(_DELETE_FC_TABLE.format(*host_port))

        # Turn binary log on
        self.master.toggle_binlog("ENABLE")

        return self.mode

    def unregister_slaves(self, topology):
        """Unregister the daemon as running on the slaves.

        This method will unregister the daemon that was previously registered
        on the slaves, for failover modes auto or elect.
        """
        if self.master is None or self.mode == "fail":
            return

        for slave_dict in topology.slaves:
            # Skip unreachable/not connected slaves.
            slave_instance = slave_dict["instance"]
            if slave_instance and slave_instance.is_alive():
                # Turn binary log off first
                slave_instance.toggle_binlog("DISABLE")
                # Drop failover instance registration table.
                slave_instance.exec_query(_DROP_FC_TABLE)
                # Turn binary log on
                slave_instance.toggle_binlog("ENABLE")

    def run(self):
        """Run automatic failover.

        This method implements the automatic failover facility. It the existing
        failover() method of the RplCommands class to conduct failover.

        When the master goes down, the method can perform one of three actions:

        1) failover to list of candidates first then slaves
        2) failover to list of candidates only
        3) fail

        rpl[in]        instance of the RplCommands class
        interval[in]   time in seconds to wait to check status of servers

        Returns bool - True = success, raises exception on error
        """
        failover_mode = self.mode
        pingtime = self.options.get("pingtime", 3)
        exec_fail = self.options.get("exec_fail", None)
        post_fail = self.options.get("post_fail", None)
        pedantic = self.options.get("pedantic", False)

        # Only works for GTID_MODE=ON
        if not self.rpl.topology.gtid_enabled():
            msg = ("Topology must support global transaction ids and have "
                   "GTID_MODE=ON.")
            self._report(msg, logging.CRITICAL)
            raise UtilRplError(msg)

        # Require --master-info-repository=TABLE for all slaves
        if not self.rpl.topology.check_master_info_type("TABLE"):
            msg = ("Failover requires --master-info-repository=TABLE for "
                   "all slaves.")
            self._report(msg, logging.ERROR, False)
            raise UtilRplError(msg)

        # Check for mixing IP and hostnames
        if not self.rpl.check_host_references():
            print("# WARNING: {0}".format(HOST_IP_WARNING))
            self._report(HOST_IP_WARNING, logging.WARN, False)
            print("#\n# Failover daemon will start in 10 seconds.")
            time.sleep(10)

        # Test failover script. If it doesn't exist, fail.
        no_exec_fail_msg = ("Failover check script cannot be found. Please "
                            "check the path and filename for accuracy and "
                            "restart the failover daemon.")
        if exec_fail is not None and not os.path.exists(exec_fail):
            self._report(no_exec_fail_msg, logging.CRITICAL, False)
            raise UtilRplError(no_exec_fail_msg)

        # Check existence of errant transactions on slaves
        errant_tnx = self.rpl.topology.find_errant_transactions()
        if errant_tnx:
            print("# WARNING: {0}".format(_ERRANT_TNX_ERROR))
            self._report(_ERRANT_TNX_ERROR, logging.WARN, False)
            for host, port, tnx_set in errant_tnx:
                errant_msg = (" - For slave '{0}@{1}': "
                              "{2}".format(host, port, ", ".join(tnx_set)))
                print("# {0}".format(errant_msg))
                self._report(errant_msg, logging.WARN, False)
            # Raise an exception (to stop) if pedantic mode is ON
            if pedantic:
                msg = ("{0} Note: If you want to ignore this issue, please do "
                       "not use the --pedantic option."
                       "".format(_ERRANT_TNX_ERROR))
                self._report(msg, logging.CRITICAL)
                raise UtilRplError(msg)

        self._report("Failover daemon started.", logging.INFO, False)
        self._report("Failover mode = {0}.".format(failover_mode),
                     logging.INFO, False)

        # Main loop - loop and fire on interval.
        done = False
        first_pass = True
        failover = False

        while not done:
            # Use try block in case master class has gone away.
            try:
                old_host = self.rpl.master.host
                old_port = self.rpl.master.port
            except:
                old_host = "UNKNOWN"
                old_port = "UNKNOWN"

            # If a failover script is provided, check it else check master
            # using connectivity checks.
            if exec_fail is not None:
                # Execute failover check script
                if not os.path.exists(exec_fail):
                    self._report(no_exec_fail_msg, logging.CRITICAL, False)
                    raise UtilRplError(no_exec_fail_msg)
                else:
                    self._report("# Spawning external script for failover "
                                 "checking.")
                    res = execute_script(exec_fail, None,
                                         [old_host, old_port],
                                         self.rpl.verbose)
                    if res == 0:
                        self._report("# Failover check script completed "
                                     "Ok. Failover averted.")
                    else:
                        self._report("# Failover check script failed. "
                                     "Failover initiated", logging.WARN)
                        failover = True
            else:
                # Check the master. If not alive, wait for pingtime seconds
                # and try again.
                if self.rpl.topology.master is not None and \
                   not self.rpl.topology.master.is_alive():
                    msg = ("Master may be down. Waiting for {0} seconds."
                           "".format(pingtime))
                    self._report(msg, logging.INFO, False)
                    time.sleep(pingtime)
                    try:
                        self.rpl.topology.master.connect()
                    except:
                        pass

                # Check the master again. If no connection or lost connection,
                # try ping. This performs the timeout threshold for detecting
                # a down master. If still not alive, try to reconnect and if
                # connection fails after 3 attempts, failover.
                if self.rpl.topology.master is None or \
                   not ping_host(self.rpl.topology.master.host, pingtime) or \
                   not self.rpl.topology.master.is_alive():
                    failover = True
                    if self._reconnect_master(self.pingtime):
                        failover = False  # Master is now connected again
                    if failover:
                        self._report("Failed to reconnect to the master after "
                                     "3 attempts.", logging.INFO)

            if failover:
                self._report("Master is confirmed to be down or "
                             "unreachable.", logging.CRITICAL, False)
                try:
                    self.rpl.topology.master.disconnect()
                except:
                    pass

                if failover_mode == "auto":
                    self._report("Failover starting in 'auto' mode...")
                    res = self.rpl.topology.failover(self.rpl.candidates,
                                                     False)
                elif failover_mode == "elect":
                    self._report("Failover starting in 'elect' mode...")
                    res = self.rpl.topology.failover(self.rpl.candidates, True)
                else:
                    msg = _FAILOVER_ERROR.format("Master has failed and "
                                                 "automatic failover is "
                                                 "not enabled. ")
                    self._report(msg, logging.CRITICAL, False)
                    # Execute post failover script
                    try:
                        self.rpl.topology.run_script(post_fail, False,
                                                     [old_host, old_port])
                    except Exception as err:  # pylint: disable=W0703
                        self._report("# Post fail script failed! {0}"
                                     "".format(err), level=logging.ERROR)
                    raise UtilRplError(msg, _FAILOVER_ERRNO)
                if not res:
                    msg = _FAILOVER_ERROR.format("An error was encountered "
                                                 "during failover. ")
                    self._report(msg, logging.CRITICAL, False)
                    # Execute post failover script
                    try:
                        self.rpl.topology.run_script(post_fail, False,
                                                     [old_host, old_port])
                    except Exception as err:  # pylint: disable=W0703
                        self._report("# Post fail script failed! {0}"
                                     "".format(err), level=logging.ERROR)
                    raise UtilRplError(msg)
                self.rpl.master = self.rpl.topology.master
                self.master = self.rpl.master
                self.rpl.topology.remove_discovered_slaves()
                self.rpl.topology.discover_slaves()
                self.list_data = None
                print("\nFailover daemon will restart in 5 seconds.")
                time.sleep(5)
                failover = False
                # Execute post failover script
                try:
                    self.rpl.topology.run_script(post_fail, False,
                                                 [old_host, old_port,
                                                  self.rpl.master.host,
                                                  self.rpl.master.port])
                except Exception as err:  # pylint: disable=W0703
                    self._report("# Post fail script failed! {0}"
                                 "".format(err), level=logging.ERROR)

                # Unregister existing instances from slaves
                self._report("Unregistering existing instances from slaves.",
                             logging.INFO, False)
                self.unregister_slaves(self.rpl.topology)

                # Register instance on the new master
                msg = ("Registering instance on new master "
                       "{0}:{1}.").format(self.master.host, self.master.port)
                self._report(msg, logging.INFO, False)

                failover_mode = self.register_instance()

            # discover slaves if option was specified at startup
            elif (self.options.get("discover", None) is not None and
                  not first_pass):
                # Force refresh of health list if new slaves found
                if self.rpl.topology.discover_slaves():
                    self.list_data = None

            # Check existence of errant transactions on slaves
            errant_tnx = self.rpl.topology.find_errant_transactions()
            if errant_tnx:
                if pedantic:
                    print("# WARNING: {0}".format(_ERRANT_TNX_ERROR))
                    self._report(_ERRANT_TNX_ERROR, logging.WARN, False)
                    for host, port, tnx_set in errant_tnx:
                        errant_msg = (" - For slave '{0}@{1}': "
                                      "{2}".format(host, port,
                                                   ", ".join(tnx_set)))
                        print("# {0}".format(errant_msg))
                        self._report(errant_msg, logging.WARN, False)

                    # Raise an exception (to stop) if pedantic mode is ON
                    raise UtilRplError("{0} Note: If you want to ignore this "
                                       "issue, please do not use the "
                                       "--pedantic "
                                       "option.".format(_ERRANT_TNX_ERROR))
                else:
                    if self.rpl.logging:
                        warn_msg = ("{0} Check log for more "
                                    "details.".format(_ERRANT_TNX_ERROR))
                    else:
                        warn_msg = _ERRANT_TNX_ERROR
                    self.add_warning("errant_tnx", warn_msg)
                    self._report(_ERRANT_TNX_ERROR, logging.WARN, False)
                    for host, port, tnx_set in errant_tnx:
                        errant_msg = (" - For slave '{0}@{1}': "
                                      "{2}".format(host, port,
                                                   ", ".join(tnx_set)))
                        self._report(errant_msg, logging.WARN, False)
            else:
                self.del_warning("errant_tnx")

            if self.master and self.master.is_alive():
                # Log status
                self._print_warnings()
                self._log_master_status()

                self.list_data = []
                if "health" in self.report_values:
                    (health_labels, health_data) = self._format_health_data()
                    if health_data:
                        self._log_data("Health Status:", health_labels,
                                       health_data)
                if "gtid" in self.report_values:
                    (gtid_labels, gtid_data) = self._format_gtid_data()
                    for i, v in enumerate(gtid_data):
                        if v:
                            self._log_data("GTID Status - {0}"
                                           "".format(_GTID_LISTS[i]),
                                           gtid_labels, v)
                if "uuid" in self.report_values:
                    (uuid_labels, uuid_data) = self._format_uuid_data()
                    if uuid_data:
                        self._log_data("UUID Status:", uuid_labels, uuid_data)

            # Disconnect the master while waiting for the interval to expire
            self.master.disconnect()

            # Wait for the interval to expire
            time.sleep(self.interval)

            # Reconnect to the master
            self._reconnect_master(self.pingtime)

            first_pass = False

        return True

    def start(self, detach_process=True):
        """Starts the daemon.

        Runs the automatic failover, it will start the daemon if detach_process
        is True.
        """
        # Check privileges
        self._report("# Checking privileges.")
        errors = self.rpl.topology.check_privileges(self.mode != "fail")
        if len(errors):
            msg = ("User {0} on {1} does not have sufficient privileges to "
                   "execute the {2} command.")
            for error in errors:
                self._report(msg.format(error[0], error[1], "failover"),
                             logging.CRITICAL)
            raise UtilRplError("Not enough privileges to execute command.")

        # Check failover instances running
        self.check_instance()

        # Start the daemon
        return super(FailoverDaemon, self).start(detach_process)

    def cleanup(self):
        """Controlled cleanup for the daemon.

        It will unregister the failover_console table.
        """
        # if master is not alive, try connecting to it
        if not self.master.is_alive():
            self.master.connect()
        try:
            self.master.exec_query(_DELETE_FC_TABLE.format(self.master.host,
                                                           self.master.port))
            self._report("Master entry in the failover_console"
                         " table was deleted.", logging.INFO, False)
        except:
            pass
