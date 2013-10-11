#
# Copyright (c) 2011, 2013, Oracle and/or its affiliates. All rights reserved.
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

import os
import re
import subprocess
import sys
import tempfile
import time

from mysql.utilities.exception import UtilError
from mysql.utilities.common.format import print_list
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.tools import get_tool_path, get_mysqld_version
from mysql.utilities.common.server import (connect_servers, get_local_servers,
                                           Server, test_connect)


_COLUMNS = ['server', 'version', 'datadir', 'basedir', 'plugin_dir',
            'config_file', 'binary_log', 'binary_log_pos', 'relay_log',
            'relay_log_pos']


def _get_binlog(server):
    """Retrieve binary log and binary log position

    server[in]        Server instance

    Returns tuple (binary log, binary log position)
    """
    binlog = None
    binlog_pos = None
    res = server.exec_query("SHOW MASTER STATUS")
    if res != [] and res is not None:
        binlog = res[0][0]
        binlog_pos = res[0][1]
    return (binlog, binlog_pos)


def _get_relay_log(server):
    """Retrieve relay log and relay log position

    server[in]        Server instance

    Returns tuple (relay log, relay log position)
    """
    relay_log = None
    relay_log_pos = None
    res = server.exec_query("SHOW SLAVE STATUS")
    if res != [] and res is not None:
        relay_log = res[0][7]
        relay_log_pos = res[0][8]
    return (relay_log, relay_log_pos)


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

    rows = server.exec_query("SHOW VARIABLES LIKE 'basedir'")
    if rows:
        basedir = rows[0][1]
    else:
        raise UtilError("Unable to determine basedir of running server.")

    if os.name == "posix":
        my_def_search = ["/etc/my.cnf", "/etc/mysql/my.cnf",
                         os.path.join(basedir, "my.cnf"), "~/.my.cnf"]
    else:
        my_def_search = [r"c:\windows\my.ini", r"c:\my.ini", r"c:\my.cnf",
                         os.path.join(os.curdir, "my.ini")]
    my_def_search.append(os.path.join(os.curdir, "my.cnf"))

    # Identify server by string: 'host:port[:socket]'.
    server_id = "{0}:{1}".format(source_values['host'], source_values['port'])
    if source_values.get('socket', None):
        server_id = "{0}:{1}".format(server_id, source_values.get('socket'))

    # Get server's default configuration values.
    defaults = []
    if get_defaults:
        # Can only get defaults for local servers (need to access local data).
        if server.is_alias('localhost'):
            try:
                my_def_path = get_tool_path(basedir, "my_print_defaults")
            except UtilError as err:
                raise UtilError("Unable to retrieve the defaults data "
                                "(requires access to my_print_defaults): {0} "
                                "(basedir: {1})".format(err.errmsg, basedir))
            out_file = tempfile.TemporaryFile()
            # Execute tool: <basedir>/my_print_defaults mysqld
            subprocess.call([my_def_path, "mysqld"], stdout=out_file)
            out_file.seek(0)
            # Get defaults data from temp output file.
            defaults.append("\nDefaults for server {0}".format(server_id))
            for line in out_file.readlines():
                defaults.append(line.rstrip())
        else:
            # Remote server; Cannot get the defaults data.
            defaults.append("\nWARNING: The utility can not get defaults from "
                            "a remote host.")

    # Get server version
    try:
        res = server.show_server_variable('version')
        version = res[0][1]
    except:
        raise UtilError("Cannot get version for server " + server_id)

    # Find config file
    config_file = ""
    for search_path in my_def_search:
        if os.path.exists(search_path):
            if len(config_file) > 0:
                config_file = "{0}, {1}".format(config_file, search_path)
            else:
                config_file = search_path

    # Find datadir, basedir, plugin-dir, binary log, relay log
    res = server.show_server_variable("datadir")
    datadir = res[0][1]
    res = server.show_server_variable("basedir")
    basedir = res[0][1]
    res = server.show_server_variable("plugin_dir")
    plugin_dir = res[0][1]
    binlog, binlog_pos = _get_binlog(server)
    relay_log, relay_log_pos = _get_relay_log(server)
    server.disconnect()

    return ((server_id, version, datadir, basedir, plugin_dir, config_file,
             binlog, binlog_pos, relay_log, relay_log_pos), defaults)


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

    mysqld_path = get_tool_path(basedir, "mysqld")

    print "# Server is offline."

    # Check server version
    print "# Checking server version ...",
    version = get_mysqld_version(mysqld_path)
    print "done."
    post_5_6 = version is not None and \
        int(version[0]) >= 5 and int(version[1]) >= 6

    # Start the instance
    print "# Starting read-only instance of the server ...",
    args = [
        "--no-defaults",
        "--skip-grant-tables",
        "--read_only",
        "--port=%(port)s" % server_val,
        "--basedir=" + basedir,
        "--datadir=" + datadir,
    ]

    # It the server is 5.6 or later, we must use additional parameters
    if post_5_6:
        args_5_6 = [
            "--skip-slave-start",
            "--skip-innodb",
            "--default-storage-engine=MYISAM",
            "--default-tmp-storage-engine=MYISAM",
            "--server-id=0",
        ]
        args.extend(args_5_6)
    args.insert(0, mysqld_path)

    socket = server_val.get('unix_socket', None)
    if socket is not None:
        args.append("--socket=%(unix_socket)s" % server_val)
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
    # Raise last known exception (if unable to connect to the server)
    if error:
        raise error  # pylint: disable=E0702
                     # See: http://www.logilab.org/ticket/3207
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
    mysqladmin_path = get_tool_path(basedir, "mysqladmin")
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

    rows = []
    server_val = {}
    for server in servers:
        new_server = None
        try:
            test_connect(server, True)
        except UtilError as util_error:
            if util_error.errmsg.startswith("Server connection "
                                            "values invalid:"):
                raise util_error
            # If we got an exception it may means that the server is offline
            # in that case we will try to turn a clone to extract the info
            # if the user passed the necessary parameters.
            pattern = r".*?: (.*?)\((.*)\)"
            res = re.match(pattern, util_error.errmsg, re.S)
            if not res:
                er = ["error: <%s>" % util_error.errmsg]
            else:
                er = res.groups()

            if (re.search("refused", "".join(er)) or
               re.search("Can't connect to local MySQL server through socket",
                         "".join(er)) or
               re.search("Can't connect to MySQL server on", "".join(er))):
                er = ["Server is offline. To connect, "
                      "you must also provide "]

                opts = ["basedir", "datadir", "start"]
                for opt in tuple(opts):
                    try:
                        if locals()[opt] is not None:
                            opts.remove(opt)
                    except KeyError:
                        pass
                if opts:
                    er.append(", ".join(opts[0:-1]))
                    if len(opts) > 1:
                        er.append(" and the ")
                    er.append(opts[-1])
                    er.append(" option")
                    raise UtilError("".join(er))

            if not start:
                raise UtilError("".join(er))
            else:
                try:
                    server_val = parse_connection(server, None, options)
                except:
                    raise UtilError("Source connection values invalid"
                                    " or cannot be parsed.")
                new_server = _start_server(server_val, basedir,
                                           datadir, options)

        info, defaults = _server_info(server, show_defaults, options)
        if info:
            rows.append(info)
        if new_server:
            # Need to stop the server!
            new_server.disconnect()
            _stop_server(server_val, basedir, options)

    print_list(sys.stdout, fmt, _COLUMNS, rows, no_headers)

    # Print the default configurations.
    if show_defaults and len(defaults) > 0:
        for row in defaults:
            print("  {0}".format(row))
