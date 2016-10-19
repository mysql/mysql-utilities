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
This file contains the reporting mechanisms for reporting disk usage.
"""
import getpass
import os
import shlex
import subprocess
import sys
import tempfile
import time

from collections import defaultdict, namedtuple
from itertools import chain

from mysql.connector.errorcode import (ER_ACCESS_DENIED_ERROR,
                                       CR_CONNECTION_ERROR,
                                       CR_CONN_HOST_ERROR)
from mysql.utilities.exception import UtilError
from mysql.utilities.common.format import print_list
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.tools import get_tool_path, get_mysqld_version
from mysql.utilities.common.server import (connect_servers,
                                           get_connection_dictionary,
                                           get_local_servers,
                                           Server, test_connect)

log_file_tuple = namedtuple('log_file_tuple',
                            "log_name log_file log_file_size")

_LOG_FILES_VARIABLES = {
    'error log': log_file_tuple('log_error', None, 'log_error_file_size'),
    'general log': log_file_tuple('general_log', 'general_log_file',
                                  'general_log_file_size'),
    'slow query log': log_file_tuple('slow_query_log', 'slow_query_log_file',
                                     'slow_query_log_file_size')
}

_SERVER_VARIABLES = ['version', 'datadir', 'basedir', 'plugin_dir']


_COLUMNS = ['server', 'config_file', 'binary_log', 'binary_log_pos',
            'relay_log', 'relay_log_pos']

_WARNING_TEMPLATE = ("Unable to get information about '{0}' size. Please "
                     "check if the file '{1}' exists or if you have the "
                     "necessary Operating System permissions to access it.")

# Add the values from server variables to the _COLUMNS list
_COLUMNS.extend(_SERVER_VARIABLES)

# Retrieve column names from the _LOG_FILES_VARIABLES, filter the
# None value, sort them alphabetically and add them to the  _COLUMNS list
_COLUMNS.extend(
    sorted(val for val in chain(
        *_LOG_FILES_VARIABLES.values()) if val is not None)
)

# Used to get O(1) performance in checking if an item is already present
# in _COLUMNS
_COLUMNS_SET = set(_COLUMNS)


def _get_binlog(server):
    """Retrieve binary log and binary log position

    server[in]        Server instance

    Returns tuple (binary log, binary log position)
    """
    binlog, binlog_pos = '', ''
    res = server.exec_query("SHOW MASTER STATUS")
    if res != [] and res is not None:
        binlog = res[0][0]
        binlog_pos = res[0][1]
    return binlog, binlog_pos


def _get_relay_log(server):
    """Retrieve relay log and relay log position

    server[in]        Server instance

    Returns tuple (relay log, relay log position)
    """
    relay_log, relay_log_pos = '', ''
    res = server.exec_query("SHOW SLAVE STATUS")
    if res != [] and res is not None:
        relay_log = res[0][7]
        relay_log_pos = res[0][8]
    return relay_log, relay_log_pos


def _server_info(server_val, get_defaults=False, options=None):
    """Show information about a running server

    This method gathers information from a running server. This information is
    returned as a tuple to be displayed to the user in a format specified. The
    information returned includes the following:

    * server connection information
    * version number of the server
    * data directory path
    * base directory path
    * plugin directory path
    * configuration file location and name
    * current binary log file
    * current binary log position
    * current relay log file
    * current relay log position

    server_val[in]    the server connection values or a connected server
    get_defaults[in]  if True, get the default settings for the server
    options[in]       options for connecting to the server

    Return tuple - information about server
    """
    if options is None:
        options = {}
    # Parse source connection values
    source_values = parse_connection(server_val, None, options)

    # Connect to the server
    conn_options = {
        'version': "5.1.30",
    }
    servers = connect_servers(source_values, None, conn_options)
    server = servers[0]

    params_dict = defaultdict(str)

    # Initialize list of warnings
    params_dict['warnings'] = []

    # Identify server by string: 'host:port[:socket]'.
    server_id = "{0}:{1}".format(server.host, server.port)
    if source_values.get('socket', None):
        server_id = "{0}:{1}".format(server_id, source_values.get('socket'))
    params_dict['server'] = server_id

    # Get _SERVER_VARIABLES values from the server
    for server_var in _SERVER_VARIABLES:
        res = server.show_server_variable(server_var)
        if res:
            params_dict[server_var] = res[0][1]
        else:
            raise UtilError("Unable to determine {0} of server '{1}'"
                            ".".format(server_var, server_id))

    # Verify if the server is a local server.
    server_is_local = server.is_alias('localhost')

    # Get _LOG_FILES_VARIABLES values from the server
    for msg, log_tpl in _LOG_FILES_VARIABLES.iteritems():
        res = server.show_server_variable(log_tpl.log_name)
        if res:
            # Check if log is turned off
            params_dict[log_tpl.log_name] = res[0][1]
            # If logs are turned off, skip checking information about the file
            if res[0][1] in ('', 'OFF'):
                continue

            # Logging is enabled, so we can get get information about log_file
            # unless it is log_error because in that case we already have it.
            if log_tpl.log_file is not None:  # if it is not log_error
                log_file = server.show_server_variable(
                    log_tpl.log_file)[0][1]
                params_dict[log_tpl.log_file] = log_file
            else:  # log error, so log_file_name is already on params_dict
                log_file = params_dict[log_tpl.log_name]

            # Size can only be obtained from the files of a local server.
            if not server_is_local:
                params_dict[log_tpl.log_file_size] = 'UNAVAILABLE'
                # Show warning about log size unaviable.
                params_dict['warnings'].append("Unable to get information "
                                               "regarding variable '{0}' "
                                               "from a remote server."
                                               "".format(msg))
            # If log file is stderr, we cannot get the correct size.
            elif log_file in ["stderr", "stdout"]:
                params_dict[log_tpl.log_file_size] = 'UNKNOWN'
                # Show warning about log unknown size.
                params_dict['warnings'].append("Unable to get size information"
                                               " from '{0}' for '{1}'."
                                               "".format(log_file, msg))
            else:
                # Now get the information about the size of the logs
                try:
                    # log_file might be a relative path, in which case we need
                    # to prepend the datadir path to it
                    if not os.path.isabs(log_file):
                        log_file = os.path.join(params_dict['datadir'],
                                                log_file)
                    params_dict[log_tpl.log_file_size] = "{0} bytes".format(
                        os.path.getsize(log_file))
                except os.error:
                    # if we are unable to get the log_file_size
                    params_dict[log_tpl.log_file_size] = ''
                    warning_msg = _WARNING_TEMPLATE.format(msg, log_file)
                    params_dict['warnings'].append(warning_msg)

        else:
            params_dict['warnings'].append(
                "Unable to get information regarding variable '{0}'"
            ).format(msg)

    # if audit_log plugin is installed and enabled
    if server.supports_plugin('audit'):
        res = server.show_server_variable('audit_log_file')
        if res:
            # Audit_log variable might be a relative path to the datadir,
            # so it needs to be treated accordingly
            if not os.path.isabs(res[0][1]):
                params_dict['audit_log_file'] = os.path.join(
                    params_dict['datadir'], res[0][1])
            else:
                params_dict['audit_log_file'] = res[0][1]

            # Add audit_log field to the _COLUMNS List unless it is already
            # there
            if 'audit_log_file' not in _COLUMNS_SET:
                _COLUMNS.append('audit_log_file')
                _COLUMNS.append('audit_log_file_size')
                _COLUMNS_SET.add('audit_log_file')
            try:
                params_dict['audit_log_file_size'] = "{0} bytes".format(
                    os.path.getsize(params_dict['audit_log_file']))

            except os.error:
                # If we are unable to get the size of the audit_log_file
                params_dict['audit_log_file_size'] = ''
                warning_msg = _WARNING_TEMPLATE.format(
                    "audit log",
                    params_dict['audit_log_file']
                )
                params_dict['warnings'].append(warning_msg)

    # Build search path for config files
    if os.name == "posix":
        my_def_search = ["/etc/my.cnf", "/etc/mysql/my.cnf",
                         os.path.join(params_dict['basedir'], "my.cnf"),
                         "~/.my.cnf"]
    else:
        my_def_search = [r"c:\windows\my.ini", r"c:\my.ini", r"c:\my.cnf",
                         os.path.join(os.curdir, "my.ini")]
    my_def_search.append(os.path.join(os.curdir, "my.cnf"))

    # Get server's default configuration values.
    defaults = []
    if get_defaults:
        # Can only get defaults for local servers (need to access local data).
        if server_is_local:
            try:
                my_def_path = get_tool_path(params_dict['basedir'],
                                            "my_print_defaults", quote=True)
            except UtilError as err:
                raise UtilError("Unable to retrieve the defaults data "
                                "(requires access to my_print_defaults): {0} "
                                "(basedir: {1})"
                                "".format(err.errmsg, params_dict['basedir']))
            out_file = tempfile.TemporaryFile()
            # Execute tool: <basedir>/my_print_defaults mysqld
            cmd_list = shlex.split(my_def_path)
            cmd_list.append("mysqld")
            subprocess.call(cmd_list, stdout=out_file)
            out_file.seek(0)
            # Get defaults data from temp output file.
            defaults.append("\nDefaults for server {0}".format(server_id))
            for line in out_file.readlines():
                defaults.append(line.rstrip())
        else:
            # Remote server; Cannot get the defaults data.
            defaults.append("\nWARNING: The utility can not get defaults from "
                            "a remote host.")

    # Find config file
    config_file = ""
    for search_path in my_def_search:
        if os.path.exists(search_path):
            if len(config_file) > 0:
                config_file = "{0}, {1}".format(config_file, search_path)
            else:
                config_file = search_path
    params_dict['config_file'] = config_file

    # Find binary log, relay log
    params_dict['binary_log'], params_dict['binary_log_pos'] = _get_binlog(
        server)
    params_dict['relay_log'], params_dict['relay_log_pos'] = _get_relay_log(
        server)

    server.disconnect()

    return params_dict, defaults


def _start_server(server_val, basedir, datadir, options=None):
    """Start an instance of a server in read only mode

    This method is used to start the server in read only mode. It will launch
    the server with --skip-grant-tables and --read_only options set.

    Caller must stop the server with _stop_server().

    server_val[in]    dictionary of server connection values
    basedir[in]       the base directory for the server
    datadir[in]       the data directory for the server
    options[in]       dictionary of options (verbosity)
    """
    if options is None:
        options = {}
    verbosity = options.get("verbosity", 0)
    start_timeout = options.get("start_timeout", 10)

    mysqld_path = get_tool_path(basedir, "mysqld", quote=True)

    print "# Server is offline."

    # Check server version
    print "# Checking server version ...",
    version = get_mysqld_version(mysqld_path)
    print "done."
    if version is not None and int(version[0]) >= 5:
        post_5_5 = int(version[1]) >= 5
        post_5_6 = int(version[1]) >= 6
        post_5_7_4 = int(version[1]) >= 7 and int(version[2]) > 4
    else:
        print("# Warning: cannot get server version.")
        post_5_5 = False
        post_5_6 = False
        post_5_7_4 = False

    # Get the user executing the utility to use in the mysqld options.
    # Note: the option --user=user_name is mandatory to start mysqld as root.
    user_name = getpass.getuser()

    # Start the instance
    if verbosity > 0:
        print "# Starting read-only instance of the server ..."
        print "# --- BEGIN (server output) ---"
    else:
        print "# Starting read-only instance of the server ...",
    args = shlex.split(mysqld_path)
    args.extend([
        "--no-defaults",
        "--skip-grant-tables",
        "--read_only",
        "--port=%(port)s" % server_val,
        "--basedir=" + basedir,
        "--datadir=" + datadir,
        "--user={0}".format(user_name),
    ])

    # It the server is 5.6 or later, we must use additional parameters
    if post_5_5:
        server_args = [
            "--skip-slave-start",
            "--default-storage-engine=MYISAM",
            "--server-id=0",
        ]
        if post_5_6:
            server_args.append("--default-tmp-storage-engine=MYISAM")
        if not post_5_7_4:
            server_args.append("--skip-innodb")
        args.extend(server_args)

    socket = server_val.get('unix_socket', None)
    if not socket and post_5_7_4 and os.name == "posix":
        socket = os.path.normpath(os.path.join(datadir, "mysql.sock"))
    if socket is not None:
        args.append("--socket={0}".format(socket))
    if verbosity > 0:
        subprocess.Popen(args, shell=False)
    else:
        out = open(os.devnull, 'w')
        subprocess.Popen(args, shell=False, stdout=out, stderr=out)

    server_options = {
        'conn_info': server_val,
        'role': "read_only",
    }
    server = Server(server_options)

    # Try to connect to the server, waiting for the server to become ready
    # (retry start_timeout times and wait 1 sec between each attempt).
    # Note: It can take up to 10 seconds for Windows machines.
    i = 0
    while i < start_timeout:
        # Reset error and wait 1 second.
        error = None
        time.sleep(1)
        try:
            server.connect()
            break  # Server ready (connect succeed)! Exit the for loop.
        except UtilError as err:
            # Store exception to raise later (if needed).
            error = err
        i += 1

    # Indicate end of the server output.
    if verbosity > 0:
        print "# --- END (server output) ---"

    # Raise last known exception (if unable to connect to the server)
    if error:
        # See: http://www.logilab.org/ticket/3207
        # pylint: disable=E0702
        raise error

    if verbosity > 0:
        print "# done (server started)."
    else:
        print "done."

    return server


def _stop_server(server_val, basedir, options=None):
    """Stop an instance of a server started in read only mode

    This method is used to stop the server started in read only mode. It will
    launch mysqladmin to stop the server.

    Caller must start the server with _start_server().

    server_val[in]    dictionary of server connection values
    basedir[in]       the base directory for the server
    options[in]       dictionary of options (verbosity)
    """
    if options is None:
        options = {}
    verbosity = options.get("verbosity", 0)
    socket = server_val.get("unix_socket", None)
    mysqladmin_path = get_tool_path(basedir, "mysqladmin", quote=True)

    # Stop the instance
    if verbosity > 0:
        print "# Shutting down server ..."
        print "# --- BEGIN (server output) ---"
    else:
        print "# Shutting down server ...",

    if os.name == "posix":
        cmd = mysqladmin_path + " shutdown -uroot "
        if socket is not None:
            cmd = cmd + " --socket=%s " % socket
    else:
        cmd = mysqladmin_path + " shutdown -uroot " + \
            " --port=%(port)s" % server_val
    if verbosity > 0:
        proc = subprocess.Popen(cmd, shell=True)
    else:
        fnull = open(os.devnull, 'w')
        proc = subprocess.Popen(cmd, shell=True,
                                stdout=fnull, stderr=fnull)
    # Wait for subprocess to finish
    proc.wait()

    if verbosity > 0:
        print "# --- END (server output) ---"
        print "# done (server stopped)."
    else:
        print "done."


def _show_running_servers(start=3306, end=3333):
    """Display a list of running MySQL servers.

    start[in]         starting port for Windows servers
    end[in]           ending port for Windows servers
    """
    print "# "
    processes = get_local_servers(True, start, end)
    if len(processes) > 0:
        print "# The following MySQL servers are active on this host:"
        for process in processes:
            if os.name == "posix":
                print "#  Process id: %6d, Data path: %s" % \
                    (int(process[0]), process[1])
            elif os.name == "nt":
                print "#  Process id: %6d, Port: %s" % \
                      (int(process[0]), process[1])
    else:
        print "# No active MySQL servers found."
    print "# "


def show_server_info(servers, options):
    """Show server information for a list of servers

    This method will gather information about a running server. If the
    show_defaults option is specified, the method will also read the
    configuration file and return a list of the server default settings.

    If the format option is set, the output will be in the format specified.

    If the no_headers option is set, the output will not have a header row (no
    column names) except for format = vertical.

    If the basedir and start options are set, the method will attempt to start
    the server in read only mode to get the information. Specifying only
    basedir will not start the server. The extra start option is designed to
    make sure the user wants to start the offline server. The user may not wish
    to do this if there are certain error conditions and/or logs in place that
    may be overwritten.

    servers[in]       list of server connections in the form
                      <user>:<password>@<host>:<port>:<socket>
    options[in]       dictionary of options (no_headers, format, basedir,
                      start, show_defaults)

    Returns tuple ((server information), defaults)
    """
    no_headers = options.get("no_headers", False)
    fmt = options.get("format", "grid")
    show_defaults = options.get("show_defaults", False)
    basedir = options.get("basedir", None)
    datadir = options.get("datadir", None)
    start = options.get("start", False)
    show_servers = options.get("show_servers", 0)

    if show_servers:
        if os.name == 'nt':
            ports = options.get("ports", "3306:3333")
            start_p, end_p = ports.split(":")
            _show_running_servers(start_p, end_p)
        else:
            _show_running_servers()
        # Don't continue unless at least one server is specified.
        if not servers:
            return

    ssl_dict = {}
    ssl_dict['ssl_cert'] = options.get("ssl_cert", None)
    ssl_dict['ssl_ca'] = options.get("ssl_ca", None)
    ssl_dict['ssl_key'] = options.get("ssl_key", None)
    ssl_dict['ssl'] = options.get("ssl", None)

    row_dict_lst = []
    warnings = []
    server_val = {}
    for server in servers:
        new_server = None
        try:
            test_connect(server, throw_errors=True, ssl_dict=ssl_dict)
        except UtilError as util_error:
            conn_dict = get_connection_dictionary(server, ssl_dict=ssl_dict)
            server1 = Server(options={'conn_info': conn_dict})
            server_is_off = False
            # If we got errno 2002 it means can not connect through the
            # given socket.
            if util_error.errno == CR_CONNECTION_ERROR:
                socket = conn_dict.get("unix_socket", "")
                if socket:
                    msg = ("Unable to connect to server using socket "
                           "'{0}'.".format(socket))
                    if os.path.isfile(socket):
                        err_msg = ["{0} Socket file is not valid.".format(msg)]
                    else:
                        err_msg = ["{0} Socket file does not "
                                   "exist.".format(msg)]
            # If we got errno 2003 and we do not have
            # socket, instead we check if server is localhost.
            elif (util_error.errno == CR_CONN_HOST_ERROR and
                  server1.is_alias("localhost")):
                server_is_off = True
            # If we got errno 1045 it means Access denied,
            # notify the user if a password was used or not.
            elif util_error.errno == ER_ACCESS_DENIED_ERROR:
                use_pass = 'YES' if conn_dict['passwd'] else 'NO'
                err_msg = ["Access denied for user '{0}'@'{1}' using "
                           "password: {2}".format(conn_dict['user'],
                                                  conn_dict['host'],
                                                  use_pass)]
            # Use the error message from the connection attempt.
            else:
                err_msg = [util_error.errmsg]
            # To propose to start a cloned server for extract the info,
            # can not predict if the server is really off, but we can do it
            # in case of socket error, or if one of the related
            # parameter was given.
            if server_is_off or basedir or datadir or start:
                err_msg = ["Server is offline. To connect, "
                           "you must also provide "]

                opts = ["basedir", "datadir", "start"]
                for opt in tuple(opts):
                    try:
                        if locals()[opt] is not None:
                            opts.remove(opt)
                    except KeyError:
                        pass
                if opts:
                    err_msg.append(", ".join(opts[0:-1]))
                    if len(opts) > 1:
                        err_msg.append(" and the ")
                    err_msg.append(opts[-1])
                    err_msg.append(" option")
                    raise UtilError("".join(err_msg))

            if not start:
                raise UtilError("".join(err_msg))
            else:
                try:
                    server_val = parse_connection(server, None, options)
                except:
                    raise UtilError("Source connection values invalid"
                                    " or cannot be parsed.")
                new_server = _start_server(server_val, basedir,
                                           datadir, options)
        info_dict, defaults = _server_info(server, show_defaults, options)
        warnings.extend(info_dict['warnings'])
        if info_dict:
            row_dict_lst.append(info_dict)
        if new_server:
            # Need to stop the server!
            new_server.disconnect()
            _stop_server(server_val, basedir, options)

    # Get the row values stored in the dictionaries
    rows = [[row_dict[key] for key in _COLUMNS] for row_dict in row_dict_lst]

    print_list(sys.stdout, fmt, _COLUMNS, rows, no_headers)
    if warnings:
        print("\n# List of Warnings: \n")
        for warning in warnings:
            print("WARNING: {0}\n".format(warning))

    # Print the default configurations.
    if show_defaults and len(defaults) > 0:
        for row in defaults:
            print("  {0}".format(row))
