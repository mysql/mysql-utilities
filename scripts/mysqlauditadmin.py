#!/usr/bin/env python
#
# Copyright (c) 2012, 2016, Oracle and/or its affiliates. All rights reserved.
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
This file contains the audit log administration utility which allows users to
manage the audit log (i.e., view/edit control variables; perform on-demand
log file rotation, and copy log files to other locations).
"""

import os.path
import sys

from mysql.utilities.common.tools import check_python_version
from mysql.utilities import VERSION_FRM
from mysql.utilities.exception import UtilError, FormatError
from mysql.utilities.command import audit_log
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.command.audit_log import (AuditLog,
                                               command_requires_value,
                                               command_requires_log_name,
                                               command_requires_server)
from mysql.utilities.common.messages import PARSE_ERR_SSL_REQ_SERVER
from mysql.utilities.common.options import (add_ssl_options, add_verbosity,
                                            UtilitiesParser,
                                            CaseInsensitiveChoicesOption,
                                            license_callback,
                                            check_password_security)
from mysql.utilities.common.tools import (check_connector_python,
                                          show_file_statistics)

# Check Python version compatibility
check_python_version()


class MyParser(UtilitiesParser):
    """Custom class to set the epilog.
    """
    def format_epilog(self, formatter):
        return self.epilog

# Constants
NAME = "MySQL Utilities - mysqlauditadmin "
DESCRIPTION = "mysqlauditadmin - audit log maintenance utility "
USAGE = "%prog --server=user:pass@host:port --show-options "

# Check for connector/python
if not check_connector_python():
    sys.exit(1)

if __name__ == '__main__':
    # Setup the command parser
    program = os.path.basename(sys.argv[0]).replace(".py", "")
    parser = MyParser(
        version=VERSION_FRM.format(program=program),
        description=DESCRIPTION,
        usage=USAGE,
        add_help_option=False,
        option_class=CaseInsensitiveChoicesOption,
        epilog=audit_log.VALID_COMMANDS_TEXT,
        prog=program
    )

    # Default option to provide help information
    parser.add_option("--help", action="help",
                      help="display this help message and exit")

    # Add --License option
    parser.add_option("--license", action='callback',
                      callback=license_callback,
                      help="display program's license and exit")

    # Setup utility-specific options:

    # Connection information for the source server
    parser.add_option("--server", action="store", dest="server",
                      type="string", default=None,
                      help="connection information for the server in the "
                           "form: <user>[:<password>]@<host>[:<port>]"
                           "[:<socket>] or <login-path>[:<port>][:<socket>]"
                           " or <config-path>[<[group]>].")

    # Audit Log name (full path)
    parser.add_option("--audit-log-name", action="store", dest="log_name",
                      type="string", default=None,
                      help="full path and file name for the audit log file. "
                           "Used for stats and copy options.")

    # Show variables
    parser.add_option("--show-options", action="store_true",
                      dest="show_options",
                      help="display the audit log system variables.")

    # Remote login
    parser.add_option("--remote-login", action="store", dest="rlogin",
                      type="string", default=None,
                      help="user name and host to be used for remote login "
                           "for copying log files. Format: <user>:<host_or_ip>"
                           " Password will be prompted.")

    # See file statistics
    parser.add_option("--file-stats", action="store_true", default=False,
                      dest="file_stats",
                      help="display the audit log file statistics.")

    # Copy file
    parser.add_option("--copy-to", action="store", dest="copy_location",
                      type="string", default=None,
                      help="the location to copy the audit log file "
                           "specified. The path must be locally accessible "
                           "for the current user.")

    # Value for command option
    parser.add_option("--value", action="store", dest="value", default=None,
                      type="string",
                      help="value used to set variables based "
                           "on the command specified. See --help for list per "
                           "command.")

    # Add ssl options
    add_ssl_options(parser)

    # Add verbosity mode
    add_verbosity(parser, False)

    # Now we process the rest of the arguments.
    opt, args = parser.parse_args()

    # Check security settings
    check_password_security(opt, args)

    # Perform error checking

    # One command at a time
    if len(args) > 1:
        parser.error("You can only perform one command at a time.")

    # Valid command?
    if args and args[0].upper() not in audit_log.VALID_COMMANDS:
        parser.error("The command '%s' is not a valid command." % args[0])

    if args:
        command = args[0].upper()
    else:
        command = None

    # At least one valid option must be specified
    if (not opt.log_name and not opt.rlogin and not opt.value and
            not opt.server and not opt.copy_location and
            not opt.show_options and not opt.file_stats):
        parser.error("At least one valid option must be specified.")

    # if command, check to see if it requires a value.
    if command and command_requires_value(command) and not opt.value:
        parser.error("The command %s requires the --value option." % command)

    # The --value option must be used with a valid command
    if opt.value and not command_requires_value(command):
        parser.error("The --value option must be used with a valid command.")

    # The --server option is required.
    if command_requires_server(command) and not opt.server:
        parser.error("The --server option is required for the {0} command."
                     "".format(command))

    # The --server option must be used with --show-options and/or a valid
    # command
    if opt.server and (not opt.show_options and
                       not command_requires_server(command)):
        parser.error("The --server option requires --show-options and/or "
                     "a valid command.")

    # The --server option is also required by --show-options
    if opt.show_options and not opt.server:
        parser.error("The --server option is required for --show-options.")

    # The --audit-log-name is required if a command specified.
    if command_requires_log_name(command) and not opt.log_name:
        parser.error("The --audit-log-name option is required for the {0} "
                     "command.".format(command))

    if opt.log_name and (not opt.file_stats and
                         not command_requires_log_name(command)):
        parser.error("The --audit-log-name option requires --file-stats "
                     "and/or a valid command.")

    # ssl option requires server
    if not opt.server and (opt.ssl_ca or opt.ssl_cert or opt.ssl_key):
        parser.error(PARSE_ERR_SSL_REQ_SERVER)

    # Attempt to parse the --server option
    server_values = None
    if opt.server:
        try:
            server_values = parse_connection(opt.server, None, opt)
        except FormatError:
            _, err, _ = sys.exc_info()
            parser.error("Server connection values invalid: %s." % err)
        except UtilError:
            _, err, _ = sys.exc_info()
            parser.error("Server connection values invalid: %s." % err.errmsg)

    # Check for copy prerequisites
    if command and command == "COPY" and not opt.copy_location:
        parser.error("You must specify the --copy-to option for copying a log "
                     "file.")

    # The --copy-to option requires the command COPY
    if opt.copy_location and (command != "COPY"):
        parser.error("The --copy-to option can only be used with the COPY "
                     "command.")

    # Check copy-to location
    if ((command and command == "COPY" and opt.copy_location) and
            not os.access(opt.copy_location, os.W_OK | os.R_OK)):
        parser.error("You must have read and write access to the destination "
                     "for audit log copy.")

    # Check args for copy-to, file-stats
    if ((command and command == "COPY" and opt.copy_location) or
            opt.file_stats) and not opt.log_name:
        parser.error("You must specify the --audit-log-name option for "
                     "copying log files or viewing file statistics.")

    # Check if the specified audit-log-name is a file
    if opt.log_name and not opt.rlogin and not os.path.isfile(opt.log_name):
        parser.error("The specified --audit-log-name is not a file: %s"
                     % opt.log_name)

    # Check remote login format
    if opt.rlogin:
        try:
            user, host = opt.rlogin.split(":", 1)
        except:
            parser.error("The --remote-login option should be in the format: "
                         "<user>:<host_or_ip>")

        if not command and command == "COPY":
            parser.error("The --remote-login option can only be used with the "
                         "COPY command.")

    # Create dictionary of options
    options = {
        'verbosity': opt.verbosity,
        'command': command,
        'log_name': opt.log_name,
        'server_vals': server_values,
        'rlogin': opt.rlogin,
        'file_stats': opt.file_stats,
        'show_options': opt.show_options,
        'copy_location': opt.copy_location,
        'value': opt.value,
    }

    try:
        # Open a connection to the audit log manager and run the audit
        # log commands as specified by the options.
        log = AuditLog(options)

        # Make sure server supports the audit log else fail
        if command != "COPY" and not opt.file_stats:
            log_error = log.check_audit_log()
            if log_error:
                parser.error(log_error)

        # Show audit log options before command
        if opt.show_options:
            # if some other command has run
            if len(args):
                print("#\n# Showing options before command.")
            log.show_options()

        # Execute the command specified
        if len(args):
            log.do_command()

        # Show audit log options after command if appropriate
        if opt.show_options and len(args):
            # if some other command has run
            print("#\n# Showing options after command.")
            log.show_options()

        # Do file stats
        if opt.file_stats:
            show_file_statistics(opt.log_name, True)

    except UtilError:
        _, e, _ = sys.exc_info()
        print("ERROR: %s" % e.errmsg)
        sys.exit(1)

    sys.exit(0)
