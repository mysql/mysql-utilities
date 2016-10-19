#!/usr/bin/env python
#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights reserved.
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
This file contains the clone server utility which launches a new instance
of an existing server.
"""

import os.path
import sys

from mysql.utilities.common.tools import check_python_version
from mysql.utilities import exception
from mysql.utilities.command import serverclone
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.tools import check_connector_python
from mysql.utilities.common.options import (add_basedir_option, add_verbosity,
                                            get_ssl_dict,
                                            check_dir_option,
                                            setup_common_options,
                                            check_password_security)
from mysql.utilities.common.server import Server

# Check Python version compatibility
check_python_version()

# Constants
NAME = "MySQL Utilities - mysqlserverclone "
DESCRIPTION = "mysqlserverclone - start another instance of a running server"
USAGE = "%prog --server=user:pass@host:port:socket --new-data=/tmp/data2 " \
        "--new-port=3310 --new-id=12 --root-password=root"

CLONE_FAILED = ("ERROR: Unable to connect to cloned server. Server may have "
                "failed to start. Try running the clone again using the -vvv "
                "option, which presents all of the messages from the server "
                "to the console. Correct the error(s) and retry the clone.")

# Check for connector/python
if not check_connector_python():
    sys.exit(1)

if __name__ == '__main__':
    # Setup the command parser and setup server, help
    parser = setup_common_options(os.path.basename(sys.argv[0]),
                                  DESCRIPTION, USAGE, False, True, None)

    # Setup utility-specific options:

    # Data directory for new instance
    parser.add_option("--new-data", action="store", dest="new_data",
                      type="string",
                      help="the full path to the location of the data "
                           "directory for the new instance. The path size "
                           "must be smaller or equal than {0} "
                           "characters.".format(serverclone.MAX_DATADIR_SIZE))

    # Port for the new instance
    parser.add_option("--new-port", action="store", dest="new_port",
                      type="string", default="3307",
                      help="the new port for the new instance - "
                           "default=%default")

    # Server id for the new instance
    parser.add_option("--new-id", action="store", dest="new_id",
                      type="string", default="2",
                      help="the server_id for the new instance - "
                           "default=%default")

    # Root password for the new instance
    parser.add_option("--root-password", action="store", dest="root_pass",
                      type="string", help="password for the root user")

    # Optional additional command-line options
    parser.add_option("--mysqld", action="store", dest="mysqld",
                      type="string", help="additional options for mysqld")

    # Option to write command to file
    parser.add_option("--write-command", "-w", action="store", dest='cmd_file',
                      default=None, type="string",
                      help="path to file for writing startup command. For "
                           "example: start_server1.sh")

    # Add verbosity and quiet mode
    add_verbosity(parser, True)

    # Add --basedir option
    add_basedir_option(parser)

    # Add --delete-data
    parser.add_option("--delete-data", action="store_true", dest="delete",
                      help="delete the folder specified by --new-data if it "
                           "exists and is not empty.")

    # Add user option
    parser.add_option("--user", action="store", dest="user", type="string",
                      default=None,
                      help="user account to launch cloned server. Default is "
                           "current user.")

    # Add startup timeout
    parser.add_option("--start-timeout", action="store", dest="start_timeout",
                      type=int, default=10,
                      help="Number of seconds to wait for server to start. "
                           "Default = 10.")

    # Add force option
    parser.add_option("--force", action="store_true", dest="force",
                      default=False,
                      help="Ignore the maximum path length and the low space "
                           "checks for the --new-data option.")

    # Now we process the rest of the arguments.
    opt, args = parser.parse_args()

    # Check security settings
    check_password_security(opt, args)

    # Check the basedir option for errors (e.g., invalid path)
    check_dir_option(parser, opt.basedir, '--basedir')

    # Can only use --basedir and --datadir if --server is missing
    if opt.basedir is not None and opt.server is not None:
        parser.error("Cannot use the --basedir and --server options together.")

    # Fail if no database path specified.
    if opt.new_data is None:
        parser.error("No new database path. Use --help for available options.")

    # Warn if root-password is left off.
    if opt.root_pass is None or opt.root_pass == '':
        print("# WARNING: Root password for new instance has not been set.")

    # Fail if user does not have access to new data dir.
    if os.path.exists(opt.new_data):
        if not os.access(opt.new_data, os.R_OK | os.W_OK):
            parser.error("You do not have enough privileges to access the "
                         "folder specified by --new-data.")

        # Fail if new data is not empty and delete not specified
        if os.listdir(opt.new_data) and not opt.delete:
            parser.error("Target data directory exists and is not empty. Use "
                         "--delete-data option to delete folder before "
                         "cloning.")

    # Check start timeout for minimal value
    if int(opt.start_timeout) < 10:
        opt.start_timeout = 10
        print("# WARNING: --start-timeout must be >= 10 seconds. Using "
              "default value.")

    # Build options
    options = {
        'new_data': opt.new_data,
        'new_port': opt.new_port,
        'new_id': opt.new_id,
        'root_pass': opt.root_pass,
        'mysqld_options': opt.mysqld,
        'verbosity': opt.verbosity,
        'quiet': opt.quiet,
        'cmd_file': opt.cmd_file,
        'basedir': opt.basedir,
        'delete': opt.delete,
        'user': opt.user,
        'start_timeout': opt.start_timeout,
        'force': opt.force,
    }

    # Expand user paths and resolve relative paths
    if opt.new_data and opt.new_data[0] == '~':
        options['new_data'] = os.path.expanduser(opt.new_data)
    if opt.basedir and opt.basedir[0] == '~':
        options['basedir'] = os.path.expanduser(opt.basedir)
    if opt.new_data and opt.new_data[0] == '.':
        options['new_data'] = os.path.abspath(opt.new_data)
    if opt.basedir and opt.basedir[0] == '.':
        options['basedir'] = os.path.abspath(opt.basedir)

    # Parse source connection values if we have a running server
    if opt.basedir is None:
        conn_options = get_ssl_dict(opt)
        try:
            conn = parse_connection(opt.server, options=conn_options)

            # Now check for local server
            server = Server({'conn_info': conn})
            if not server.is_alias('localhost'):
                parser.error("Server to be cloned must be running on the same "
                             "machine as mysqlserverclone.")
        except exception.FormatError:
            _, err, _ = sys.exc_info()
            parser.error("Server connection values invalid: %s." % err)
        except exception.UtilError:
            _, err, _ = sys.exc_info()
            parser.error("Server connection values invalid: %s." % err.errmsg)
    else:
        conn = None

    try:
        serverclone.clone_server(conn, options)
    except exception.UtilError:
        _, e, _ = sys.exc_info()
        print(CLONE_FAILED)
        print("ERROR: {0}".format(e.errmsg))
        sys.exit(1)

    sys.exit()
