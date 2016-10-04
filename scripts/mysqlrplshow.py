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
This file contains the show replication topology utility. It is used to
find the slaves for a given master and can traverse the list of slaves
checking for additional master/slave connections.
"""

import os.path
import sys

from mysql.utilities.common.tools import check_python_version
from mysql.utilities.exception import UtilError, FormatError
from mysql.utilities.command.show_rpl import show_topology
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.tools import check_connector_python
from mysql.utilities.common.options import (add_verbosity, add_format_option,
                                            setup_common_options,
                                            add_ssl_options,
                                            check_password_security)

# Check Python version compatibility
check_python_version()

# Constants
NAME = "MySQL Utilities - mysqlrplshow "
DESCRIPTION = "mysqlrplshow - show slaves attached to a master"
USAGE = "%prog --master=root@localhost:3306 "

PRINT_WIDTH = 75

# Check for connector/python
if not check_connector_python():
    sys.exit(1)

if __name__ == '__main__':
    # Setup the command parser
    parser = setup_common_options(os.path.basename(sys.argv[0]),
                                  DESCRIPTION, USAGE, True, False)

    # Setup utility-specific options:

    # Connection information for the source server
    parser.add_option("--master", action="store", dest="master",
                      type="string", default="root@localhost:3306",
                      help="connection information for master server in the "
                           "form: <user>[:<password>]@<host>[:<port>]"
                           "[:<socket>] or <login-path>[:<port>][:<socket>]"
                           " or <config-path>[<[group]>].")

    # Show graph option
    parser.add_option("-l", "--show-list", action="store_true",
                      dest="show_list",
                      help="print a list of the topology.",
                      default=False)

    # Output format
    add_format_option(parser, "display the list in either grid (default), "
                      "tab, csv, or vertical format", "grid")

    # Check slaves option - if True, recurse slaves from master to find
    # additional master/slave connections
    parser.add_option("-r", "--recurse", action="store_true",
                      dest="recurse",
                      help="traverse the list of slaves to find additional "
                      "master/slave connections. User this option to map a "
                      "replication topology.", default=False)

    # Add limit for recursion
    parser.add_option("--max-depth", action="store", default=None, type="int",
                      help="limit the traversal to this depth. Valid only "
                           "with the --recurse option. Valid values are "
                           "non-negative integers.",
                      dest="max_depth")

    # Prompt for slave connections if default login/password fail
    parser.add_option("-p", "--prompt", action="store_true", dest="prompt",
                      help="prompt for slave user and password if different "
                           "from master login.",
                      default=False)

    # Number of retries for failed slave login
    parser.add_option("-n", "--num-retries", action="store",
                      dest="num_retries", type="int",
                      help="number of retries allowed for failed slave login "
                           "attempt. Valid with --prompt only.",
                      default=0)

    # Add ssl options
    add_ssl_options(parser)

    # Add verbosity mode and quiet option
    add_verbosity(parser, True)

    parser.add_option("--discover-slaves-login", action="store",
                      dest="discover", default=None, type="string",
                      help="at startup, query master for all registered "
                           "slaves and use the user name and password "
                           "specified to connect. Supply the user and "
                           "password in the form <user>[:<password>] or "
                           "<login-path>. For example, --discover-slaves-"
                           "login=joe:secret will use 'joe' as the user and "
                           "'secret' as the password for each discovered "
                           "slave.")

    # Now we process the rest of the arguments.
    opt, args = parser.parse_args()

    # Check security settings
    check_password_security(opt, args)

    # Fail is --discover-slaves-login not specified
    if opt.discover is None:
        parser.error("The --discover-slaves-login is required to test slave "
                     "connectivity.")

    # Fail if recurse specified and max-depth is invalid
    if opt.recurse and opt.max_depth is not None:
        if opt.max_depth < 0:
            parser.error("The --max-depth option needs to be >= 0.")

    # Parse master connection values
    try:
        m_values = parse_connection(opt.master, None, opt)
    except FormatError:
        _, err, _ = sys.exc_info()
        parser.error("Master connection values invalid: %s." % err)
    except UtilError:
        _, err, _ = sys.exc_info()
        parser.error("Master connection values invalid: %s." % err.errmsg)

    # Create dictionary of options
    options = {
        'quiet': opt.quiet,
        'prompt': opt.prompt,
        'num_retries': opt.num_retries,
        'recurse': opt.recurse,
        'show_list': opt.show_list,
        'format': opt.format,
        'max_depth': opt.max_depth,
        'discover': opt.discover,
        'verbosity': opt.verbosity
    }

    try:
        show_topology(m_values, options)
    except UtilError:
        _, e, _ = sys.exc_info()
        print("ERROR: {0}".format(e.errmsg))
        sys.exit(1)

    sys.exit()
