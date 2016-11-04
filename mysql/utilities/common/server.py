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
This module contains an abstraction of a MySQL server object used
by multiple utilities. It also contains helper methods for common
server operations used in multiple utilities.
"""

import os
import re
import socket
import string
import subprocess
import tempfile
import threading
import logging

import mysql.connector
from mysql.connector.constants import ClientFlag

from mysql.connector.errorcode import CR_SERVER_LOST
from mysql.utilities.exception import (ConnectionValuesError, UtilError,
                                       UtilDBError, UtilRplError)
from mysql.utilities.common.user import User
from mysql.utilities.common.tools import (delete_directory, execute_script,
                                          ping_host)
from mysql.utilities.common.ip_parser import (parse_connection, hostname_is_ip,
                                              clean_IPv6, format_IPv6)
from mysql.utilities.common.messages import MSG_MYSQL_VERSION


_FOREIGN_KEY_SET = "SET foreign_key_checks = {0}"
_AUTOCOMMIT_SET = "SET AUTOCOMMIT = {0}"
_GTID_ERROR = ("The server %s:%s does not comply to the latest GTID "
               "feature support. Errors:")


def tostr(value):
    """Cast value to str except when None

    value[in]          Value to be cast to str

    Returns value as str instance or None.
    """
    return None if value is None else str(value)


class MySQLUtilsCursorRaw(mysql.connector.cursor.MySQLCursorRaw):
    """
    Cursor for Connector/Python v2.0, returning str instead of bytearray
    """
    def fetchone(self):
        row = self._fetch_row()
        if row:
            return tuple([tostr(v) for v in row])
        return None

    def fetchall(self):
        rows = []
        all_rows = super(MySQLUtilsCursorRaw, self).fetchall()
        for row in all_rows:
            rows.append(tuple([tostr(v) for v in row]))
        return rows


class MySQLUtilsCursorBufferedRaw(
        mysql.connector.cursor.MySQLCursorBufferedRaw):
    """
    Cursor for Connector/Python v2.0, returning str instead of bytearray
    """
    def fetchone(self):
        row = self._fetch_row()
        if row:
            return tuple([tostr(v) for v in row])
        return None

    def fetchall(self):
        if self._rows is None:
            raise mysql.connector.InterfaceError(
                "No result set to fetch from."
            )

        rows = []
        all_rows = [r for r in self._rows[self._next_row:]]
        for row in all_rows:
            rows.append(tuple([tostr(v) for v in row]))
        return rows


def get_connection_dictionary(conn_info, ssl_dict=None):
    """Get the connection dictionary.

    The method accepts one of the following types for conn_info:

        - dictionary containing connection information including:
          (user, passwd, host, port, socket)
        - connection string in the form: user:pass@host:port:socket or
                                         login-path:port:socket
        - an instance of the Server class

    conn_info[in]          Connection information
    ssl_dict[in]           A dictionary with the ssl certificates
                           (ssl_ca, ssl_cert and ssl_key).

    Returns dict - dictionary for connection (user, passwd, host, port, socket)
    """
    if conn_info is None:
        return conn_info

    conn_val = {}
    if isinstance(conn_info, dict) and 'host' in conn_info:
        # Not update conn_info if already has any ssl certificate.
        if (ssl_dict is not None and
                not (conn_info.get("ssl_ca", None) or
                     conn_info.get("ssl_cert", None) or
                     conn_info.get("ssl_key", None) or
                     conn_info.get("ssl", None))):
            conn_info.update(ssl_dict)
        conn_val = conn_info
    elif isinstance(conn_info, Server):
        # get server's dictionary
        conn_val = conn_info.get_connection_values()
    elif isinstance(conn_info, basestring):
        # parse the string
        conn_val = parse_connection(conn_info, options=ssl_dict)
    else:
        raise ConnectionValuesError("Cannot determine connection information"
                                    " type.")

    return conn_val


def set_ssl_opts_in_connection_info(ssl_opts, connection_info):
    """Sets the ssl options in a connection information to be used with C/py.

    ssl_opts[in]           A dictionary with the ssl options (ssl_ca, ssl_cert
                           and ssl_key).
    connection_info[out]   A dictionary to set the ssl options after validate
                           them.

    The ssl options will be set on the connection_info if they are not None.
    In addition the SSL client flags are added if at least one ssl option is
    set.
    """
    # Add SSL parameters ONLY if they are not None
    add_ssl_flag = False
    if ssl_opts.get('ssl_ca') is not None:
        connection_info['ssl_ca'] = ssl_opts.get('ssl_ca')
        add_ssl_flag = True
    if ssl_opts.get('ssl_cert') is not None:
        connection_info['ssl_cert'] = ssl_opts.get('ssl_cert')
        add_ssl_flag = True
    if ssl_opts.get('ssl_key') is not None:
        connection_info['ssl_key'] = ssl_opts.get('ssl_key')
        add_ssl_flag = True
    if ssl_opts.get('ssl'):
        add_ssl_flag = True

    # When at least one of cert, key or ssl options are specified, the ca
    # option is not required for establishing the encrypted connection,
    # but C/py will not allow the None value for the ca option, so we use an
    # empty string i.e '' to avoid an error from C/py about ca option being
    # the None value.
    if ('ssl_cert' in connection_info.keys() or
            'ssl_key' in connection_info.keys() or
            ssl_opts.get('ssl')) and \
            'ssl_ca' not in connection_info.keys():
        connection_info['ssl_ca'] = ''

    # The ca certificate is verified only if the ssl option is also specified.
    if ssl_opts.get('ssl') and connection_info['ssl_ca']:
        connection_info['ssl_verify_cert'] = True

    if add_ssl_flag:
        cpy_flags = [ClientFlag.SSL,
                     ClientFlag.SSL_VERIFY_SERVER_CERT]
        connection_info['client_flags'] = cpy_flags


def _print_connection(prefix, conn_info):
    """Print connection information

    The method accepts one of the following types for conn_info:

        - dictionary containing connection information including:
          (user, passwd, host, port, socket)
        - connection string in the form: user:pass@host:port:socket or
                                         login-path:port:socket
        - an instance of the Server class

    conn_info[in]          Connection information
    """
    conn_val = get_connection_dictionary(conn_info)
    print "# %s on %s: ..." % (prefix, conn_val["host"]),


def get_local_servers(all_proc=False, start=3306, end=3333,
                      datadir_prefix=None):
    """Check to see if there are any servers running on the local host.

    This method attempts to locate all running servers. If provided, it will
    also limit the search to specific ports of datadirectory prefixes.

    This method uses ps for posix systems and netstat for Windows machines
    to determine the list of running servers.

    For posix, it matches on the datadir and if datadir is the path for the
    test directory, the server will be added to the list.

    For nt, it matches on the port in the range starting_port,
    starting_port + 10.

    all_proc[in]        If True, find all processes else only user processes
    start[in]           For Windows/NT systems: Starting port value to search.
                        Default = 3306
    end[in]             For Windows/NT systems: Ending port value to search.
                        Default = 3333
    datadir_prefix[in]  For posix systems, if not None, find only those servers
                        whose datadir starts with this prefix.

    Returns list - tuples of the form: (process_id, [datadir|port])
    """
    processes = []
    if os.name == "posix":
        tmp_file = tempfile.TemporaryFile()
        if all_proc:
            subprocess.call(["ps", "-A"], stdout=tmp_file)
        else:
            subprocess.call(["ps", "-f"], stdout=tmp_file)
        tmp_file.seek(0)
        for line in tmp_file.readlines():
            mysqld_safe = False
            mysqld = False
            datadir = False
            grep = False
            datadir_arg = ""
            proginfo = string.split(line)
            for arg in proginfo:
                if "datadir" in arg:
                    datadir = True
                    datadir_arg = arg
                if "mysqld" in arg:
                    mysqld = True
                if "mysqld_safe" in arg:
                    mysqld_safe = True
                if "grep" in arg:
                    grep = True
            # Check to see if this is a mysqld server and not mysqld_safe proc
            if ((mysqld and datadir) or (mysqld and not grep)) and \
               not mysqld_safe:
                # If provided, check datadir prefix
                if all_proc:
                    proc_id = proginfo[0]
                else:
                    proc_id = proginfo[1]
                if datadir_prefix is not None:
                    if datadir_prefix in datadir_arg:
                        processes.append((proc_id, datadir_arg[10:]))
                else:
                    processes.append((proc_id, datadir_arg[10:]))
    elif os.name == "nt":
        f_out = open("portlist", 'w+')
        execute_script("netstat -anop tcp", "portlist")
        f_out = open("portlist", 'r')
        for line in f_out.readlines():
            proginfo = string.split(line)
            if proginfo:
                # Look for port on either local or foreign address
                port = proginfo[1][proginfo[1].find(":") + 1:]
                if proginfo[1][0] == '0' and port.isdigit():
                    if int(port) >= int(start) and int(port) <= int(end):
                        processes.append((proginfo[4], port))
                        break
                if len(proginfo) > 2:
                    port = proginfo[2][proginfo[2].find(":") + 1:]
                    if port.isdigit() and \
                       int(port) >= int(start) and int(port) <= int(end):
                        processes.append((proginfo[4], port))
                        break
        f_out.close()
        os.unlink("portlist")
    return processes


def get_server(name, values, quiet, verbose=False):
    """Connect to a server and return Server instance

    If the name is 'master' or 'slave', the connection will be made via the
    Master or Slave class else a normal Server class shall be used.

    name[in]        Name of the server.
    values[in]      Dictionary of connection values.
    quiet[in]       If True, do not print messages.
    verbose[in]     Verbose value used by the returned server instances.
                    By default False.

    Returns Server class instance
    """
    from mysql.utilities.common.replication import Master, Slave

    server_conn = None

    # Try to connect to the MySQL database server.
    if not quiet:
        _print_connection(name, values)

    server_options = {
        'conn_info': values,
        'role': name,
        'verbose': verbose,
    }
    if name.lower() == 'master':
        server_conn = Master(server_options)
    elif name.lower() == 'slave':
        # pylint: disable=R0204
        server_conn = Slave(server_options)
    else:
        # pylint: disable=R0204
        server_conn = Server(server_options)
    try:
        server_conn.connect()
    except:
        if not quiet:
            print("")
        raise

    return server_conn


def _require_version(server, version):
    """Check version of server

    server[in]         Server instance
    version[in]        minimal version of the server required

    Returns boolean - True = version Ok, False = version < required
    """
    if version is not None and server is not None:
        major, minor, rel = version.split(".")
        if not server.check_version_compat(major, minor, rel):
            return False
    return True


def get_server_state(server, host, pingtime=3, verbose=False):
    """Return the state of the server.

    This method returns one of the following states based on the
    criteria shown.

      UP   - server is connected
      WARN - server is not connected but can be pinged
      DOWN - server cannot be pinged nor is connected

    server[in]     Server class instance
    host[in]       host name to ping if server is not connected
    pingtime[in]   timeout in seconds for ping operation
                   Default = 3 seconds
    verbose[in]    if True, show ping status messages
                   Default = False

    Returns string - state
    """
    if verbose:
        print "# Attempting to contact %s ..." % host,
    if server is not None and server.is_alive():
        if verbose:
            print "Success"
        return "UP"
    elif ping_host(host, pingtime):
        if verbose:
            print "Server is reachable"
        return "WARN"
    if verbose:
        print "FAIL"
    return "DOWN"


def connect_servers(src_val, dest_val, options=None):
    """Connect to a source and destination server.

    This method takes two groups of --server=user:password@host:port:socket
    values and attempts to connect one as a source connection and the other
    as the destination connection. If the source and destination are the
    same server and the unique parameter is False, destination is set to None.

    The method accepts one of the following types for the src_val and dest_val:

        - dictionary containing connection information including:
          (user, passwd, host, port, socket)
        - connection string in the form: user:pass@host:port:socket or
                                         login-path:port:socket or
                                         config-path[group]
        - an instance of the Server class

    src_val[in]        source connection information
    dest_val[in]       destination connection information
    options[in]        options to control behavior:
        quiet          do not print any information during the operation
                       (default is False)
        version        if specified (default is None), perform version
                       checking and fail if server version is < version
                       specified - an exception is raised
        src_name       name to use for source server
                       (default is "Source")
        dest_name      name to use for destination server
                       (default is "Destination")
        unique         if True, servers must be different when dest_val is
                       not None (default is False)
        verbose        Verbose value used by the returned server instances
                       (default is False).

    Returns tuple (source, destination) where
            source = connection to source server
            destination = connection to destination server (set to None)
                          if source and destination are same server
            if error, returns (None, None)
    """
    if options is None:
        options = {}
    quiet = options.get("quiet", False)
    src_name = options.get("src_name", "Source")
    dest_name = options.get("dest_name", "Destination")
    version = options.get("version", None)
    charset = options.get("charset", None)
    verbose = options.get('verbose', False)

    ssl_dict = {}
    if options.get("ssl_cert", None) is not None:
        ssl_dict['ssl_cert'] = options.get("ssl_cert")
    if options.get("ssl_ca", None) is not None:
        ssl_dict['ssl_ca'] = options.get("ssl_ca", None)
    if options.get("ssl_key", None) is not None:
        ssl_dict['ssl_key'] = options.get("ssl_key", None)
    if options.get("ssl", None) is not None:
        ssl_dict['ssl'] = options.get("ssl", None)

    source = None
    destination = None

    # Get connection dictionaries
    src_dict = get_connection_dictionary(src_val, ssl_dict)
    if "]" in src_dict['host']:
        src_dict['host'] = clean_IPv6(src_dict['host'])
    dest_dict = get_connection_dictionary(dest_val)
    if dest_dict and "]" in dest_dict['host']:
        dest_dict['host'] = clean_IPv6(dest_dict['host'])

    # Add character set
    if src_dict and charset:
        src_dict["charset"] = charset
    if dest_dict and charset:
        dest_dict["charset"] = charset

    # Check for uniqueness - dictionary
    if options.get("unique", False) and dest_dict is not None:
        dupes = False
        if "unix_socket" in src_dict and "unix_socket" in dest_dict:
            dupes = (src_dict["unix_socket"] == dest_dict["unix_socket"])
        else:
            dupes = (src_dict["port"] == dest_dict["port"]) and \
                    (src_dict["host"] == dest_dict["host"])
        if dupes:
            raise UtilError("You must specify two different servers "
                            "for the operation.")

    # If we're cloning so use same server for faster copy
    cloning = dest_dict is None or (src_dict == dest_dict)

    # Connect to the source server and check version
    if isinstance(src_val, Server):
        source = src_val
    else:
        source = get_server(src_name, src_dict, quiet, verbose=verbose)
        if not quiet:
            print "connected."
    if not _require_version(source, version):
        raise UtilError("The %s version is incompatible. Utility "
                        "requires version %s or higher." %
                        (src_name, version))

    # If not cloning, connect to the destination server and check version
    if not cloning:
        if isinstance(dest_val, Server):
            destination = dest_val
        else:
            destination = get_server(dest_name, dest_dict, quiet,
                                     verbose=verbose)
            if not quiet:
                print "connected."
        if not _require_version(destination, version):
            raise UtilError("The %s version is incompatible. Utility "
                            "requires version %s or higher." %
                            (dest_name, version))
    elif not quiet and dest_dict is not None and \
            not isinstance(dest_val, Server):
        try:
            _print_connection(dest_name, src_dict)
            print "connected."
        except:
            print("")
            raise
    return (source, destination)


def test_connect(conn_info, throw_errors=False, ssl_dict=None):
    """Test connection to a server.

    The method accepts one of the following types for conn_info:

        - dictionary containing connection information including:
          (user, passwd, host, port, socket)
        - connection string in the form: user:pass@host:port:socket or
                                         login-path:port:socket or
                                         config-path[group]
        - an instance of the Server class

    conn_info[in]          Connection information

    throw_errors           throw any errors found during the test,
                           false by default.
    ssl_dict[in]           A dictionary with the ssl certificates
                           (ssl_ca, ssl_cert and ssl_key).

    Returns True if connection success, False if error
    """
    # Parse source connection values
    try:
        src_val = get_connection_dictionary(conn_info, ssl_dict)
    except Exception as err:
        raise ConnectionValuesError("Server connection values invalid: {0}."
                                    "".format(err))
    try:
        conn_options = {
            'quiet': True,
            'src_name': "test",
            'dest_name': None,
        }
        s = connect_servers(src_val, None, conn_options)
        s[0].disconnect()
    except UtilError:
        if throw_errors:
            raise
        return False
    return True


def get_port(server1_vals):
    """Get the port for a connection using a socket.

    This method attempts to connect to a server to retrieve
    its port. It is used to try and update local connection
    values with a valid port number for servers connected
    via a socket.

    server1_vals[in]   connection dictionary for server1

    Returns string - port for server or None if cannot connect
                     or server is not connected via socket
    """
    socket = server1_vals.get('unix_socket', None)
    if socket:
        try:
            server1 = Server({'conn_info': server1_vals})
            server1.connect()
            port = server1.port
            server1.disconnect()
            return port
        except:
            pass
    return None


def check_hostname_alias(server1_vals, server2_vals):
    """Check to see if the servers are the same machine by host name.

    This method will attempt to compare two servers to see
    if they are the same host and port. However, if either is
    using a unix socket, it will connect to the server and attempt
    so that the port is updated.

    server1_vals[in]   connection dictionary for server1
    server2_vals[in]   connection dictionary for server2

    Returns bool - true = server1 and server2 are the same host
    """
    server1 = Server({'conn_info': server1_vals})
    server2 = Server({'conn_info': server2_vals})
    server1_socket = server1_vals.get('unix_socket', None)
    server2_socket = server1_vals.get('unix_socket', None)
    if server1_socket:
        server1.connect()
        server1.disconnect()
    if server2_socket:
        server2.connect()
        server2.disconnect()

    return (server1.is_alias(server2.host) and
            int(server1.port) == int(server2.port))


def stop_running_server(server, wait=10, drop=True):
    """Stop a running server.

    This method will stop a server using the mysqladmin utility to
    shutdown the server. It also destroys the datadir.

    server[in]          Server instance to clone
    wait[in]            Number of wait cycles for shutdown
                        default = 10
    drop[in]            If True, drop datadir

    Returns - True = server shutdown, False - unknown state or error
    """
    # Nothing to do if server is None
    if server is None:
        return True

    # Build the shutdown command
    res = server.show_server_variable("basedir")
    mysqladmin_client = "mysqladmin"
    if os.name != 'posix':
        mysqladmin_client = "mysqladmin.exe"
    mysqladmin_path = os.path.normpath(os.path.join(res[0][1], "bin",
                                                    mysqladmin_client))
    if not os.path.exists(mysqladmin_path):
        mysqladmin_path = os.path.normpath(os.path.join(res[0][1], "client",
                                                        mysqladmin_client))
    if not os.path.exists(mysqladmin_path) and os.name != 'posix':
        mysqladmin_path = os.path.normpath(os.path.join(res[0][1],
                                                        "client/debug",
                                                        mysqladmin_client))
    if not os.path.exists(mysqladmin_path) and os.name != 'posix':
        mysqladmin_path = os.path.normpath(os.path.join(res[0][1],
                                                        "client/release",
                                                        mysqladmin_client))
    if os.name == 'posix':
        cmd = "'{0}'".format(mysqladmin_path)
    else:
        cmd = '"{0}"'.format(mysqladmin_path)
    if server.socket is None and server.host == 'localhost':
        server.host = '127.0.0.1'
    cmd = "{0} shutdown --user={1} --host={2} ".format(cmd, server.user,
                                                       server.host)
    if server.passwd:
        cmd = "{0} --password={1} ".format(cmd, server.passwd)
    # Use of server socket only works with 'localhost' (not with 127.0.0.1).
    if server.socket and server.host == 'localhost':
        cmd = "{0} --socket={1} ".format(cmd, server.socket)
    else:
        cmd = "{0} --port={1} ".format(cmd, server.port)
    if server.has_ssl:
        if server.ssl_cert is not None:
            cmd = "{0} --ssl-cert={1} ".format(cmd, server.ssl_cert)
        if server.ssl_ca is not None:
            cmd = "{0} --ssl-ca={1} ".format(cmd, server.ssl_ca)
        if server.ssl_key is not None:
            cmd = "{0} --ssl-key={1} ".format(cmd, server.ssl_key)

    res = server.show_server_variable("datadir")
    datadir = os.path.normpath(res[0][1])
    # Kill all connections so shutdown will work correctly
    res = server.exec_query("SHOW PROCESSLIST")
    for row in res:
        if not row[7] or not row[7].upper().startswith("SHOW PROCESS"):
            try:
                server.exec_query("KILL CONNECTION %s" % row[0])
            except UtilDBError:  # Ok to ignore KILL failures
                pass

    # disconnect user
    server.disconnect()

    # Stop the server
    f_null = os.devnull
    f_out = open(f_null, 'w')
    proc = subprocess.Popen(cmd, shell=True,
                            stdout=f_out, stderr=f_out)
    ret_val = proc.wait()
    f_out.close()

    # if shutdown doesn't work, exit.
    if int(ret_val) != 0:
        return False

    # If datadir exists, delete it
    if drop:
        delete_directory(datadir)

    if os.path.exists("cmd.txt"):
        try:
            os.unlink("cmd.txt")
        except:
            pass

    return True


def log_server_version(server, level=logging.INFO):
    """Log server version message.

    This method will log the server version message.
    If no log file is provided it will also print the message to stdout.

    server[in]           Server instance.
    level[in]            Level of message to log. Default = INFO.
    print_version[in]    If True, print the message to stdout. Default = True.
    """
    host_port = "{host}:{port}".format(**get_connection_dictionary(server))
    version_msg = MSG_MYSQL_VERSION.format(server=host_port,
                                           version=server.get_version())
    logging.log(level, version_msg)


class Server(object):
    """The Server class can be used to connect to a running MySQL server.
    The following utilities are provided:

        - Connect to the server
        - Retrieve a server variable
        - Execute a query
        - Return list of all databases
        - Return a list of specific objects for a database
        - Return list of a specific objects for a database
        - Return list of all indexes for a table
        - Read SQL statements from a file and execute
    """

    def __init__(self, options=None):
        """Constructor

        The method accepts one of the following types for options['conn_info']:

            - dictionary containing connection information including:
              (user, passwd, host, port, socket)
            - connection string in the form: user:pass@host:port:socket or
                                             login-path:port:socket
            - an instance of the Server class

        options[in]        options for controlling behavior:
            conn_info      a dictionary containing connection information
                           (user, passwd, host, port, socket)
            role           Name or role of server (e.g., server, master)
            verbose        print extra data during operations (optional)
                           default value = False
            charset        Default character set for the connection.
                           (default None)
        """
        if options is None:
            options = {}

        assert options.get("conn_info") is not None

        self.verbose = options.get("verbose", False)
        self.db_conn = None
        self.host = None
        self.role = options.get("role", "Server")
        self.has_ssl = False
        conn_values = get_connection_dictionary(options.get("conn_info"))
        try:
            self.host = conn_values["host"]
            self.user = conn_values["user"]
            self.passwd = conn_values["passwd"] \
                if "passwd" in conn_values else None
            self.socket = conn_values["unix_socket"] \
                if "unix_socket" in conn_values else None
            self.port = 3306
            if conn_values["port"] is not None:
                self.port = int(conn_values["port"])
            self.charset = options.get("charset",
                                       conn_values.get("charset", None))
            # Optional values
            self.ssl_ca = conn_values.get('ssl_ca', None)
            self.ssl_cert = conn_values.get('ssl_cert', None)
            self.ssl_key = conn_values.get('ssl_key', None)
            self.ssl = conn_values.get('ssl', False)
            if self.ssl_cert or self.ssl_ca or self.ssl_key or self.ssl:
                self.has_ssl = True
        except KeyError:
            raise UtilError("Dictionary format not recognized.")
        self.connect_error = None
        # Set to TRUE when foreign key checks are ON. Check with
        # foreign_key_checks_enabled.
        self.fkeys = None
        self.autocommit = None
        self.read_only = False
        self.aliases = set()
        self.grants_enabled = None
        self._version = None

    @classmethod
    def fromServer(cls, server, conn_info=None):
        """ Create a new server instance from an existing one

        Factory method that will allow the creation of a new server instance
        from an existing server.

        server[in]       instance object that must be instance of the Server
                         class or a subclass.
        conn_info[in]    A dictionary with the connection information to
                         connect to the server

        Returns an instance of the calling class as a result.
        """

        if isinstance(server, Server):
            options = {"role": server.role,
                       "verbose": server.verbose,
                       "charset": server.charset}
            if conn_info is not None and isinstance(conn_info, dict):
                options["conn_info"] = conn_info
            else:
                options["conn_info"] = server.get_connection_values()

            return cls(options)
        else:
            raise TypeError("The server argument's type is neither Server nor "
                            "a subclass of Server")

    def is_alive(self):
        """Determine if connection to server is still alive.

        Returns bool - True = alive, False = error or cannot connect.
        """
        res = True
        try:
            if self.db_conn is None:
                res = False
            else:
                # ping and is_connected only work partially, try exec_query
                # to make sure connection is really alive
                retval = self.db_conn.is_connected()
                if retval:
                    self.exec_query("SHOW DATABASES")
                else:
                    res = False
        except:
            res = False
        return res

    def _update_alias(self, ip_or_hostname, suffix_list):
        """Update list of aliases for the given IP or hostname.

        Gets the list of aliases for host *ip_or_hostname*. If any
        of them matches one of the server's aliases, then update
        the list of aliases (self.aliases). It also receives a list (tuple)
        of suffixes that can be ignored when checking if two hostnames are
        the same.

        ip_or_hostname[in] IP or hostname to test.
        suffix_list[in]    Tuple with list of suffixes that can be ignored.

        Returns True if ip_or_hostname is a server alias, otherwise False.
        """
        host_or_ip_aliases = self._get_aliases(ip_or_hostname)
        host_or_ip_aliases.add(ip_or_hostname)

        # Check if any of aliases matches with one the servers's aliases
        common_alias = self.aliases.intersection(host_or_ip_aliases)
        if common_alias:  # There are common aliases, host is the same
            self.aliases.update(host_or_ip_aliases)
            return True
        else:  # Check with and without suffixes
            no_suffix_server_aliases = set()
            no_suffix_host_aliases = set()

            for suffix in suffix_list:
                # Add alias with and without suffix from self.aliases
                for alias in self.aliases:
                    if alias.endswith(suffix):
                        try:
                            host, _ = alias.rsplit('.', 1)
                            no_suffix_host_aliases.add(host)
                        except:
                            pass  # Ok if parts don't split correctly
                    no_suffix_server_aliases.add(alias)
                # Add alias with and without suffix from host_aliases
                for alias in host_or_ip_aliases:
                    if alias.endswith(suffix):
                        try:
                            host, _ = alias.rsplit('.', 1)
                            no_suffix_host_aliases.add(host)
                        except:
                            pass  # Ok if parts don't split correctly
                    no_suffix_host_aliases.add(alias)
            # Check if there is any alias in common
            common_alias = no_suffix_host_aliases.intersection(
                no_suffix_server_aliases)
            if common_alias:  # Same host, so update self.aliases
                self.aliases.update(
                    no_suffix_host_aliases.union(no_suffix_server_aliases)
                )
                return True

        return False

    def _get_aliases(self, host):
        """Gets the aliases for the given host
        """
        aliases = set([clean_IPv6(host)])
        if hostname_is_ip(clean_IPv6(host)):  # IP address
            try:
                my_host = socket.gethostbyaddr(clean_IPv6(host))
                aliases.add(my_host[0])
                # socket.gethostbyname_ex() does not work with ipv6
                if (my_host[0].count(":") >= 1 or
                        my_host[0] != "ip6-localhost"):
                    host_ip = socket.gethostbyname_ex(my_host[0])
                else:
                    addrinfo = socket.getaddrinfo(my_host[0], None)
                    host_ip = ([socket.gethostbyaddr(addrinfo[0][4][0])],
                               [fiveple[4][0] for fiveple in addrinfo],
                               [addrinfo[0][4][0]])
            except (socket.gaierror, socket.herror,
                    socket.error) as err:
                host_ip = ([], [], [])
                if self.verbose:
                    print("WARNING: IP lookup by address failed for {0},"
                          "reason: {1}".format(host, err.strerror))
        else:
            try:
                # server may not really exist.
                host_ip = socket.gethostbyname_ex(host)
            except (socket.gaierror, socket.herror,
                    socket.error) as err:
                if self.verbose:
                    print("WARNING: hostname: {0} may not be reachable, "
                          "reason: {1}".format(host, err.strerror))
                return aliases
            aliases.add(host_ip[0])
            addrinfo = socket.getaddrinfo(host, None)
            local_ip = None
            error = None
            for addr in addrinfo:
                try:
                    local_ip = socket.gethostbyaddr(addr[4][0])
                    break
                except (socket.gaierror, socket.herror,
                        socket.error) as err:
                    error = err

            if local_ip:
                host_ip = ([local_ip[0]],
                           [fiveple[4][0] for fiveple in addrinfo],
                           [addrinfo[0][4][0]])
            else:
                host_ip = ([], [], [])
                if self.verbose:
                    print("WARNING: IP lookup by name failed for {0},"
                          "reason: {1}".format(host, error.strerror))
        aliases.update(set(host_ip[1]))
        aliases.update(set(host_ip[2]))
        return aliases

    def is_alias(self, host_or_ip):
        """Determine if host_or_ip is an alias for this host

        host_or_ip[in] host or IP number to check

        Returns bool - True = host_or_ip is an alias
        """
        # List of possible suffixes
        suffixes = ('.local', '.lan', '.localdomain')

        host_or_ip = clean_IPv6(host_or_ip.lower())

        # for quickness, verify in the existing aliases, if they exist.
        if self.aliases:
            if host_or_ip.lower() in self.aliases:
                return True
            else:
                # get the alias for the given host_or_ip
                return self._update_alias(host_or_ip, suffixes)

        # no previous aliases information
        # First, get the local information
        hostname_ = socket.gethostname()
        try:
            local_info = socket.gethostbyname_ex(hostname_)
            local_aliases = set([local_info[0].lower()])
            # if dotted host name, take first part and use as an alias
            try:
                local_aliases.add(local_info[0].split('.')[0])
            except:
                pass
            local_aliases.update(['127.0.0.1', 'localhost', '::1', '[::1]'])
            local_aliases.update(local_info[1])
            local_aliases.update(local_info[2])
            local_aliases.update(self._get_aliases(hostname_))
        except (socket.herror, socket.gaierror, socket.error) as err:
            if self.verbose:
                print("WARNING: Unable to find aliases for hostname"
                      " '{0}' reason: {1}".format(hostname_, str(err)))
            # Try with the basic local aliases.
            local_aliases = set(['127.0.0.1', 'localhost', '::1', '[::1]'])

        # Get the aliases for this server host
        self.aliases = self._get_aliases(self.host)

        # Check if this server is local
        for host in self.aliases.copy():
            if host in local_aliases:
                # Is local then save the local aliases for future.
                self.aliases.update(local_aliases)
                break
            # Handle special suffixes in hostnames.
            for suffix in suffixes:
                if host.endswith(suffix):
                    # Remove special suffix and attempt to match with local
                    # aliases.
                    host, _ = host.rsplit('.', 1)
                    if host in local_aliases:
                        # Is local then save the local aliases for future.
                        self.aliases.update(local_aliases)
                        break

        # Check if the given host_or_ip is alias of the server host.
        if host_or_ip in self.aliases:
            return True

        # Check if any of the aliases of ip_or_host is also an alias of the
        # host server.
        return self._update_alias(host_or_ip, suffixes)

    def user_host_exists(self, user, host_or_ip):
        """Check to see if a user, host exists

        This method attempts to see if a user name matches the users on the
        server and that any user, host pair can match the host or IP address
        specified. This attempts to resolve wildcard matches.

        user[in]       user name
        host_or_ip[in] host or IP address

        Returns string - host from server that matches the host_or_ip or
                         None if no match.
        """
        res = self.exec_query("SELECT host FROM mysql.user WHERE user = '%s' "
                              "AND '%s' LIKE host " % (user, host_or_ip))
        if res:
            return res[0][0]
        return None

    def get_connection_values(self):
        """Return a dictionary of connection values for the server.

        Returns dictionary
        """
        conn_vals = {
            "user": self.user,
            "host": self.host
        }
        if self.passwd:
            conn_vals["passwd"] = self.passwd
        if self.socket:
            conn_vals["socket"] = self.socket
        if self.port:
            conn_vals["port"] = self.port
        if self.ssl_ca:
            conn_vals["ssl_ca"] = self.ssl_ca
        if self.ssl_cert:
            conn_vals["ssl_cert"] = self.ssl_cert
        if self.ssl_key:
            conn_vals["ssl_key"] = self.ssl_key
        if self.ssl:
            conn_vals["ssl"] = self.ssl

        return conn_vals

    def connect(self, log_version=False):
        """Connect to server

        Attempts to connect to the server as specified by the connection
        parameters.

        log_version[in]      If True, log server version. Default = False.

        Note: This method must be called before executing queries.

        Raises UtilError if error during connect
        """
        try:
            self.db_conn = self.get_connection()
            if log_version:
                log_server_version(self)
            # If no charset provided, get it from the "character_set_client"
            # server variable.
            if not self.charset:
                res = self.show_server_variable('character_set_client')
                self.db_conn.set_charset_collation(charset=res[0][1])
                self.charset = res[0][1]
            if self.ssl:
                res = self.exec_query("SHOW STATUS LIKE 'Ssl_cipher'")
                if res[0][1] == '':
                    raise UtilError("Can not encrypt server connection.")
            # if we connected via a socket, get the port
            if os.name == 'posix' and self.socket:
                res = self.show_server_variable('port')
                if res:
                    self.port = res[0][1]
        except UtilError:
            # Reset any previous value if the connection cannot be established,
            # before raising an exception. This prevents the use of a broken
            # database connection.
            self.db_conn = None
            raise
        self.connect_error = None
        # Valid values are ON and OFF, not boolean.
        self.read_only = self.show_server_variable("READ_ONLY")[0][1] == "ON"

    def get_connection(self):
        """Return a new connection to the server.

        Attempts to connect to the server as specified by the connection
        parameters and returns a connection object.

        Return the resulting MySQL connection object or raises an UtilError if
        an error occurred during the server connection process.
        """
        try:
            parameters = {
                'user': self.user,
                'host': self.host,
                'port': self.port,
            }
            if self.socket and os.name == "posix":
                parameters['unix_socket'] = self.socket
            if self.passwd and self.passwd != "":
                parameters['passwd'] = self.passwd
            if self.charset:
                parameters['charset'] = self.charset
            parameters['host'] = parameters['host'].replace("[", "")
            parameters['host'] = parameters['host'].replace("]", "")

            # Add SSL parameters ONLY if they are not None
            if self.ssl_ca is not None:
                parameters['ssl_ca'] = self.ssl_ca
            if self.ssl_cert is not None:
                parameters['ssl_cert'] = self.ssl_cert
            if self.ssl_key is not None:
                parameters['ssl_key'] = self.ssl_key

            # When at least one of cert, key or ssl options are specified,
            # the ca option is not required for establishing the encrypted
            # connection, but C/py will not allow the None value for the ca
            # option, so we use an empty string i.e '' to avoid an error from
            # C/py about ca option being the None value.
            if ('ssl_cert' in parameters.keys() or
                    'ssl_key' in parameters.keys() or
                    self.ssl) and \
                    'ssl_ca' not in parameters:
                parameters['ssl_ca'] = ''

            # The ca certificate is verified only if the ssl option is also
            # specified.
            if self.ssl and parameters['ssl_ca']:
                parameters['ssl_verify_cert'] = True

            if self.has_ssl:
                cpy_flags = [ClientFlag.SSL, ClientFlag.SSL_VERIFY_SERVER_CERT]
                parameters['client_flags'] = cpy_flags

            db_conn = mysql.connector.connect(**parameters)
            # Return MySQL connection object.
            return db_conn
        except mysql.connector.Error as err:
            raise UtilError(err.msg, err.errno)
        except AttributeError as err:
            raise UtilError(str(err))

    def disconnect(self):
        """Disconnect from the server.
        """
        try:
            self.db_conn.disconnect()
        except:
            pass

    def get_version(self):
        """Return version number of the server.

        Get the server version. The respective instance variable is set with
        the result after querying the server the first time. The version is
        immediately returned when already known, avoiding querying the server
        at each time.

        Returns string - version string or None if error
        """
        # Return the local version value if already known.
        if self._version:
            return self._version

        # Query the server for its version.
        try:
            res = self.show_server_variable("VERSION")
            if res:
                self._version = res[0][1]
        except UtilError:
            # Ignore errors and return _version, initialized with None.
            pass

        return self._version

    def check_version_compat(self, t_major, t_minor, t_rel):
        """Checks version of the server against requested version.

        This method can be used to check for version compatibility.

        t_major[in]        target server version (major)
        t_minor[in]        target server version (minor)
        t_rel[in]          target server version (release)

        Returns bool True if server version is GE (>=) version specified,
                     False if server version is LT (<) version specified
        """
        version_str = self.get_version()
        if version_str is not None:
            match = re.match(r'^(\d+\.\d+(\.\d+)*).*$', version_str.strip())
            if match:
                version = [int(x) for x in match.group(1).split('.')]
                version = (version + [0])[:3]  # Ensure a 3 elements list
                return version >= [int(t_major), int(t_minor), int(t_rel)]
            else:
                return False
        return True

    def exec_query(self, query_str, options=None, exec_timeout=0):
        """Execute a query and return result set

        This is the singular method to execute queries. It should be the only
        method used as it contains critical error code to catch the issue
        with mysql.connector throwing an error on an empty result set.

        Note: will handle exception and print error if query fails

        Note: if fetchall is False, the method returns the cursor instance

        query_str[in]      The query to execute
        options[in]        Options to control behavior:
            params         Parameters for query
            columns        Add column headings as first row
                           (default is False)
            fetch          Execute the fetch as part of the operation and
                           use a buffered cursor
                           (default is True)
            raw            If True, use a buffered raw cursor
                           (default is True)
            commit         Perform a commit (if needed) automatically at the
                           end (default: True).
        exec_timeout[in]   Timeout value in seconds to kill the query execution
                           if exceeded. Value must be greater than zero for
                           this feature to be enabled. By default 0, meaning
                           that the query will not be killed.

        Returns result set or cursor
        """
        if options is None:
            options = {}
        params = options.get('params', ())
        columns = options.get('columns', False)
        fetch = options.get('fetch', True)
        raw = options.get('raw', True)
        do_commit = options.get('commit', True)

        # Guard for connect() prerequisite
        assert self.db_conn, "You must call connect before executing a query."

        # If we are fetching all, we need to use a buffered
        if fetch:
            if raw:
                if mysql.connector.__version_info__ < (2, 0):
                    cur = self.db_conn.cursor(buffered=True, raw=True)
                else:
                    cur = self.db_conn.cursor(
                        cursor_class=MySQLUtilsCursorBufferedRaw)
            else:
                cur = self.db_conn.cursor(buffered=True)
        else:
            if mysql.connector.__version_info__ < (2, 0):
                cur = self.db_conn.cursor(raw=True)
            else:
                cur = self.db_conn.cursor(cursor_class=MySQLUtilsCursorRaw)

        # Execute query, handling parameters.
        q_killer = None
        try:
            if exec_timeout > 0:
                # Spawn thread to kill query if timeout is reached.
                # Note: set it as daemon to avoid waiting for it on exit.
                q_killer = QueryKillerThread(self, query_str, exec_timeout)
                q_killer.daemon = True
                q_killer.start()
            # Execute query.
            if params == ():
                cur.execute(query_str)
            else:
                cur.execute(query_str, params)
        except mysql.connector.Error as err:
            cur.close()
            if err.errno == CR_SERVER_LOST and exec_timeout > 0:
                # If the connection is killed (because the execution timeout is
                # reached), then it attempts to re-establish it (to execute
                # further queries) and raise a specific exception to track this
                # event.
                # CR_SERVER_LOST = Errno 2013 Lost connection to MySQL server
                # during query.
                self.db_conn.reconnect()
                raise UtilError("Timeout executing query", err.errno)
            else:
                raise UtilDBError("Query failed. {0}".format(err))
        except Exception:
            cur.close()
            raise UtilError("Unknown error. Command: {0}".format(query_str))
        finally:
            # Stop query killer thread if alive.
            if q_killer and q_killer.is_alive():
                q_killer.stop()

        # Fetch rows (only if available or fetch = True).
        # pylint: disable=R0101
        if cur.with_rows:
            if fetch or columns:
                try:
                    results = cur.fetchall()
                    if columns:
                        col_headings = cur.column_names
                        col_names = []
                        for col in col_headings:
                            col_names.append(col)
                        # pylint: disable=R0204
                        results = col_names, results
                except mysql.connector.Error as err:
                    raise UtilDBError("Error fetching all query data: "
                                      "{0}".format(err))
                finally:
                    cur.close()
                return results
            else:
                # Return cursor to fetch rows elsewhere (fetch = false).
                return cur
        else:
            # No results (not a SELECT)
            try:
                if do_commit:
                    self.db_conn.commit()
            except mysql.connector.Error as err:
                raise UtilDBError("Error performing commit: {0}".format(err))
            finally:
                cur.close()
            return cur

    def commit(self):
        """Perform a COMMIT.
        """
        # Guard for connect() prerequisite
        assert self.db_conn, "You must call connect before executing a query."

        self.db_conn.commit()

    def rollback(self):
        """Perform a ROLLBACK.
        """
        # Guard for connect() prerequisite
        assert self.db_conn, "You must call connect before executing a query."

        self.db_conn.rollback()

    def show_server_variable(self, variable):
        """Returns one or more rows from the SHOW VARIABLES command.

        variable[in]       The variable or wildcard string

        Returns result set
        """

        return self.exec_query("SHOW VARIABLES LIKE '%s'" % variable)

    def select_variable(self, var_name, var_type=None):
        """Get server system variable value using SELECT statement.

        This function displays the value of system variables using the SELECT
        statement. This can be used as a workaround for variables with very
        long values, as SHOW VARIABLES is subject to a version-dependent
        display-width limit.

        Note: Some variables may not be available using SELECT @@var_name, in
        such cases use SHOW VARIABLES LIKE 'var_name'.

        var_name[in]    Name of the variable to display.
        var_type[in]    Type of the variable ('session' or 'global'). By
                        default no type is used, meaning that the session
                        value is returned if it exists and the global value
                        otherwise.

        Return the value for the given server system variable.
        """
        if var_type is None:
            var_type = ''
        elif var_type.lower() in ('global', 'session', ''):
            var_type = '{0}.'.format(var_type)  # Add dot (.)
        else:
            raise UtilDBError("Invalid variable type: {0}. Supported types: "
                              "'global' and 'session'.".format(var_type))
        # Execute SELECT @@[var_type.]var_name.
        # Note: An error is issued if the given variable is not known.
        res = self.exec_query("SELECT @@{0}{1}".format(var_type, var_name))
        return res[0][0]

    def flush_logs(self, log_type=None):
        """Execute the FLUSH [log_type] LOGS statement.

        Reload internal logs cache and closes and reopens all log files, or
        only of the specified log_type.

        Note: The log_type option is available from MySQL 5.5.3.

        log_type[in]    Type of the log files to be flushed. Supported values:
                        BINARY, ENGINE, ERROR, GENERAL, RELAY, SLOW.
        """
        if log_type:
            self.exec_query("FLUSH {0} LOGS".format(log_type))
        else:
            self.exec_query("FLUSH LOGS")

    def get_uuid(self):
        """Return the uuid for this server if it is GTID aware.

        Returns uuid or None if server is not GTID aware.
        """
        if self.supports_gtid() != "NO":
            res = self.show_server_variable("server_uuid")
            return res[0][1]
        return None

    def supports_gtid(self):
        """Determine if server supports GTIDs

        Returns string - 'ON' = gtid supported and turned on,
                         'OFF' = supported but not enabled,
                         'NO' = not supported
        """
        # Check servers for GTID support
        version_ok = self.check_version_compat(5, 6, 5)
        if not version_ok:
            return "NO"
        try:
            res = self.exec_query("SELECT @@GLOBAL.GTID_MODE")
        except:
            return "NO"

        return res[0][0]

    def check_gtid_version(self):
        """Determine if server supports latest GTID changes

        This method checks the server to ensure it contains the latest
        changes to the GTID variables (from version 5.6.9).

        Raises UtilRplError when errors occur.
        """
        errors = []
        if self.supports_gtid() != "ON":
            errors.append("    GTID is not enabled.")
        if not self.check_version_compat(5, 6, 9):
            errors.append("    Server version must be 5.6.9 or greater.")
        if errors:
            error_str = "\n".join(errors)
            error_str = "\n".join([_GTID_ERROR % (self.host, self.port),
                                   error_str])
            raise UtilRplError(error_str)

    def check_gtid_executed(self, operation="copy"):
        """Check to see if the gtid_executed variable is clear

        If the value is not clear, raise an error with appropriate instructions
        for the user to correct the issue.

        operation[in]  Name of the operation (copy, import, etc.)
                       default = copy
        """
        res = self.exec_query("SHOW GLOBAL VARIABLES LIKE 'gtid_executed'")[0]
        if res[1].strip() == '':
            return
        err = ("The {0} operation contains GTID statements "
               "that require the global gtid_executed system variable on the "
               "target to be empty (no value). The gtid_executed value must "
               "be reset by issuing a RESET MASTER command on the target "
               "prior to attempting the {0} operation. "
               "Once the global gtid_executed value is cleared, you may "
               "retry the {0}.").format(operation)
        raise UtilRplError(err)

    def get_gtid_executed(self, skip_gtid_check=True):
        """Get the executed GTID set of the server.

        This function retrieves the (current) GTID_EXECUTED set of the server.

        skip_gtid_check[in]     Flag indicating if the check for GTID support
                                will be skipped or not. By default 'True'
                                (check is skipped).

        Returns a string with the GTID_EXECUTED set for this server.
        """
        if not skip_gtid_check:
            # Check server for GTID support.
            gtid_support = self.supports_gtid() == "NO"
            if gtid_support == 'NO':
                raise UtilRplError("Global Transaction IDs are not supported.")
            elif gtid_support == 'OFF':
                raise UtilError("Global Transaction IDs are not enabled.")
        # Get GTID_EXECUTED.
        try:
            return self.exec_query("SELECT @@GLOBAL.GTID_EXECUTED")[0][0]
        except UtilError:
            if skip_gtid_check:
                # Query likely failed because GTIDs are not supported,
                # therefore skip error in this case.
                return ""
            else:
                # If GTID check is not skipped re-raise exception.
                raise
        except IndexError:
            # If no rows are returned by query then return an empty string.
            return ''

    def gtid_subtract(self, gtid_set, gtid_subset):
        """Subtract given GTID sets.

        This function invokes GTID_SUBTRACT function on the server to retrieve
        the GTIDs from the given gtid_set that are not in the specified
        gtid_subset.

        gtid_set[in]        Base GTID set to subtract the subset from.
        gtid_subset[in]     GTID subset to be subtracted from the base set.

        Return a string with the GTID set resulting from the subtraction of the
        specified gtid_subset from the gtid_set.
        """
        try:
            return self.exec_query(
                "SELECT GTID_SUBTRACT('{0}', '{1}')".format(gtid_set,
                                                            gtid_subset)
            )[0][0]
        except IndexError:
            # If no rows are returned by query then return an empty string.
            return ''

    def gtid_subtract_executed(self, gtid_set):
        """Subtract GTID_EXECUTED to the given GTID set.

        This function invokes GTID_SUBTRACT function on the server to retrieve
        the GTIDs from the given gtid_set that are not in the GTID_EXECUTED
        set.

        gtid_set[in]        Base GTID set to subtract the GTID_EXECUTED.

        Return a string with the GTID set resulting from the subtraction of the
        GTID_EXECUTED set from the specified gtid_set.
        """
        from mysql.utilities.common.topology import _GTID_SUBTRACT_TO_EXECUTED
        try:
            result = self.exec_query(
                _GTID_SUBTRACT_TO_EXECUTED.format(gtid_set)
            )[0][0]
            # Remove newlines (\n and/or \r) from the GTID set string returned
            # by the server.
            return result.replace('\n', '').replace('\r', '')
        except IndexError:
            # If no rows are returned by query then return an empty string.
            return ''

    def inject_empty_trx(self, gtid, gtid_next_automatic=True):
        """ Inject an empty transaction.

        This method injects an empty transaction on the server for the given
        GTID.

        Note: SUPER privilege is required for this operation, more precisely
        to set the GTID_NEXT variable.

        gtid[in]                    GTID for the empty transaction to inject.
        gtid_next_automatic[in]     Indicate if the GTID_NEXT is set to
                                    AUTOMATIC after injecting the empty
                                    transaction. By default True.
        """
        self.exec_query("SET GTID_NEXT='{0}'".format(gtid))
        self.exec_query("BEGIN")
        self.commit()
        if gtid_next_automatic:
            self.exec_query("SET GTID_NEXT='AUTOMATIC'")

    def set_gtid_next_automatic(self):
        """ Set GTID_NEXT to AUTOMATIC.
        """
        self.exec_query("SET GTID_NEXT='AUTOMATIC'")

    def checksum_table(self, tbl_name, exec_timeout=0):
        """Compute checksum of specified table (CHECKSUM TABLE tbl_name).

        This function executes the CHECKSUM TABLE statement for the specified
        table and returns the result. The CHECKSUM is aborted (query killed)
        if a timeout value (greater than zero) is specified and the execution
        takes longer than the specified time.

        tbl_name[in]        Name of the table to perform the checksum.
        exec_timeout[in]    Maximum execution time (in seconds) of the query
                            after which it will be killed. By default 0, no
                            timeout.

        Returns a tuple with the checksum result for the target table. The
        first tuple element contains the result from the CHECKSUM TABLE query
        or None if an error occurred (e.g. execution timeout reached). The
        second element holds any error message or None if the operation was
        successful.
        """
        try:
            return self.exec_query(
                "CHECKSUM TABLE {0}".format(tbl_name),
                exec_timeout=exec_timeout
            )[0], None
        except IndexError:
            # If no rows are returned by query then return None.
            return None, "No data returned by CHECKSUM TABLE"
        except UtilError as err:
            # Return None if the query is killed (exec_timeout reached).
            return None, err.errmsg

    def get_gtid_status(self):
        """Get the GTID information for the server.

        This method attempts to retrieve the GTID lists. If the server
        does not have GTID turned on or does not support GTID, the method
        will throw and exception.

        Returns [list, list, list]
        """
        # Check servers for GTID support
        if self.supports_gtid() == "NO":
            raise UtilError("Global Transaction IDs are not supported.")

        res = self.exec_query("SELECT @@GLOBAL.GTID_MODE")
        if res[0][0].upper() == 'OFF':
            raise UtilError("Global Transaction IDs are not enabled.")

        gtid_data = [self.exec_query("SELECT @@GLOBAL.GTID_EXECUTED")[0],
                     self.exec_query("SELECT @@GLOBAL.GTID_PURGED")[0],
                     self.exec_query("SELECT @@GLOBAL.GTID_OWNED")[0]]

        return gtid_data

    def check_rpl_user(self, user, host):
        """Check replication user exists and has the correct privileges.

        user[in]      user name of rpl_user
        host[in]      host name of rpl_user

        Returns [] - no exceptions, list if exceptions found
        """
        errors = []
        ipv6 = False
        if "]" in host:
            ipv6 = True
            host = clean_IPv6(host)
        result = self.user_host_exists(user, host)
        if ipv6:
            result = format_IPv6(result)
        if result is None or result == []:
            errors.append("The replication user %s@%s was not found "
                          "on %s:%s." % (user, host, self.host, self.port))
        else:
            rpl_user = User(self, "%s@" % user + result)
            if not rpl_user.has_privilege('*', '*',
                                          'REPLICATION SLAVE'):
                errors.append("Replication user does not have the "
                              "correct privilege. She needs "
                              "'REPLICATION SLAVE' on all replicated "
                              "databases.")

        return errors

    def supports_plugin(self, plugin):
        """Check if the given plugin is supported.

        Check to see if the server supports a plugin. Return True if
        plugin installed and active.

        plugin[in]     Name of plugin to check

        Returns True if plugin is supported, and False otherwise.
        """
        _PLUGIN_QUERY = ("SELECT * FROM INFORMATION_SCHEMA.PLUGINS "
                         "WHERE PLUGIN_NAME ")
        res = self.exec_query("".join([_PLUGIN_QUERY, "LIKE ",
                                       "'%s" % plugin, "%'"]))
        if not res:
            return False
        # Now see if it is active.
        elif res[0][2] != 'ACTIVE':
            return False
        return True

    def get_all_databases(self, ignore_internal_dbs=True):
        """Return a result set containing all databases on the server
        except for internal databases (mysql, INFORMATION_SCHEMA,
        PERFORMANCE_SCHEMA).

        Note: New internal database 'sys' added by default for MySQL 5.7.7+.

        Returns result set
        """

        if ignore_internal_dbs:
            _GET_DATABASES = """
            SELECT SCHEMA_NAME
            FROM INFORMATION_SCHEMA.SCHEMATA
            WHERE SCHEMA_NAME != 'INFORMATION_SCHEMA'
            AND SCHEMA_NAME != 'PERFORMANCE_SCHEMA'
            AND SCHEMA_NAME != 'mysql'
            """
            # Starting from MySQL 5.7.7, sys schema is installed by default.
            if self.check_version_compat(5, 7, 7):
                _GET_DATABASES = "{0} AND SCHEMA_NAME != 'sys'".format(
                    _GET_DATABASES)
        else:
            _GET_DATABASES = """
            SELECT SCHEMA_NAME
            FROM INFORMATION_SCHEMA.SCHEMATA
            """

        return self.exec_query(_GET_DATABASES)

    def get_storage_engines(self):
        """Return list of storage engines on this server.

        Returns (list) (engine, support, comment)
        """

        _QUERY = """
            SELECT UPPER(engine), UPPER(support)
            FROM INFORMATION_SCHEMA.ENGINES
            ORDER BY engine
        """
        return self.exec_query(_QUERY)

    def check_storage_engines(self, other_list):
        """Compare storage engines from another server.

        This method compares the list of storage engines for the current
        server against a list supplied as **other_list**. It returns two
        lists - one for the storage engines on this server not on the other
        list, and another for the storage engines on the other list not on this
        server.

        Note: type case sensitive - make sure list is in uppercase

        other_list[in]     A list from another server in the form
                           (engine, support) - same output as
                           get_storage_engines()

        Returns (list, list)
        """
        # Guard for connect() prerequisite
        assert self.db_conn, "You must call connect before check engine lists."

        def _convert_set_to_list(set_items):
            """Convert a set to list
            """
            if len(set_items) > 0:
                item_list = []
                for item in set_items:
                    item_list.append(item)
            else:
                item_list = None
            return item_list

        # trivial, but guard against misuse
        this_list = self.get_storage_engines()
        if other_list is None:
            return (this_list, None)

        same = set(this_list) & set(other_list)
        master_extra = _convert_set_to_list(set(this_list) - same)
        slave_extra = _convert_set_to_list(set(other_list) - same)

        return (master_extra, slave_extra)

    def has_storage_engine(self, target):
        """Check to see if an engine exists and is supported.

        target[in]     name of engine to find

        Returns bool True - engine exists and is active, false = does not
                     exist or is not supported/not active/disabled
        """
        if len(target) == 0:
            return True  # This says we will use default engine on the server.
        if target is not None:
            engines = self.get_storage_engines()
            for engine in engines:
                if engine[0].upper() == target.upper() and \
                   engine[1].upper() in ['YES', 'DEFAULT']:
                    return True
        return False

    def substitute_engine(self, tbl_name, create_str,
                          new_engine, def_engine, quiet=False):
        """Replace storage engine in CREATE TABLE

        This method will replace the storage engine in the CREATE statement
        under the following conditions:
            - If new_engine is specified and it exists on destination, use it.
            - Else if existing engine does not exist and def_engine is specfied
              and it exists on destination, use it. Also, don't substitute if
              the existing engine will not be changed.

        tbl_name[in]       table name
        create_str[in]     CREATE statement
        new_engine[in]     name of storage engine to substitute (convert to)
        def_engine[in]     name of storage engine to use if existing engines
                           does not exist

        Returns string CREATE string with replacements if found, else return
                       original string
        """
        res = [create_str]
        exist_engine = ''
        is_create_like = False
        replace_msg = "# Replacing ENGINE=%s with ENGINE=%s for table %s."
        add_msg = "# Adding missing ENGINE=%s clause for table %s."
        if new_engine is not None or def_engine is not None:
            i = create_str.find("ENGINE=")
            if i > 0:
                j = create_str.find(" ", i)
                exist_engine = create_str[i + 7:j]
            else:
                # Check if it is a CREATE TABLE LIKE statement
                is_create_like = (create_str.find("CREATE TABLE {0} LIKE"
                                                  "".format(tbl_name)) == 0)

        # Set default engine
        #
        # If a default engine is specified and is not the same as the
        # engine specified in the table CREATE statement (existing engine) if
        # specified, and both engines exist on the server, replace the existing
        # engine with the default engine.
        #
        if def_engine is not None and \
                exist_engine.upper() != def_engine.upper() and \
                self.has_storage_engine(def_engine) and \
                self.has_storage_engine(exist_engine):

            # If no ENGINE= clause present, add it
            if len(exist_engine) == 0:
                if is_create_like:
                    alter_str = "ALTER TABLE {0} ENGINE={1}".format(tbl_name,
                                                                    def_engine)
                    res = [create_str, alter_str]
                else:
                    i = create_str.find(";")
                    i = len(create_str) if i == -1 else i
                    create_str = "{0} ENGINE={1};".format(create_str[0:i],
                                                          def_engine)
                    res = [create_str]
            # replace the existing storage engine
            else:
                create_str.replace("ENGINE=%s" % exist_engine,
                                   "ENGINE=%s" % def_engine)
            if not quiet:
                if len(exist_engine) > 0:
                    print replace_msg % (exist_engine, def_engine, tbl_name)
                else:
                    print add_msg % (def_engine, tbl_name)
            exist_engine = def_engine

        # Use new engine
        if (new_engine is not None and
                exist_engine.upper() != new_engine.upper() and
                self.has_storage_engine(new_engine)):
            if len(exist_engine) == 0:
                if is_create_like:
                    alter_str = "ALTER TABLE {0} ENGINE={1}".format(tbl_name,
                                                                    new_engine)
                    res = [create_str, alter_str]
                else:
                    i = create_str.find(";")
                    i = len(create_str) if i == -1 else i
                    create_str = "{0} ENGINE={1};".format(create_str[0:i],
                                                          new_engine)
                    res = [create_str]
            else:
                create_str = create_str.replace("ENGINE=%s" % exist_engine,
                                                "ENGINE=%s" % new_engine)
                res = [create_str]
            if not quiet:
                if len(exist_engine) > 0:
                    print replace_msg % (exist_engine, new_engine, tbl_name)
                else:
                    print add_msg % (new_engine, tbl_name)
        return res

    def get_innodb_stats(self):
        """Return type of InnoDB engine and its version information.

        This method returns a tuple containing the type of InnoDB storage
        engine (builtin or plugin) and the version number reported.

        Returns (tuple) (type = 'builtin' or 'plugin', version_number,
                         have_innodb = True or False)
        """
        # Guard for connect() prerequisite
        assert self.db_conn, "You must call connect before get innodb stats."

        _BUILTIN = """
            SELECT (support='YES' OR support='DEFAULT' OR support='ENABLED')
            AS `exists` FROM INFORMATION_SCHEMA.ENGINES
            WHERE engine = 'innodb';
        """
        _PLUGIN = """
            SELECT (plugin_library LIKE 'ha_innodb_plugin%') AS `exists`
            FROM INFORMATION_SCHEMA.PLUGINS
            WHERE LOWER(plugin_name) = 'innodb' AND
                  LOWER(plugin_status) = 'active';
        """
        _VERSION = """
            SELECT plugin_version, plugin_type_version
            FROM INFORMATION_SCHEMA.PLUGINS
            WHERE LOWER(plugin_name) = 'innodb';
        """

        inno_type = None
        results = self.exec_query(_BUILTIN)
        if results is not None and results != () and results[0][0] is not None:
            inno_type = "builtin"

        results = self.exec_query(_PLUGIN)
        if results is not None and results != () and \
           results != [] and results[0][0] is not None:
            inno_type = "plugin "

        results = self.exec_query(_VERSION)
        version = []
        if results is not None:
            version.append(results[0][0])
            version.append(results[0][1])
        else:
            version.append(None)
            version.append(None)

        results = self.show_server_variable("have_innodb")
        # pylint: disable=R0102
        if results is not None and results != [] and \
           results[0][1].lower() == "yes":
            have_innodb = True
        else:
            have_innodb = False

        return (inno_type, version[0], version[1], have_innodb)

    def read_and_exec_SQL(self, input_file, verbose=False):
        """Read an input file containing SQL statements and execute them.

        input_file[in]     The full path to the file
        verbose[in]        Print the command read
                           Default = False

        Returns True = success, False = error

        TODO : Make method read multi-line queries.
        """
        f_input = open(input_file)
        res = True
        while True:
            cmd = f_input.readline()
            if not cmd:
                break
            res = None
            if len(cmd) > 1:
                if cmd[0] != '#':
                    if verbose:
                        print cmd
                    query_options = {
                        'fetch': False
                    }
                    res = self.exec_query(cmd, query_options)
        f_input.close()
        return res

    def binlog_enabled(self):
        """Check binary logging status for the client.

        Returns bool - True - binary logging is ON, False = OFF
        """
        res = self.show_server_variable("log_bin")
        if not res:
            raise UtilRplError("Cannot retrieve status of log_bin variable.")
        if res[0][1] in ("OFF", "0"):
            return False
        return True

    def toggle_binlog(self, action="disable"):
        """Enable or disable binary logging for the client.

        Note: user must have SUPER privilege

        action[in]         if 'disable', turn off the binary log
                           elif 'enable' turn binary log on
                           do nothing if action != 'enable' or 'disable'
        """

        if action.lower() == 'disable':
            self.exec_query("SET SQL_LOG_BIN=0")
        elif action.lower() == 'enable':
            self.exec_query("SET SQL_LOG_BIN=1")

    def foreign_key_checks_enabled(self, force=False):
        """Check foreign key status for the connection.
        force[in]       if True, returns the value directly from the server
                        instead of returning the cached fkey value

        Returns bool - True - foreign keys are enabled
        """
        if self.fkeys is None or force:
            res = self.exec_query("SELECT @@GLOBAL.foreign_key_checks")
            self.fkeys = (res is not None) and (res[0][0] == "1")
        return self.fkeys

    def disable_foreign_key_checks(self, disable=True):
        """Enable or disable foreign key checks for the connection.

        disable[in]     if True, turn off foreign key checks
                        elif False turn foreign key checks on.
        """
        if self.fkeys is None:
            self.foreign_key_checks_enabled()

        # Only do something if foreign keys are OFF and shouldn't be disabled
        # or if they are ON and should be disabled
        if self.fkeys == disable:
            val = "OFF" if disable else "ON"
            self.exec_query(_FOREIGN_KEY_SET.format(val),
                            {'fetch': False, 'commit': False})
            self.fkeys = not self.fkeys

    def autocommit_set(self):
        """Check autocommit status for the connection.

        Returns bool - True if autocommit is enabled and False otherwise.
        """
        if self.autocommit is None:
            res = self.show_server_variable('autocommit')
            self.autocommit = (res and res[0][1] == '1')
        return self.autocommit

    def toggle_autocommit(self, enable=None):
        """Enable or disable autocommit for the connection.

        This method switch the autocommit value or enable/disable it according
        to the given parameter.

        enable[in]         if True, turn on autocommit (set to 1)
                           else if False turn autocommit off (set to 0).
        """
        if enable is None:
            # Switch autocommit value.
            if self.autocommit is None:
                # Get autocommit value if unknown
                self.autocommit_set()
            if self.autocommit:
                value = '0'
                self.autocommit = False
            else:
                value = '1'
                self.autocommit = True
        else:
            # Set AUTOCOMMIT according to provided value.
            if enable:
                value = '1'
                self.autocommit = True
            else:
                value = '0'
                self.autocommit = False
        # Change autocommit value.
        self.exec_query(_AUTOCOMMIT_SET.format(value), {'fetch': 'false'})

    def get_server_id(self):
        """Retrieve the server id.

        Returns int - server id.
        """
        try:
            res = self.show_server_variable("server_id")
        except:
            raise UtilRplError("Cannot retrieve server id from "
                               "%s." % self.role)

        return int(res[0][1])

    def get_server_uuid(self):
        """Retrieve the server uuid.

        Returns string - server uuid.
        """
        try:
            res = self.show_server_variable("server_uuid")
            if res is None or res == []:
                return None
        except:
            raise UtilRplError("Cannot retrieve server_uuid from "
                               "%s." % self.role)

        return res[0][1]

    def get_lctn(self):
        """Get lower_case_table_name setting.

        Returns lctn value or None if cannot get value
        """
        res = self.show_server_variable("lower_case_table_names")
        if res != []:
            return res[0][1]
        return None

    def get_binary_logs(self, options=None):
        """Return a list of the binary logs.

        options[in]        query options

        Returns list - binlogs or None if binary logging turned off
        """
        if options is None:
            options = {}
        if self.binlog_enabled():
            return self.exec_query("SHOW BINARY LOGS", options)

        return None

    def set_read_only(self, on=False):
        """Turn read only mode on/off

        on[in]         if True, turn read_only ON
                       Default is False
        """
        # Only turn on|off read only if it were off at connect()
        if on and not self.read_only:
            self.exec_query("SET @@GLOBAL.READ_ONLY = 'ON'")
            self.read_only = True
        elif not on and self.read_only:
            self.read_only = False
            self.exec_query("SET @@GLOBAL.READ_ONLY = 'OFF'")
        return None

    def grant_tables_enabled(self):
        """Check to see if grant tables are enabled

        Returns bool - True = grant tables are enabled, False = disabled
        """
        if self.grants_enabled is None:
            try:
                self.exec_query("SHOW GRANTS FOR 'snuffles'@'host'")
                self.grants_enabled = True
            except UtilError as error:
                if "--skip-grant-tables" in error.errmsg:
                    self.grants_enabled = False
                # Ignore other errors as they are not pertinent to the check
                else:
                    self.grants_enabled = True
        return self.grants_enabled

    def get_server_binlogs_list(self, include_size=False):
        """Find the binlog file names listed on a server.

        Obtains the binlog file names available on the server by using the
        'SHOW BINARY LOGS' query at the given server instance and returns these
        file names as a list.

        include_size[in]  Boolean value to indicate if the returning list shall
                          include the size of the file.

        Returns a list with the binary logs names available on master.
        """
        res = self.exec_query("SHOW BINARY LOGS")

        server_binlogs = []
        for row in res:
            if include_size:
                server_binlogs.append(row)
            else:
                server_binlogs.append(row[0])
        return server_binlogs

    def sql_mode(self, mode, enable):
        """Set the sql_mode

        This method sets the sql_mode passed. If enable is True,
        the method adds the mode, else, it removes the mode.

        mode[in]      The sql_mode you want to set
        enable[in]    If True, set the mode, else remove the mode.

        Returns string - new sql_mode setting or None=not enabled/disabled
        """
        SQL_MODE = 'SET @@GLOBAL.SQL_MODE = "{0}"'
        sql_mode = self.show_server_variable("sql_mode")
        if sql_mode[0]:
            modes = sql_mode[0][1].split(",")
            sql_mode_str = 'mt'
            if enable:
                if mode not in modes:
                    modes.append(mode)
                else:
                    sql_mode_str = None
            else:
                if mode in modes:
                    index = modes.index(mode)
                    modes.pop(index)
                else:
                    sql_mode_str = None
            if sql_mode_str:
                sql_mode_str = SQL_MODE.format(",".join(modes))
                self.exec_query(sql_mode_str)
                return sql_mode_str
        return None


class QueryKillerThread(threading.Thread):
    """Class to run a thread to kill an executing query.

    This class is used to spawn a thread than will kill the execution
    (connection) of a query upon reaching a given timeout.
    """

    def __init__(self, server, query, timeout):
        """Constructor.

        server[in]      Server instance where the target query is executed.
        query[in]       Target query to kill.
        timeout[in]     Timeout value in seconds used to kill the query when
                        reached.
        """
        threading.Thread.__init__(self)
        self._stop_event = threading.Event()
        self._query = query
        self._timeout = timeout
        self._server = server
        self._connection = server.get_connection()
        server.get_version()

    def run(self):
        """Main execution of the query killer thread.
        Stop the thread if instructed as such
        """
        connector_error = None
        # Kill the query connection upon reaching the given execution timeout.
        while not self._stop_event.is_set():
            # Wait during the defined time.
            self._stop_event.wait(self._timeout)
            # If the thread was asked to stop during wait, it does not try to
            # kill the query.
            if not self._stop_event.is_set():
                try:
                    if mysql.connector.__version_info__ < (2, 0):
                        cur = self._connection.cursor(raw=True)
                    else:
                        cur = self._connection.cursor(
                            cursor_class=MySQLUtilsCursorRaw)

                    # Get process information from threads table when available
                    # (for versions > 5.6.1), since it does not require a mutex
                    # and has minimal impact on server performance.
                    if self._server.check_version_compat(5, 6, 1):
                        cur.execute(
                            "SELECT processlist_id "
                            "FROM performance_schema.threads"
                            " WHERE processlist_command='Query'"
                            " AND processlist_info='{0}'".format(self._query))
                    else:
                        cur.execute(
                            "SELECT id FROM information_schema.processlist"
                            " WHERE command='Query'"
                            " AND info='{0}'".format(self._query))
                    result = cur.fetchall()

                    try:
                        process_id = result[0][0]
                    except IndexError:
                        # No rows are returned if the query ended in the
                        # meantime.
                        process_id = None

                    # Kill the connection associated to que process id.
                    # Note: killing the query will not work with
                    # connector-python,since it will hang waiting for the
                    #  query to return.
                    if process_id:
                        cur.execute("KILL {0}".format(process_id))
                except mysql.connector.Error as err:
                    # Hold error to raise at the end.
                    connector_error = err
                finally:
                    # Close cursor if available.
                    if cur:
                        cur.close()
                # Stop this thread.
                self.stop()

        # Close connection.
        try:
            self._connection.disconnect()
        except mysql.connector.Error:
            # Only raise error if no previous error has occurred.
            if not connector_error:
                raise
        finally:
            # Raise any previous error that already occurred.
            if connector_error is not None:
                # pylint: disable=E0702
                raise connector_error

    def stop(self):
        """Stop the thread.

        Set the event flag for the thread to stop as soon as possible.
        """
        self._stop_event.set()
