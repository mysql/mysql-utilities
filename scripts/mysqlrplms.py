#!/usr/bin/env python
#
# Copyright (c) 2014, 2016 Oracle and/or its affiliates. All rights reserved.
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
This file contains the replicate utility. It is used to establish a
multi-source replication topology.
"""

import os.path
import sys
import logging

from mysql.utilities.common.tools import check_python_version
from mysql.utilities import VERSION_STRING
from mysql.utilities.exception import FormatError, UtilError, UtilRplError
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.messages import (
    PARSE_ERR_OPTS_REQ_GREATER_OR_EQUAL,
    PARSE_ERR_OPTS_REQ,
    MSG_UTILITIES_VERSION
)
from mysql.utilities.common.options import (setup_common_options,
                                            add_verbosity, add_rpl_user,
                                            add_format_option,
                                            add_ssl_options,
                                            get_ssl_dict,
                                            check_password_security)
from mysql.utilities.common.server import check_hostname_alias
from mysql.utilities.common.tools import check_connector_python
from mysql.utilities.common.my_print_defaults import MyDefaultsReader
from mysql.utilities.command.rpl_admin import purge_log
from mysql.utilities.command.setup_rpl import start_ms_replication

# Check Python version compatibility
check_python_version()

# Constants
NAME = "MySQL Utilities - mysqlrplms "
DESCRIPTION = "mysqlrplms - establish multi-source replication"
USAGE = ("%prog --slave=root@localhost:3306 --masters=root@localhost:3310,"
         "root@localhost:3311 --rpl-user=rpl:passwd")
DATE_FORMAT = '%Y-%m-%d %H:%M:%S %p'
EXTENDED_HELP = """
Introduction
------------
The mysqlrplms utility is used to setup round robin multi-source replcation.
This technique can be a solution for aggregating streams of data from multiple
masters for a single slave.

The mysqlrplms utility follows these assumptions:

  - All servers have GTIDs enabled.
  - There are no conflicts between transactions from different sources/masters.
    For example, there are no updates to the same object from multiple masters.
  - Replication is asynchronous.

A round-robin scheduling is used to setup replication among the masters and
slave.

The utility can be run as a daemon on POSIX systems.

  # Basic multi-source replication setup.

  $ mysqlrplms --slave=root:pass@host1:3306 \\
               --masters=root:pass@host2:3306,root:pass@host3:3306

  # Multi-source replication setup using a different report values.

  $ mysqlrplms --slave=root:pass@host1:3306 \\
               --masters=root:pass@host2:3306,root:pass@host3:3306 \\
               --report-values=health,gtid,uuid

  # Start multi-source replication running as a daemon. (POSIX only)

  $ mysqlrplms --slave=root:pass@host1:3306 \\
               --masters=root:pass@host2:3306,root:pass@host3:3306 \\
               --log=rplms_daemon.log --pidfile=rplms_daemon.pid \\
               --daemon=start

  # Restart a multi-source replication running as a daemon.

  $ mysqlrplms --slave=root:pass@host1:3306 \\
               --masters=root:pass@host2:3306,root:pass@host3:3306 \\
               --log=rplms_daemon.log --pidfile=rplms_daemon.pid \\
               --daemon=restart

  # Stop a multi-source replication running as a daemon.

  $ mysqlrplms --slave=root:pass@host1:3306 \\
               --masters=root:pass@host2:3306,root:pass@host3:3306 \\
               --log=rplms_daemon.log --pidfile=rplms_daemon.pid \\
               --daemon=stop


Helpful Hints
-------------
  - The default report value is 'health'.
    This value can be changed with the --report-values option. It can be
    'health', 'gtid' or 'uuid'. Multiple values can be used separated by
    commas.

  - The default output for reporting health is 'grid'.
    This value can be changed with the --format option. It can be 'grid',
    'tab', 'csv' or 'vertical' format.

  - The default interval for reporting health is 15 seconds.
    This value can be changed with the --interval option.

  - The default interval for switching masters is 60 seconds.
    This value can be changed with the --switchover-interval option.

