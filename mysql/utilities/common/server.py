#
# Copyright (c) 2010, Oracle and/or its affiliates. All rights reserved.
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
by multiple utlities. It also contains helper methods for common
server operations used in multiple utilities.
"""

import os
import re
import sys
import mysql.connector
from mysql.utilities.exception import MySQLUtilError

def _print_connection(prefix, conn_val):
    """ Print connection information
    """
    conn_str = None
    sys.stdout.write("# %s on %s: ... " % (prefix, conn_val["host"]))


def find_running_servers(all=False, start=3306, end=3333, datadir_prefix=None):
    """Check to see if there are any servers running on the local host.

    This method attempts to locate all running servers. If provided, it will
    also limit the search to specific ports of datadirectory prefixes.
    
    This method uses ps for posix systems and netstat for Windows machines
    to determine the list of running servers.

    For posix, it matches on the datadir and if datadir is the path for the
    test directory, the server will be added to the list.

    For nt, it matches on the port in the range starting_port,
    starting_port + 10.

    all[in]             If True, find all processes else only user processes
    start[in]           For Windows/NT systems: Starting port value to search.
                        Default = 3306
    end[in]             For Windows/NT systems: Ending port value to search.
                        Default = 3333
    datadir_prefix[in]  For posix systems, if not None, find only those servers
                        whose datadir starts with this prefix.

    Returns list - tuples of the form: (process_id, [datadir|port])
    """
    import string
    import subprocess
    import tempfile

    processes = []
    if os.name == "posix":
        file = tempfile.TemporaryFile()
        if all:
            output = subprocess.call(["ps", "-A"], stdout=file)
        else:
            output = subprocess.call(["ps", "-f"], stdout=file)
        file.seek(0)
        for line in file.readlines():
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
                if all:
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
        proc = subprocess.Popen("netstat -anop tcp", shell=True,
                                stdout=f_out, stderr=f_out)
        res = proc.wait()
        f_out.close()
        f_out = open("portlist", 'r')
        for line in f_out.readlines():
            proginfo = string.split(line)
            if proginfo:
                # Look for port on either local or foreign address
                port = proginfo[1][proginfo[1].find(":")+1:]
                if proginfo[1][0] == '0' and port.isdigit():
                    if int(port) >= start and int(port) <= end:
                        processes.append((proginfo[4], port))
                        break
                if len(proginfo) > 2:
                    port = proginfo[2][proginfo[2].find(":")+1:]
                    if port.isdigit() and \
                       int(port) >= int(start) and int(port) <= int(end):
                        processes.append((proginfo[4], port))
                        break
        f_out.close()
        os.unlink("portlist")
    return processes


def connect_servers(src_val, dest_val, quiet=False, version=None,
                    src_name="Source", dest_name="Destination"):
    """ Connect to a source and destination server.

    This method takes two groups of --server=user:password@host:port:socket
    values and attempts to connect one as a source connection and the other
    as the destination connection. If the source and destination are the
    same server, destination is set to None.

    src_val[in]        a dictionary containing connection information for the
                       source including:
                       (user, passwd, host, port, socket)
    dest_val[in]       a dictionary containing connection information for the
                       destination including:
                       (user, passwd, host, port, socket)
    quiet[in]          do not print any information during the operation
                       (default is False)
    version[in]        if specified (default is None), perform version
                       checking and fail if server version is < version
                       specified - an exception is raised
    src_name[in]       name to use for source server
                       (default is "Source")
    dest_name[in]      name to use for destination server
                       (default is "Destination")

    Returns tuple (source, destination) where
            source = connection to source server
            destination = connection to destination server (set to None)
                          if source and destination are same server
            if error, returns (None, None)
    """
    
    def _connect_server(name, values, version, quiet):
        server_conn = None
        if not quiet:
            _print_connection(name, values)
    
        # Try to connect to the MySQL database server.
        server_conn = Server(values, name)
        server_conn.connect()
        if version is not None:
            if not server_conn.check_version_compat(major, minor, rel):
                raise MySQLUtilError("The %s version is incompatible. Utility "
                                     "requires version %s or higher." %
                                     (name, version))
    
        if not quiet:
            sys.stdout.write("connected.\n")

        return server_conn

    source = None
    destination = None
    cloning = (src_val == dest_val) or dest_val is None
    if version is not None:
        major, minor, rel = version.split(".")

    if type(src_val) == type({}): 
        # If we're cloning so use same server for faster copy
        if not cloning and dest_val is None:
            dest_val = src_val
    
        source = _connect_server(src_name, src_val, version, quiet)
    
        if not cloning:
            destination = _connect_server(dest_name, dest_val, version, quiet)
        elif not quiet and dest_val is not None:
            _print_connection(dest_name, src_val)
            sys.stdout.write("connected.\n")
    elif type(src_val) != Server:
        raise MySQLUtilError("Cannot determine type of parameter.")
    else:
        source = src_val
        destination = dest_val

    servers = (source, destination)
    return servers


def test_connect(server_dict):
    """Test connection to a server.
    
    server_dict[in]    a dictionary containing connection information for the
                       source including:
                       (user, passwd, host, port, socket)

    Returns True if connection success, False if error
    """
    from mysql.utilities.common.options import parse_connection
    from mysql.utilities.exception import FormatError
    
    # Parse source connection values
    src_val = parse_connection(server_dict)
    try:
        s = connect_servers(src_val, None, True, None, "test", None)
    except MySQLUtilError, e:
        return False
    return True


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

    def __init__(self, conn_val, role="Server", verbose=False):
        """Constructor

        dest_val[in]       a dictionary containing connection information
                           (user, passwd, host, port, socket)
        role[in]           Name or role of server (e.g., server, master)
        verbose[in]        print extra data during operations (optional)
                           default value = False
        """
        self.verbose = verbose
        self.db_conn = None
        self.role = role
        self.host = conn_val["host"]
        self.user = conn_val["user"]
        self.passwd = conn_val["passwd"]
        self.socket = conn_val["unix_socket"] if "unix_socket" in conn_val else None
        self.port = 3306
        if conn_val["port"] is not None:
            self.port = int(conn_val["port"])
        self.connect_error = None


    def connect(self, charset="latin1"):
        """Connect to server

        Attempts to connect to the server as specified by the connection
        parameters.

        Note: This method must be called before executing queries.

        charset[in]        Default character set for the connection.
                           (default latin1)

        Raises MySQLUtilError if error during connect
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
            parameters['charset'] = charset
            self.db_conn = mysql.connector.connect(**parameters)
        except mysql.connector.Error, e:
            raise MySQLUtilError("Cannot connect to the %s server.\n"
                                 "Error %s" % (self.role, e.msg))
            return False
        self.connect_error = None


    def check_version_compat(self, t_major, t_minor, t_rel):
        """ Checks version of the server against requested version.

        This method can be used to check for version compatibility.

        t_major[in]        target server version (major)
        t_minor[in]        target server version (minor)
        t_rel[in]          target server version (release)

        Returns bool True if server version is GE (>=) version specified,
                     False if server version is LT (<) version specified
        """
        res = self.show_server_variable("VERSION")
        if res:
            version_str = res[0][1]
            index = version_str.find("-")
            if index >= 0:
                parts = res[0][1][0:index].split(".")
            else:
                parts = res[0][1].split(".")
            major = parts[0]
            minor = parts[1]
            rel = parts[2]
            if int(t_major) > int(major):
                return False
            elif int(t_major) == int(major):
                if int(t_minor) > int(minor):
                    return False
                elif int(t_minor) == int(minor):
                    if int(t_rel) > int(rel):
                        return False
        return True


    def toggle_fkeys(self, turn_on=True):
        """ Turn foreign key checks on or off

        turn_on[in]        if True, turns on fkey check
                           if False, turns off fkey check

        Returns original value = True == ON, False == OFF
        """

        fkey_query = "SET foreign_key_checks = %s"
        res = self.show_server_variable("foreign_key_checks")
        fkey = (res[0][1] == "ON")
        if not fkey and turn_on:
            res = self.exec_query(fkey_query % "ON", (), False, False)
        elif fkey and not turn_on:
            res = self.exec_query(fkey_query % "OFF", (), False, False)
        return fkey


    def exec_query(self, query_str, params=(),
                   columns=False, fetch=True, raw=True):
        """Execute a query and return result set

        This is the singular method to execute queries. It should be the only
        method used as it contains critical error code to catch the issue
        with mysql.connector throwing an error on an empty result set.

        Note: will handle exception and print error if query fails

        Note: if fetchall is False, the method returns the cursor instance

        query_str[in]      The query to execute
        params[in]         Parameters for query
        columns[in]        Add column headings as first row
                           (default is False)
        fetch[in]          Execute the fetch as part of the operation and
                           use a buffered cursor
                           (default is True)
        raw[in]            If True, use a buffered raw cursor
                           (default is True)

        Returns result set or cursor
        """

        # Guard for connect() prerequisite
        assert self.db_conn, "You must call connect before executing a query."

        results = ()
        # If we are fetching all, we need to use a buffered
        if fetch:
            if raw:
                #print "USING: buffered raw!"
                cur = self.db_conn.cursor(
                    cursor_class=mysql.connector.cursor.MySQLCursorBufferedRaw)
            else:
                #print "USING: buffered only"
                cur = self.db_conn.cursor(buffered)
        else:
            #print "USING: default cursor!"
            cur = self.db_conn.cursor(raw=True)

        #print "query_str:", query_str, "\nparams:", params
        try:
            if params == ():
                res = cur.execute(query_str)
            else:
                res = cur.execute(query_str, params)
        except mysql.connector.Error, e:
            cur.close()
            raise MySQLUtilError("Query failed. " + e.__str__())
        except Exception, e:
            cursor.close()
            raise MySQLUtilError("Unknown error. Command: %s" % query_str)
        if fetch or columns:
            try:
                results = cur.fetchall()
            except mysql.connector.errors.InterfaceError, e:
                if e.msg.lower() == "no result set to fetch from.":
                    pass # This error means there were no results.
                else:    # otherwise, re-raise error
                    raise e

            if columns:
                col_headings = cur.column_names
                stop = len(col_headings)
                col_names = []
                for col in col_headings:
                    col_names.append(col)
                results = col_names, results
            cur.close()
            self.db_conn.commit()
            return results
        else:
            return cur

    def show_server_variable(self, variable):
        """Returns one or more rows from the SHOW VARIABLES command.

        variable[in]       The variable or wildcard string

        Returns result set
        """

        return self.exec_query("SHOW VARIABLES LIKE '%s'" % variable)


    def get_all_databases(self):
        """Return a result set containing all databases on the server
        except for internal databases (mysql, INFORMATION_SCHEMA,
        PERFORMANCE_SCHEMA)

        Returns result set
        """

        _GET_DATABASES = """
        SELECT SCHEMA_NAME
        FROM INFORMATION_SCHEMA.SCHEMATA
        WHERE SCHEMA_NAME != 'INFORMATION_SCHEMA'
        AND SCHEMA_NAME != 'PERFORMANCE_SCHEMA'
        AND SCHEMA_NAME != 'mysql'
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
        file = open(input_file)
        i = 0
        res = True
        while True:
            cmd = file.readline()
            if not cmd:
                break;
            i += 1
            res = None
            if len(cmd) > 1:
                if cmd[0] != '#':
                    if verbose:
                        print cmd
                    res = self.exec_query(cmd, (), False, False)
        file.close()
        return res


    def binlog_enabled(self):
        """Check binary logging status for the client.
        
        Returns bool - True - binary logging is ON, False = OFF
        """
        res = self.show_server_variable("sql_log_bin")
        if not res:
            raise MySQLUtilError("Cannot retrieve status of "
                                 "sql_log_bin variable.")
        if res[0][1] == "OFF" or res[0][1] == "0":
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

