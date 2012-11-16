#
# Copyright (c) 2012 Oracle and/or its affiliates. All rights reserved.
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
This file contains features to examine an audit log file, including
searching and displaying the results.
"""

import sys
from mysql.utilities.exception import UtilError
from mysql.utilities.common.audit_log_parser import AuditLogParser
from mysql.utilities.common.format import convert_dictionary_list, print_list
from mysql.utilities.common.server import Server

_PRINT_WIDTH = 75

_VALID_COMMAND_OPTIONS = {
    'policies': ("ALL", "NONE", "LOGINS", "QUERIES", "DEFAULT"),
    'sizes': (0, 4294967295)
}

_COMMANDS_WITH_OPTIONS = ['POLICY', 'ROTATE_ON_SIZE']
_COMMANDS_WITH_SERVER_OPT = ['POLICY', 'ROTATE_ON_SIZE', 'ROTATE']

VALID_COMMANDS_TEXT = """
Available Commands:

  copy             - copy the audit log to a locally accessible path
  policy           - set the audit log policy
                     Values = {policies}
  rotate           - perform audit log rotation
  rotate_on_size   - set the rotate log size limit for auto rotation
                     Values = {sizes}

""".format(policies=', '.join(_VALID_COMMAND_OPTIONS['policies']),
           sizes=', '.join([str(v) for v in _VALID_COMMAND_OPTIONS['sizes']]))

VALID_COMMANDS = ["COPY", "POLICY", "ROTATE", "ROTATE_ON_SIZE"]

EVENT_TYPES = ["Audit", "Binlog Dump", "Change user", "Close stmt",
    "Connect Out", "Connect", "Create DB", "Daemon", "Debug", "Delayed insert",
    "Drop DB", "Execute", "Fetch", "Field List", "Init DB", "Kill",
    "Long Data", "NoAudit", "Ping", "Prepare", "Processlist", "Query", "Quit",
    "Refresh", "Register Slave", "Reset stmt", "Set option", "Shutdown",
     "Sleep", "Statistics", "Table Dump", "Time"]

QUERY_TYPES = ["CREATE", "ALTER", "DROP", "TRUNCATE", "RENAME", "GRANT",
                "REVOKE", "SELECT", "INSERT", "UPDATE", "DELETE", "COMMIT",
                "SHOW", "SET", "CALL", "PREPARE", "EXECUTE", "DEALLOCATE"]


def command_requires_log_name(command):
    """Check if the specified command requires the --audit-log-name option.

    command[in] command to be checked
    """
    return command == "COPY"


def command_requires_server(command):
    """Check if the specified command requires the --server option.

    command[in] command to be checked.
    """
    return command in _COMMANDS_WITH_SERVER_OPT


def command_requires_value(command):
    """Check the specified command requires an option (i.e. --value).

    command[in] command to be checked.
    """
    return command in _COMMANDS_WITH_OPTIONS


def check_command_value(command, value):
    """Check if the value is valid for the given command.

    command[in] command to which the value is concerned.
    value[in] value to check for the given command.
    """
    if command in _COMMANDS_WITH_OPTIONS:
        # do range values
        if command == "ROTATE_ON_SIZE":
            values = _VALID_COMMAND_OPTIONS['sizes']
            try:
                int_value = int(value)
            except ValueError:
                print "Invalid integer value: %s" % value
                return False
            if int_value < values[0] or int_value > values[1]:
                print "The %s command requires values in the range (%s, %s)." \
                      % (command, values[0], values[1])
                return False
        elif value.upper() not in _VALID_COMMAND_OPTIONS['policies']:
            print "The %s command requires one of the following " % command + \
                  "values: %s." % ', '.join(_VALID_COMMAND_OPTIONS['policies'])
            return False

    return True


class AuditLog(object):
    """ Class to manage and parse the audit log.

    The AuditLog class is used to manage and retrieve information of the
    audit log. It allows the execution of commands to change audit log
    settings, display control variables, copy and parse audit log files.
    """

    def __init__(self, options):
        """Constructor

        options[in]       dictionary of options to include width, verbosity,
                          pedantic, quiet
        """
        self.options = options
        self.log = None

    def open_log(self):
        """ Create an AuditLogParser and open the audit file.
        """
        self.log = AuditLogParser(self.options)
        self.log.open_log()

    def close_log(self):
        """Close the previously opened audit log file.
        """
        self.log.close_log()

    def parse_log(self):
        """ Parse the audit log file (previously opened), applying
        search/filtering criterion.
        """
        self.log.parse_log()

    def output_formatted_log(self):
        """Output the parsed log entries according to the specified format.

        Print the entries resulting from the parsing process to the standard
        output in the specified format. If no entries are found (i.e., none
        match the defined search criterion) a notification message is print.
        """
        log_rows = self.log.retrieve_rows()
        if log_rows:
            out_format = self.options.get("format", "GRID")
            if out_format == 'raw':
                for row in log_rows:
                    sys.stdout.write(row)
            else:
                #Convert the results to the appropriate format
                cols, rows = convert_dictionary_list(log_rows)
                # Note: No need to sort rows, retrieved with the same order
                # as read (i.e., sorted by timestamp)
                print_list(sys.stdout, out_format, cols, rows)
        else:
            #Print message notifying that no entry was found
            no_entry_msg = "#\n# No entry found!\n#"
            print no_entry_msg

    def check_audit_log(self):
        """Verify if the audit log plugin is installed on the server.
        Return the message error if not, or None.
        """
        error = None
        server = Server({'conn_info': self.options.get("server_vals", None)})
        server.connect()
        # Check to see if the plug-in is installed
        if not server.supports_plugin("audit"):
            error = "The audit log plug-in is not installed on this " + \
                    "server or is not enabled."
        server.disconnect()

        return error

    def show_statistics(self):
        """Display statistical information about audit log including:
            - size, date, etc.
            - Audit log entries
        """
        out_format = self.options.get("format", "GRID")
        log_name = self.options.get("log_name", None)
        # Print file statistics:
        print "#\n# Audit Log File Statistics:\n#"
        from mysql.utilities.common.tools import show_file_statistics
        show_file_statistics(log_name, False, out_format)

        # Print audit log 'AUDIT' entries
        print "\n#\n# Audit Log Startup Entries:\n#\n"
        cols, rows = convert_dictionary_list(self.log.header_rows)
        # Note: No need to sort rows, retrieved with the same order
        # as read (i.e., sorted by timestamp)
        print_list(sys.stdout, out_format, cols, rows)

    def show_options(self):
        """ Show all audit log variables.
        """
        server = Server({'conn_info': self.options.get("server_vals", None)})
        server.connect()
        rows = server.show_server_variable("audit%")
        server.disconnect()
        if rows:
            print "#\n# Audit Log Variables and Options\n#"
            print_list(sys.stdout, "GRID", ['Variable_name', 'Value'],
                       rows)
            print
        else:
            raise UtilError("No audit log variables found.")

    def _copy_log(self):
        """ Copy the audit log to a local destionation or from a remote server.
        """
        # Need to see if this is a local copy or not.
        rlogin = self.options.get("rlogin", None)
        log_name = self.options.get("log_name", None)
        copy_location = self.options.get("copy_location", None)
        if not rlogin:
            from shutil import copy
            copy(log_name, copy_location)
        else:
            from mysql.utilities.common.tools import remote_copy
            user, host = rlogin.split(":", 1)
            remote_copy(log_name, user, host, copy_location,
                        self.options.get("verbosity", 0))

    def _rotate_log(self, server):
        """Rotate the log.

        To rotate the log, first discover the value of rotate_on_size
        then set rotate_on_size to the minimum allowed value (i.e. 4096) and
        force rotation with a manual flush. Note: the rotation will only
        effectively occur if the audit log file size is greater than 4096.
        """

        # Get the current rotation size
        rotate_size = server.show_server_variable(
                                            "audit_log_rotate_on_size")[0][1]
        min_rotation_size = 4096

        # If needed, set rotation size to the minimum allowed value.
        if int(rotate_size) != min_rotation_size:
            #
            server.exec_query("SET @@GLOBAL.audit_log_rotate_on_size = %d" % \
                              min_rotation_size)

        # Flush the audit_log forcing the rotation if the file size is greater
        # than the minimum (i.e. 4096).
        server.exec_query("SET @@GLOBAL.audit_log_flush = ON")

        # If needed, restore the rotation size to what it was initially.
        if int(rotate_size) != min_rotation_size:
            server.exec_query("SET @@GLOBAL.audit_log_rotate_on_size = %s" %
                          rotate_size)

    def do_command(self):
        """ Check and execute the audit log command (previously set by the the
        options of the object constructor).
        """
        # Check for valid command
        command = self.options.get("command", None)
        if not command in VALID_COMMANDS:
            raise UtilError("Invalid command.")

        command_value = self.options.get("value", None)
        # Check for valid value if needed
        if (command_requires_value(command)
            and not check_command_value(command, command_value)):
            raise UtilError("Please provide the correct value for the %s "
                             "command." % command)

        # Copy command does not need the server
        if command == "COPY":
            self._copy_log()
            return True

        # Connect to server
        server = Server({'conn_info': self.options.get("server_vals", None)})
        server.connect()

        # Now execute the command
        print "#\n# Executing %s command.\n#\n" % command
        try:
            if command == "POLICY":
                server.exec_query("SET @@GLOBAL.audit_log_policy = %s" %
                                  command_value)
            elif command == "ROTATE":
                self._rotate_log(server)
            else:  # "ROTATE_ON_SIZE":
                server.exec_query("SET @@GLOBAL.audit_log_rotate_on_size = %s"
                                  % command_value)
        finally:
            server.disconnect()

        return True
