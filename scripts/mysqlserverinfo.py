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
This file contains the server information utility.
"""

import os
import sys

from mysql.utilities.common.tools import check_python_version
from mysql.utilities.exception import UtilError
from mysql.utilities.command.serverinfo import show_server_info
from mysql.utilities.common.tools import check_connector_python
from mysql.utilities.common.options import (add_basedir_option, add_verbosity,
                                            add_format_option,
                                            get_ssl_dict,
                                            add_no_headers_option,
                                            check_dir_option,
                                            setup_common_options,
                                            check_password_security)

# Check Python version compatibility
check_python_version()

# Constants
NAME = "MySQL Utilities - mysqlserverinfo "
DESCRIPTION = "mysqlserverinfo - show server information"
USAGE = "%prog --server=user:pass@host:port:socket --format=grid"

# Check for connector/python
if not check_connector_python():
    sys.exit(1)

if __name__ == '__main__':
    # Setup the command parser and setup server, help
    parser = setup_common_options(os.path.basename(sys.argv[0]),
                                  DESCRIPTION, USAGE, True)

    # Setup utility-specific options:

    # Input format
    add_format_option(parser, "display the output in either grid (default), "
                      "tab, csv, or vertical format", "grid")

    # No header option
    add_no_headers_option(parser, restricted_formats=['grid', 'tab', 'csv'])

    # Show my.cnf values
    parser.add_option("-d", "--show-defaults", action="store_true",
                      dest="show_defaults", default=False,
                      help="show defaults from the config file per server")

    # Add --start option
    parser.add_option("-s", "--start", action="store_true", dest="start",
                      help="start server in read only mode if offline")

    # Add --basedir option
    add_basedir_option(parser)

    # Add --datadir option
    parser.add_option("--datadir", action="store", dest="datadir",
                      default=None, type="string",
                      help="the data directory for the server")

    # Add --search-port
    parser.add_option("--port-range", action="store", dest="ports",
                      default="3306:3333", type="string",
                      help="the port range to search for running mysql "
                           "servers on Windows systems")

    # Add --show-servers option
    parser.add_option("--show-servers", action="store_true",
                      dest="show_servers",
                      help="show any known MySQL servers running on this host")

    # Add startup timeout
    parser.add_option("--start-timeout", action="store",
                      dest="start_timeout", type=int, default=10,
                      help="Number of seconds to wait for the server to "
                           "start. Default = 10.")

    # Add verbosity mode
    add_verbosity(parser, False)

    # Now we process the rest of the arguments.
    opt, args = parser.parse_args()

    # Check security settings
    check_password_security(opt, args)

    # The --basedir and --datadir options are only required if --start is used
    # otherwise they are ignored.
    if opt.start:
        # Check the basedir option for errors (e.g., invalid path).
        check_dir_option(parser, opt.basedir, '--basedir', check_access=True,
                         read_only=True)

        # Check the datadir option for errors.
        check_dir_option(parser, opt.datadir, '--datadir', check_access=True,
                         read_only=False)

    # Check start timeout for minimal value
    if int(opt.start_timeout) < 10:
        opt.start_timeout = 10
        print("# WARNING: --start-timeout must be >= 10 seconds. Using "
              "default value 10.")

    # Check port range
    if os.name == 'nt':
        parts = opt.ports.split(":")
        if len(parts) != 2:
            print("# WARNING : {0} is not a valid port range. "
                  "Using default." .format(opt.ports))
            opt.ports = "3306:3333"

    # Set options for database operations.
    options = {
        "format": opt.format,
        "no_headers": opt.no_headers,
        "verbosity": opt.verbosity,
        "debug": opt.verbosity >= 3,
        "show_defaults": opt.show_defaults,
        "start": opt.start,
        "basedir": opt.basedir,
        "datadir": opt.datadir,
        "ports": opt.ports,
        "show_servers": opt.show_servers,
        "start_timeout": opt.start_timeout,
    }

    if opt.server is None and not opt.show_servers:
        parser.error("You must specify at least one server.")

    # add ssl options values.
    options.update(get_ssl_dict(opt))

    try:
        show_server_info(opt.server, options)
    except UtilError:
        _, e, _ = sys.exc_info()
        print("ERROR: {0}".format(e.errmsg))
        sys.exit(1)
    except:
        _, e, _ = sys.exc_info()
        print("ERROR: {0}".format(e))
        sys.exit(1)

    print("#...done.")

    sys.exit()
