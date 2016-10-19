#!/usr/bin/env python
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
This file contains the .frm file utility for reading .frm files to construct
CREATE TABLE commands and display diagnostic information.
"""

import os
import sys

from mysql.utilities.common.tools import (check_python_version,
                                          check_connector_python)
from mysql.utilities import VERSION_FRM
from mysql.utilities.exception import FormatError, UtilError
from mysql.utilities.command.read_frm import (read_frm_files,
                                              read_frm_files_diagnostic)
from mysql.utilities.common.options import CaseInsensitiveChoicesOption
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.options import (add_ssl_options, add_verbosity,
                                            get_ssl_dict, license_callback,
                                            UtilitiesParser,
                                            check_password_security)
from mysql.utilities.common.server import connect_servers

# Check Python version compatibility
check_python_version()

# Check C/Python version compatibility
if not check_connector_python():
    sys.exit(1)


class MyParser(UtilitiesParser):
    """Custom class to set the epilog.
    """
    def format_epilog(self, formatter):
        return self.epilog

# Constants
NAME = "MySQL Utilities - mysqlfrm "
DESCRIPTION = "mysqlfrm - show CREATE TABLE from .frm files"
USAGE = ("%prog --server=[user[:<pass>]@host[:<port>][:<socket>]|"
         "<login-path>[:<port>][:<socket>]] [path\\tbl1.frm|db:tbl.frm]")
EXTENDED_HELP = """
Introduction
------------
The mysqlfrm utility is designed as a recovery tool that reads .frm files and
produces facsimile CREATE statements from the table definition data found in
the .frm file. In most cases, the CREATE statement produced will be usable
for recreating the table on another server or for extended diagnostics.
However, some features are not saved in the .frm files and therefore will be
omitted. The exclusions include but are not limited to:

  - foreign key constraints
  - auto increment number sequences

The mysqlfrm utility has two modes of operation. The default mode is
designed to spawn an instance of an installed server by reference
to the base directory using the --basedir option or by connecting to the
server with the --server option. The process will not alter the original
.frm file(s). This mode also requires the --port option to specify a
port to use for the spawned server. The spawned server will be shutdown
and all temporary files removed after the .frm files are read.

A diagnostic mode is available by using the --diagnostic option. This will
switch the utility to reading the .frm files byte-by-byte to recover as
much information as possible. The diagnostic mode has additional limitations
in that it cannot decipher character set or collation values without using
an existing server installation specified with either the --server or
--basedir option. This can also affect the size of the columns if the table
uses multi-byte characters. Use this mode when the default mode cannot read
the file or if there is no server installed on the host.

To read .frm files, list each file as a separate argument for the utility as
shown in the following examples. You will need to specify the path for each
.frm file you want to read or supply a path to a directory and all of the
.frm files in that directory will be read.

  # Read a single .frm file in the default mode using the server installed
  # in /usr/local/bin/mysql where the .frm file is in the current folder.
  # Notice the use of the db:table.frm format for specifying the database
  # name for the table. The database name appears to the left of ':' and
  # the .frm name to the right. So in this case, we have database = test1
  # and table = db1 so the CREATE statement will read CREATE test1.db1.

  $ mysqlfrm --basedir=/usr/local/bin/mysql test1:db1.frm --port=3333

  # Read multiple .frm files in the default mode using a running server
  # where the .frm files are located in different folders.

  $ mysqlfrm --server=root:pass@localhost:3306 /mysql/data/temp1/t1.frm \\
             /mysql/data/temp2/g1.frm --port=3310

  # Execute the spawned server under a different user name and read
  # all of the .frm files in a particular folder in default mode.

  $ mysqlfrm --server=root:pass@localhost:3306 /mysql/data/temp1/t1.frm \\
             /mysql/data/temp2/g1.frm --port=3310 --user=joeuser

  # Read all of the .frm files in a particular folder using the diagnostic
  # mode.

  $ mysqlfrm --diagnostic /mysql/data/database1