"""

# Check for connector/python
if not check_connector_python():
    sys.exit(1)

if __name__ == '__main__':
    # Setup the command parser
    program = os.path.basename(sys.argv[0]).replace(".py", "")
    parser = setup_common_options(os.path.basename(sys.argv[0]),
                                  DESCRIPTION, USAGE, True, False,
                                  extended_help=EXTENDED_HELP)

    # Setup utility-specific options:

    # Interval for reporting health
    parser.add_option("--interval", "-i", action="store", dest="interval",
                      type="int", default="15", help="interval in seconds for "
                      "reporting health. Default = 15 seconds. "
                      "Lowest value is 5 seconds.")

    # Interval for switching masters
    parser.add_option("--switchover-interval", action="store",
                      dest="switchover_interval",
                      type="int", default="60", help="interval in seconds for "
                      "switching masters. Default = 60 seconds. "
                      "Lowest value is 30 seconds.")

    # Connection information for the sink server
    parser.add_option("--slave", action="store", dest="slave",
                      type="string", default=None,
                      help="connection information for slave server in "
                      "the form: <user>[:<password>]@<host>[:<port>]"
                      "[:<socket>] or <login-path>[:<port>][:<socket>]"
                      " or <config-path>[<[group]>]")

    # Connection information for the masters servers
    parser.add_option("--masters", action="store", dest="masters",
                      type="string", default=None, help="connection "
                      "information for master servers in the form: "
                      "<user>[:<password>]@<host>[:<port>][:<socket>] or "
                      "<login-path>[:<port>][:<socket>]"
                      " or <config-path>[<[group]>]. List multiple master "
                      "in comma-separated list.")

    # Replication user and password
    add_rpl_user(parser)

    # Add start from beginning option
    parser.add_option("-b", "--start-from-beginning", action="store_true",
                      default=False, dest="from_beginning",
                      help="start replication from the first event recorded "
                      "in the binary logging of the masters.")

    # Add report values
    parser.add_option("--report-values", action="store", dest="report_values",
                      type="string", default="health",
                      help="report values used in multi-source replication. "
                      "It can be health, gtid or uuid. Multiple values can be "
                      "used separated by commas. The default is health.")

    # Add output format
    add_format_option(parser, "display the output in either grid (default), "
                      "tab, csv, or vertical format", None)

    # Add option to run as daemon
    parser.add_option("--daemon", action="store", dest="daemon", default=None,
                      help="run on daemon mode. It can be start, stop, "
                      "restart or nodetach.", type="choice",
                      choices=("start", "stop", "restart", "nodetach"))

    # Add pidfile for the daemon option
    parser.add_option("--pidfile", action="store", dest="pidfile",
                      type="string", default=None, help="pidfile for running "
                      "mysqlrplms as a daemon.")

    # Add a log file to use for logging messages
    parser.add_option("--log", action="store", dest="log_file", default=None,
                      type="string", help="specify a log file to use for "
                      "logging messages")

    # Add the maximum age of log entries in days for the logging system
    parser.add_option("--log-age", action="store", dest="log_age", default=7,
                      type="int", help="specify maximum age of log entries in "
                      "days. Entries older than this will be purged on "
                      "startup. Default = 7 days.")

    # Add ssl options
    add_ssl_options(parser)

    # Add verbosity
    add_verbosity(parser)

    # Now we process the rest of the arguments.
    opt, args = parser.parse_args()

    # Check security settings
    check_password_security(opt, args)

    # Check if the values specified for the --report-values option are valid.
    for report in opt.report_values.split(","):
        if report.lower() not in ("health", "gtid", "uuid"):
            parser.error("The value for the option --report-values is not "
                         "valid: '{0}', the values allowed are 'health', "
                         "'gitd' or 'uuid'".format(opt.report_values))

    # Check for errors
    if int(opt.interval) < 5:
        parser.error(PARSE_ERR_OPTS_REQ_GREATER_OR_EQUAL.format(
            opt="--interval", value=5))

    if int(opt.switchover_interval) < 30:
        parser.error(PARSE_ERR_OPTS_REQ_GREATER_OR_EQUAL.format(
            opt="--switchover-interval", value=30))

    # option --slave is required (mandatory)
    if not opt.slave:
        parser.error(PARSE_ERR_OPTS_REQ.format(opt="--slave"))

    # option --masters is required (mandatory)
    if not opt.masters:
        parser.error(PARSE_ERR_OPTS_REQ.format(opt="--masters"))

    # option --rpl-user is required (mandatory)
    if not opt.rpl_user:
        parser.error(PARSE_ERR_OPTS_REQ.format(opt="--rpl-user"))

    config_reader = MyDefaultsReader(opt, False)

    # Parse slave connection values
    try:
        slave_vals = parse_connection(opt.slave, config_reader, opt)
    except FormatError:
        _, err, _ = sys.exc_info()
        parser.error("Slave connection values invalid: {0}.".format(err))
    except UtilError:
        _, err, _ = sys.exc_info()
        parser.error("Slave connection values invalid: {0}."
                     "".format(err.errmsg))

    # Parse masters connection values
    masters_vals = []
    masters = opt.masters.split(",")
    if len(masters) == 1:
        parser.error("At least two masters are required for multi-source "
                     "replication.")

    for master in masters:
        try:
            masters_vals.append(parse_connection(master, config_reader, opt))
        except FormatError as err:
            msg = ("Masters connection values invalid or cannot be parsed: "
                   "{0} ({1})".format(master, err))
            raise UtilRplError(msg)
        except UtilError as err:
            msg = ("Masters connection values invalid or cannot be parsed: "
                   "{0} ({1})".format(master, err.errmsg))
            raise UtilRplError(msg)

    # Check hostname alias
    for master_vals in masters_vals:
        if check_hostname_alias(slave_vals, master_vals):
            parser.error("The master and slave are the same host and port.")

    # Check the daemon options
    if opt.daemon:
        # Check if a POSIX system
        if os.name != "posix":
            parser.error("Running mysqlfailover with --daemon is only "
                         "available for POSIX systems.")

        # Check the presence of --log
        if opt.daemon != "stop" and not opt.log_file:
            parser.error("The option --log is required when using --daemon.")

        # Test pidfile
        if opt.daemon != "nodetach":
            pidfile = opt.pidfile or "./rplms_daemon.pid"
            pidfile = os.path.realpath(os.path.normpath(pidfile))
            if opt.daemon == "start":
                # Test if pidfile exists
                if os.path.exists(pidfile):
                    parser.error("pidfile {0} already exists. The daemon is "
                                 "already running?".format(pidfile))
                # Test if pidfile is writable
                try:
                    with open(pidfile, "w") as f:
                        f.write("{0}\n".format(0))
                    # Delete temporary pidfile
                    os.remove(pidfile)
                except IOError as err:
                    parser.error("Unable to write pidfile: {0}"
                                 "".format(err.strerror))
            else:
                # opt.daemon == stop/restart, test if pidfile is readable
                pid = None
                try:
                    if not os.path.exists(pidfile):
                        parser.error("pidfile {0} does not exist."
                                     "".format(pidfile))
                    with open(pidfile, "r") as f:
                        pid = int(f.read().strip())
                except IOError:
                    pid = None
                except ValueError:
                    pid = None
                # Test pid presence
                if not pid:
                    parser.error("Can not read pid from pidfile.")

    if opt.pidfile and not opt.daemon:
        parser.error("The option --daemon is required when using --pidfile.")

    # Purge log file of old data
    if opt.log_file is not None and not purge_log(opt.log_file, opt.log_age):
        parser.error("Error purging log file.")

    # Setup log file
    try:
        logging.basicConfig(filename=opt.log_file, level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s",
                            datefmt=DATE_FORMAT)
    except IOError:
        _, e, _ = sys.exc_info()
        parser.error("Error opening log file: {0}".format(str(e.args[1])))

    # Create dictionary of options
    options = {
        "verbosity": opt.verbosity,
        "quiet": opt.quiet,
        "interval": opt.interval,
        "switchover_interval": opt.switchover_interval,
        "from_beginning": opt.from_beginning,
        "report_values": opt.report_values,
        'format': opt.format,
        "rpl_user": opt.rpl_user,
        "daemon": opt.daemon,
        "pidfile": opt.pidfile,
        "logging": opt.log_file is not None,
        "log_file": opt.log_file,
    }

    # Add ssl values to options instead of connection.
    options.update(get_ssl_dict(opt))

    # Log MySQL Utilities version string
    if opt.log_file:
        logging.info(MSG_UTILITIES_VERSION.format(utility=program,
                                                  version=VERSION_STRING))
    try:
        start_ms_replication(slave_vals, masters_vals, options)
    except UtilError:
        _, e, _ = sys.exc_info()
        errmsg = e.errmsg.strip(" ")
        if opt.log_file:
            logging.log(logging.CRITICAL, errmsg)
        print("ERROR: {0}".format(errmsg))
        sys.exit(1)

    sys.exit(0)
