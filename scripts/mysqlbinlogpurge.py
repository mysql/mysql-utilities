#!/usr/bin/env python
#
# Copyright (c) 2014, 2016, Oracle and/or its affiliates. All rights reserved.
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
This file contains the purge binlog utility. It is used to purge binlog on
demand or by schedule and standalone or on a establish replication topology.
"""

import os
import sys

from mysql.utilities.common.tools import check_python_version
from mysql.utilities.command.binlog_admin import binlog_purge
from mysql.utilities.common.messages import (ERROR_MASTER_IN_SLAVES,
                                             PARSE_ERR_OPT_REQ_OPT,
                                             PARSE_ERR_OPTS_EXCLD,
                                             PARSE_ERR_OPTS_REQ)
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.options import (add_verbosity,
                                            add_discover_slaves_option,
                                            add_master_option,
                                            add_slaves_option,
                                            check_server_lists, get_ssl_dict,
                                            setup_common_options)
from mysql.utilities.common.server import check_hostname_alias
from mysql.utilities.common.tools import check_connector_python
from mysql.utilities.common.topology import parse_topology_connections
from mysql.utilities.exception import UtilError, UtilRplError, FormatError

# Check Python version compatibility
check_python_version()

# Check for connector/python
if not check_connector_python():
    sys.exit(1)

# Constants
NAME = "MySQL Utilities - mysqlbinlogpurge "
DESCRIPTION = "mysqlbinlogpurge - purges unnecessary binary log files"
USAGE = (
    "%prog --master=user:pass@host:port "
    "--slaves=user:pass@host:port,user:pass@host:port"
)
DATE_FORMAT = '%Y-%m-%d %H:%M:%S %p'
EXTENDED_HELP = """
Introduction
------------
The mysqlbinlogpurge utility was designed to purge binary log files in a
replication scenario operating in a safe manner by prohibiting deletion of
binary log files that are open or which are required by a slave (have not
been read by the slave). The utility verifies the latest binary log file that
has been read by all the slave servers to determine the binary log files that
can be deleted.

Note: In order to determine the latest binary log file that has been
replicated by all the slaves, they must be connected to the master at the time
the utility is executed.

The following are examples of use:
  # Purge all the binary log files prior to a specified file for a standalone
  # server.
  $ mysqlbinlogpurge --server=root:pass@host1:3306 \\
                     --binlog=bin-log.001302

  # Display the latest binary log that has been replicated by all specified
  # slaves in a replication scenario.
  $ mysqlbinlogpurge --master=root:pass@host2:3306 \\
                     --slaves=root:pass@host3:3308,root:pass@host3:3309 \\
                     --dry-run
"""

if __name__ == '__main__':
    # Setup the command parser
    parser = setup_common_options(os.path.basename(sys.argv[0]),
                                  DESCRIPTION, USAGE, False, True,
                                  server_default=None,
                                  extended_help=EXTENDED_HELP, add_ssl=True)

    # Do not Purge binlog, instead print info
    parser.add_option("-d", "--dry-run", action="store_true", dest="dry_run",
                      help="run the utility without purge any binary log, "
                      "instead it will print the unused binary log files.")

    # Add Binlog index binlog_name
    parser.add_option("--binlog", action="store",
                      dest="binlog", default=None, type="string",
                      help="Binlog file name to keep (not to purge). All the "
                      "binary log files prior to the specified file will be "
                      "removed.")

    # Add the --discover-slaves-login option.
    add_discover_slaves_option(parser)

    # Add the --master option.
    add_master_option(parser)

    # Add the --slaves option.
    add_slaves_option(parser)

    # Add verbosity
    add_verbosity(parser, quiet=False)

    # Now we process the rest of the arguments.
    opt, args = parser.parse_args()

    server_val = None
    master_val = None
    slaves_val = None

    if opt.server and opt.master:
        parser.error(PARSE_ERR_OPTS_EXCLD.format(opt1="--server",
                                                 opt2="--master"))

    if opt.master is None and opt.slaves:
        parser.error(PARSE_ERR_OPT_REQ_OPT.format(opt="--slaves",
                                                  opts="--master"))

    if opt.master is None and opt.discover:
        parser.error(
            PARSE_ERR_OPT_REQ_OPT.format(opt="--discover-slaves-login",
                                         opts="--master")
        )

    if opt.master and opt.slaves is None and opt.discover is None:
        err_msg = PARSE_ERR_OPT_REQ_OPT.format(
            opt="--master",
            opts="--slaves or --discover-slaves-login",
        )
        parser.error(err_msg)

    # Check mandatory options: --server or --master.
    if not opt.server and not opt.master:
        parser.error(PARSE_ERR_OPTS_REQ.format(
            opt="--server' or '--master"))

    # Check slaves list (master cannot be included in slaves list).
    if opt.master:
        check_server_lists(parser, opt.master, opt.slaves)

        # Parse the master and slaves connection parameters (no candidates).
        try:
            master_val, slaves_val, _ = parse_topology_connections(
                opt, parse_candidates=False
            )
        except UtilRplError:
            _, err, _ = sys.exc_info()
            parser.error("ERROR: {0}\n".format(err.errmsg))
            sys.exit(1)

        # Check host aliases (master cannot be included in slaves list).
        if master_val:
            for slave_val in slaves_val:
                if check_hostname_alias(master_val, slave_val):
                    err = ERROR_MASTER_IN_SLAVES.format(
                        master_host=master_val['host'],
                        master_port=master_val['port'],
                        slaves_candidates="slaves",
                        slave_host=slave_val['host'],
                        slave_port=slave_val['port'],
                    )
                    parser.error(err)

    # Parse source connection values of --server
    if opt.server:
        try:
            ssl_opts = get_ssl_dict(opt)
            server_val = parse_connection(opt.server, None, ssl_opts)
        except FormatError:
            _, err, _ = sys.exc_info()
            parser.error("ERROR: {0}\n".format(err.errmsg))
        except UtilError as err:
            _, err, _ = sys.exc_info()
            parser.error("ERROR: {0}\n".format(err.errmsg))

    # Create dictionary of options
    options = {
        'discover': opt.discover,
        'verbosity': 0 if opt.verbosity is None else opt.verbosity,
        'to_binlog_name': opt.binlog,
        'dry_run': opt.dry_run,
    }

    try:
        binlog_purge(server_val, master_val, slaves_val, options)
    except UtilError:
        _, e, _ = sys.exc_info()
        errmsg = e.errmsg.strip(" ")
        sys.stderr.write("ERROR: {0}\n".format(errmsg))
        sys.exit(1)
    sys.exit(0)