Helpful Hints
-------------
  - Tables with certain storage engines cannot be read in the default mode.
    These include PARTITION, PERFORMANCE_SCHEMA. You must read these with
    the --diagnostic mode.

  - Use the --diagnostic mode for tables that fail to open correctly
    in the default mode or if there is no server installed on the host.

  - To change the storage engine in the CREATE statement generated for all
    .frm files read, use the --new-storage-engine option

  - To turn off all messages except the CREATE statement and warnings or
    errors, use the --quiet option.

  - Use the --show-stats option to see file statistics for each .frm file.

  - If you encounter connection or similar errors when running in default
    mode, re-run the command with the --verbose option and view the
    output from the spawned server and repair any errors in launching the
    server. If mysqlfrm fails in the middle, you may need to manually
    shutdown the server on the port specified with --port.

  - If the spawned server takes more than 10 seconds to start, use the
    --start-timeout option to increase the timeout to wait for the
    spawned server to start.

  - If you need to run the utility with elevated privileges, use the --user
    option to execute the spawned server using a normal user account.

  - You can specify the database name to be used in the resulting CREATE
    statement by prepending the .frm file with the name of the database
    followed by a colon. For example, oltp:t1.frm will use 'oltp' for the
    database name in the CREATE statement. The optional database name can
    also be used with paths. For example, /home/me/oltp:t1.frm will use
    'oltp' as the database name. If you leave off the optional database
    name and include a path, the last folder will be the database name.
    For example /home/me/data1/t1.frm will use 'data1' as the database
    name. If you do not want to use the last folder as the database name,
    simply specify the colon like this: /home/me/data1/:t1.frm. In this
    case, the database will be omitted from the CREATE statement.

  - If you use the --new-storage-engine option, you must also provide the
    --frmdir option. When these options are specified, the utility will
    generate a new .frm file (prefixed with 'new_') and save it in the
    --frmdir= directory.

Enjoy!

