#!/usr/bin/env python
#
# Copyright (c) 2011, 2016, Oracle and/or its affiliates. All rights reserved.
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
This file contains the disk usage utility for showing the estimated disk
storage of the databases and system files.
"""

import os
import sys
import time

from mysql.utilities.common.tools import check_python_version
from mysql.utilities.exception import FormatError, UtilError
from mysql.utilities.command import diskusage
from mysql.utilities.common.server import connect_servers
from mysql.utilities.common.tools import check_connector_python
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.options import (add_verbosity, add_format_option,
                                            add_no_headers_option,
                                            setup_common_options,
                                            check_password_security)

# Check Python version compatibility
check_python_version()

# Constants
NAME = "MySQL Utilities - mysqldiskusage "
DESCRIPTION = "mysqldiskusage - show disk usage for databases"
USAGE = "%prog --server=user:pass@host:port:socket db1 --all"

# Check for connector/python
if not check_connector_python():
    sys.exit(1)


def print_elapsed_time(start_test):
    """Print the elapsed time to stdout (screen)

    start_test[in]      The starting time of the test
    """
    stop_test = time.time()
    display_time = int((stop_test - start_test) * 100)
    if display_time == 0:
        display_time = 1
    print("Time: %6d\n" % display_time)

if __name__ == '__main__':
    # Setup the command parser and setup server, help
    parser = setup_common_options(os.path.basename(sys.argv[0]),
                                  DESCRIPTION, USAGE, add_ssl=True)

    # Setup utility-specific options:

    # Output format
    add_format_option(parser, "display the output in either grid (default), "
                      "tab, csv, or vertical format", "grid")

    # No header option
    add_no_headers_option(parser, restricted_formats=['grid', 'tab', 'csv'])

    # Binlogs option
    parser.add_option("-b", "--binlog", action="store_true", dest="do_binlog",
                      default=False, help="include binary log usage")

    # Relay logs option
    parser.add_option("-r", "--relaylog", action="store_true",
                      dest="do_relaylog", default=False,
                      help="include relay log usage")

    # Logs option
    parser.add_option("-l", "--logs", action="store_true", dest="do_logs",
                      default=False, help="include general and slow log usage")

    # Innodb option
    parser.add_option("-i", "--innodb", action="store_true", dest="do_innodb",
                      default=False, help="include InnoDB tablespace usage")

    # Show empty databases option
    parser.add_option("-m", "--empty", action="store_true", dest="do_empty",
                      default=False, help="include empty databases")

    # all option
    parser.add_option("-a", "--all", action="store_true", dest="do_all",
                      default=False, help="show all usage including empty "
                      "databases")

    # Add verbosity mode
    add_verbosity(parser, True)

    # Now we process the rest of the arguments.
    opt, args = parser.parse_args()

    # Check security settings
    check_password_security(opt, args)

    # Parse source connection values
    try:
        source_values = parse_connection(opt.server, None, opt)
    except FormatError:
        _, err, _ = sys.exc_info()
        parser.error("Source connection values invalid: %s." % err)
    except UtilError:
        _, err, _ = sys.exc_info()
        parser.error("Source connection values invalid: %s." % err.errmsg)

    try:
        conn_options = {
            'version': "5.1.30",
        }
        servers = connect_servers(source_values, None)
    except UtilError:
        _, e, _ = sys.exc_info()
        parser.error(e.errmsg)

    try:
        res = servers[0].show_server_variable("datadir")
        datadir = res[0][1]
    except UtilError:
        _, e, _ = sys.exc_info()
        parser.error(e.errmsg)

    # Flag for testing if is a remote server
    is_remote = not servers[0].is_alias("localhost")

    # Flag for read access to the datadir
    have_read = True

    if is_remote:
        print("\nWARNING: You are using a remote server and the datadir "
              "cannot be accessed. Some features may be unavailable.\n")
        have_read = False
    elif not os.access(datadir, os.R_OK):
        print("\nWARNING: Your user account does not have read access to the "
              "datadir. Data sizes will be calculated and actual file sizes "
              "may be omitted. Some features may be unavailable.\n")
        have_read = False

    # Set options for database operations.
    options = {
        "format": opt.format,
        "no_headers": opt.no_headers,
        "verbosity": opt.verbosity,
        "debug": opt.verbosity >= 3,
        "have_read": have_read,
        "is_remote": is_remote,
        "do_empty": opt.do_empty,
        "do_all": opt.do_all,
        "quiet": opt.quiet
    }

    # We do database disk usage by default.
    try:
        diskusage.show_database_usage(servers[0], datadir, args, options)
    except UtilError:
        _, e, _ = sys.exc_info()
        print("ERROR: %s" % e.errmsg)
        sys.exit(1)

    # Look for the general and query logs and report
    if opt.do_logs or opt.do_all:
        try:
            diskusage.show_logfile_usage(servers[0], options)
        except UtilError:
            _, e, _ = sys.exc_info()
            print("ERROR: %s" % e.errmsg)
            sys.exit(1)

    # Look for the binary logs and report
    if opt.do_binlog or opt.do_all:
        try:
            options["log_type"] = 'binary log'
            diskusage.show_log_usage(servers[0], datadir, options)
        except UtilError:
            _, e, _ = sys.exc_info()
            print("ERROR: %s" % e.errmsg)
            sys.exit(1)

    # Look for the relay logs and report
    if opt.do_relaylog or opt.do_all:
        try:
            options["log_type"] = 'relay log'
            diskusage.show_log_usage(servers[0], datadir, options)
        except UtilError:
            _, e, _ = sys.exc_info()
            print("ERROR: %s" % e.errmsg)
            sys.exit(1)

    # Look at the inoodb tablespace information are report
    if opt.do_innodb or opt.do_all:
        try:
            diskusage.show_innodb_usage(servers[0], datadir, options)
        except UtilError:
            _, e, _ = sys.exc_info()
            print("ERROR: %s" % e.errmsg)
            sys.exit(1)

    if not opt.quiet:
        print("#...done.")

    sys.exit()
