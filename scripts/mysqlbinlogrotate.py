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
This file contains the rotate binlog utility. It is used to rotate binary logs.
"""

import os
import sys

from mysql.utilities.common.tools import check_python_version
from mysql.utilities.command.binlog_admin import binlog_rotate
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.messages import PARSE_ERR_OPTS_REQ
from mysql.utilities.common.options import setup_common_options
from mysql.utilities.common.options import add_verbosity, get_ssl_dict
from mysql.utilities.exception import UtilError, FormatError

# Check Python version compatibility
check_python_version()

# Constants
NAME = "MySQL Utilities - mysqlbinlogrotate "
DESCRIPTION = "mysqlbinlogrotate - rotates the active binary log file"
USAGE = (
    "%prog --server=user:pass@host:port"
)
DATE_FORMAT = '%Y-%m-%d %H:%M:%S %p'
EXTENDED_HELP = """
Introduction
------------
The mysqlbinlogrotate utility was designed to rotate the active binary log.

The following are examples of use:
  # Rotate the active binary log from a server.
  $ mysqlbinlogrotate --server=root:pass@host1:3306

  # Rotate the active binary log from a server if the active binlog is bigger
  # than 1MB or 1048576 bytes.
  $ mysqlbinlogrotate --server=root:pass@host1:3306 \\
                      --min-size=1048576
"""

if __name__ == '__main__':
    # Setup the command parser
    parser = setup_common_options(os.path.basename(sys.argv[0]),
                                  DESCRIPTION, USAGE, False, True,
                                  server_default=None,
                                  extended_help=EXTENDED_HELP, add_ssl=True)

    # Do not Purge binlog, instead print info
    parser.add_option("--min-size", action="store", dest="min_size",
                      type="int",
                      help="rotate the active binlog file only if the file "
                      "size exceeds the specified value in bytes.")

    # Add verbosity
    add_verbosity(parser, quiet=False)

    # Now we process the rest of the arguments.
    opt, args = parser.parse_args()

    # Check mandatory options: --server
    if not opt.server:
        parser.error(PARSE_ERR_OPTS_REQ.format(
            opt="--server"))

    servers_val = None
    # Parse source connection values if --server provided or default
    try:
        ssl_opts = get_ssl_dict(opt)
        server_val = parse_connection(opt.server, None, ssl_opts)
    except FormatError as err:
        # pylint: disable=E1101
        parser.error("ERROR: {0}\n".format(err.errmsg))
    except UtilError as err:
        parser.error("ERROR: {0}\n".format(err.errmsg))

    # Create dictionary of options
    options = {
        'verbosity': 0 if opt.verbosity is None else opt.verbosity,
        "min_size": opt.min_size,
    }

    try:
        binlog_rotate(server_val, options)
    except UtilError:
        _, e, _ = sys.exc_info()
        errmsg = e.errmsg
        sys.stderr.write("ERROR: {0}\n".format(errmsg))
        sys.exit(1)

    sys.exit(0)