"""

if __name__ == '__main__':
    # Setup the command parser
    program = os.path.basename(sys.argv[0]).replace(".py", "")
    parser = MyParser(
        version=VERSION_FRM.format(program=program),
        description=DESCRIPTION,
        usage=USAGE,
        add_help_option=False,
        option_class=CaseInsensitiveChoicesOption,
        epilog=EXTENDED_HELP,
        prog=program
    )

    # Add --License option
    parser.add_option("--license", action='callback',
                      callback=license_callback,
                      help="display program's license and exit")

    # Add --help option
    parser.add_option("--help", action="help")

    # Setup utility-specific options:

    # Add --basedir option
    parser.add_option("--basedir", action="store", dest="basedir",
                      default=None, type="string",
                      help="the base directory for the server")

    # Add diagnostic mode
    parser.add_option("--diagnostic", action="store_true", dest="diagnostic",
                      help="read the frm files byte-by-byte to form the "
                           "CREATE statement. May require the --server or "
                           "--basedir options to decipher character set "
                           "information")
    # Add engine
    parser.add_option("--new-storage-engine", action="store",
                      dest="new_engine", default=None,
                      help="change ENGINE clause to use this engine.")

    # Add frmdir
    parser.add_option("--frmdir", action="store", dest="frmdir", default=None,
                      help="save the new .frm files in this directory. "
                           "Used and valid with --new-storage-engine only.")

    # Need port - only valid with --diagnostic mode
    parser.add_option("--port", action="store", dest="port",
                      help="Port to use for the spawned server.", default=None)

    # Add show-stats
    parser.add_option("--show-stats", "-s", action="store_true",
                      dest="show_stats",
                      help="show file statistics and general table "
                           "information.")

    # Add server option
    parser.add_option("--server", action="store", dest="server", type="string",
                      default=None,
                      help="connection information for the server in the "
                           "form: <user>[:<password>]@<host>[:<port>]"
                           "[:<socket>] or <login-path>[:<port>][:<socket>] "
                           "(optional) - if provided, the storage engine and "
                           "character set information will be validated "
                           "against this server.")

    # Add user option
    parser.add_option("--user", action="store", dest="user", type="string",
                      default=None,
                      help="user account to launch spawned server. Required "
                           "if running as root user. Used only in the "
                           "default mode.")

    # Add startup timeout
    parser.add_option("--start-timeout", action="store", dest="start_timeout",
                      type=int, default=10,
                      help="Number of seconds to wait for spawned server to "
                           "start. Default = 10.")

    # Add verbosity mode
    add_verbosity(parser, True)

    # Add ssl options
    add_ssl_options(parser)

    # Now we process the rest of the arguments.
    opt, args = parser.parse_args()

    # Check security settings
    check_password_security(opt, args)

    # Check for argument errors
    if not args:
        parser.error("Nothing to do. You must specify a list of paths or "
                     "files to read. See --help for more information and "
                     "examples.")

    if not opt.port and not opt.diagnostic:
        parser.error("The --port option is required for reading .frm files in "
                     "the default mode.")

    if opt.diagnostic and opt.port:
        print("# WARNING The --port option is not used in the "
              "--diagnostic mode.")

    use_port = opt.port
    if not opt.diagnostic and opt.port:
        try:
            use_port = int(opt.port)
        except ValueError:
            parser.error("The --port option requires an integer value.")

    # Check for access to basedir if specified
    if opt.basedir:
        opt.basedir = os.path.expanduser(opt.basedir)
        if not os.access(opt.basedir, os.R_OK):
            parser.error("You must have read access to the base directory "
                         "specified with the --basedir option.")

    # Warn if both --server and --basedir used
    if opt.server and opt.basedir:
        print ("# WARNING: The --server option is not needed when the "
               "--basedir option is used.")

    # Warn if --diagnostic and --user
    if opt.diagnostic and opt.user:
        print ("# WARNING: The --user option is only used for the default "
               "mode.")

    # Check for --new-storage-engine and --frmdir
    if opt.new_engine:
        if not opt.frmdir:
            parser.error("You must specify the --frmdir with "
                         "--new-storage-engine.")
        # Check frmdir validity
        else:
            if not os.path.exists(opt.frmdir):
                parser.error("The directory, "
                             "'{0}' does not exist.".format(opt.frmdir))
            if not os.access(opt.frmdir, os.R_OK | os.W_OK):
                parser.error("You must have read and write access to the .frm "
                             "directory '{0}'.".format(opt.frmdir))
    elif not opt.new_engine and opt.frmdir:
        print("# WARNING: --frmdir encountered without --new-storage-engine. "
              "No .frm files will be saved.")

    server = None
    if opt.server is None and opt.diagnostic:
        print("# WARNING: Cannot generate character set or "
              "collation names without the --server option.")

    # Check start timeout for minimal value
    if int(opt.start_timeout) < 10:
        opt.start_timeout = 10
        print("# WARNING: --start-timeout must be >= 10 seconds. Using "
              "default value.")

    # Parse source connection values if --server provided
    if opt.server is not None and not opt.basedir:
        try:
            ssl_opts = get_ssl_dict(opt)
            source_values = parse_connection(opt.server, None, ssl_opts)
        except FormatError as err:
            parser.error("Source connection values invalid: %s." % err)
        except UtilError as err:
            parser.error("Source connection values invalid: %s." % err.errmsg)

        try:
            conn_options = {
                'version': "5.1.30",
                'quiet': opt.quiet,
            }
            servers = connect_servers(source_values, None, conn_options)
        except UtilError as error:
            parser.error(error.errmsg)
        server = servers[0]

        if use_port == int(server.port):
            parser.error("You must specify a different port to use for the "
                         "spawned server.")

        basedir = server.show_server_variable("basedir")[0][1]
    else:
        basedir = opt.basedir

    # Set options for frm operations.
    options = {
        "basedir": basedir,
        "new_engine": opt.new_engine,
        "show_stats": opt.show_stats,
        "port": use_port,
        "quiet": opt.quiet,
        "server": server,
        "verbosity": opt.verbosity if opt.verbosity else 0,
        "user": opt.user,
        "start_timeout": opt.start_timeout,
        "frm_dir": opt.frmdir,
    }

    # Print disclaimer banner for diagnostic mode
    if opt.diagnostic:
        print ("# CAUTION: The diagnostic mode is a best-effort parse of the "
               ".frm file. As such, it may not identify all of the components "
               "of the table correctly. This is especially true for damaged "
               "files. It will also not read the default values for the "
               "columns and the resulting statement may not be syntactically "
               "correct.")

    if os.name == "posix":
        if os.getuid() == 0 and not opt.diagnostic and not opt.user:
            parser.error("Running a spawned server as root is not advised. If "
                         "you want to run the utility as root, please provide "
                         "the --user option to specify a user to use to "
                         "launch the server. Example: --user=mysql.")

    all_frm_files = []
    for arg in args:
        frm_files_found = []

        # check to see if we have access iff it is not in the form of
        # db:table.frm, but watchout for Windows paths!
        if (os.name != "nt" and ":" not in arg) or \
           (os.name == "nt" and len(arg) >= 2 and ":" not in arg[2:]):
            if not os.access(arg, os.R_OK):
                print ("ERROR: Cannot read %s. You must have read privileges"
                       " to the file or path and it must exist. Skipping "
                       "this argument." % arg)
                continue

        # if argument is a folder, get all files from the folder and read them
        if os.path.isdir(arg):
            files = os.listdir(arg)
            for filename in files:
                if os.path.splitext(filename)[1].lower() == ".frm":
                    frm_files_found.append(os.path.join(arg, filename))
        else:
            frm_files_found.append(arg)

        if not frm_files_found:
            print "# NOTE: No .frm files found in folder %s." % arg
            continue
        all_frm_files.extend(frm_files_found)

    # For each file specified, attempt to read the .frm file
    try:
        all_frm_files.sort()
        if opt.diagnostic:
            read_frm_files_diagnostic(all_frm_files, options)
        else:
            failed = read_frm_files(all_frm_files, options)
            if failed:
                print ("#\n# WARNING: The following files could not be read. "
                       "You can try the --diagnostic mode to read these "
                       "files.\n#")
                for frm_file in failed:
                    print "#", frm_file
                print "#"
    except UtilError as error:
        print "ERROR: {0}".format(error.errmsg)
        sys.exit(1)

    if not opt.quiet:
        print "#...done."

    sys.exit()
