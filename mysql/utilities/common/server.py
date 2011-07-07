#
# Copyright (c) 2010, 2011 Oracle and/or its affiliates. All rights reserved.
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
from mysql.utilities.common.options import parse_connection

def get_connection_dictionary(conn_info):
    """Get the connection dictionary.

    The method accepts one of the following types for conn_info:
    
        - dictionary containing connection information including:
          (user, passwd, host, port, socket)
        - connection string in the form: user:pass@host:port:socket
        - an instance of the Server class
        
    conn_info[in]          Connection information

    Returns dict - dictionary for connection (user, passwd, host, port, socket)
    """
    if conn_info is None:
        return conn_info
    conn_val = {}
    if isinstance(conn_info, dict):
        conn_val = conn_info
    elif isinstance(conn_info, Server):
        # get server's dictionary
        conn_val = conn_info.get_connection_values()
    elif isinstance(conn_info, basestring):
        # parse the string
        conn_val = parse_connection(conn_info)
    else:
        raise MySQLUtilError("Cannot determine connection information type.")

    return conn_val


def _print_connection(prefix, conn_info):
    """ Print connection information
    
    The method accepts one of the following types for conn_info:
    
        - dictionary containing connection information including:
          (user, passwd, host, port, socket)
        - connection string in the form: user:pass@host:port:socket
        - an instance of the Server class
        
    conn_info[in]          Connection information
    """
    conn_val = get_connection_dictionary(conn_info)
    print "# %s on %s: ..." % (prefix, conn_val["host"]),


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


def connect_servers(src_val, dest_val, options={}):
    """ Connect to a source and destination server.

    This method takes two groups of --server=user:password@host:port:socket
    values and attempts to connect one as a source connection and the other
    as the destination connection. If the source and destination are the
    same server and the unique parameter is False, destination is set to None.
     
    The method accepts one of the following types for the src_val and dest_val:
    
        - dictionary containing connection information including:
          (user, passwd, host, port, socket)
        - connection string in the form: user:pass@host:port:socket
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

    Returns tuple (source, destination) where
            source = connection to source server
            destination = connection to destination server (set to None)
                          if source and destination are same server
            if error, returns (None, None)
    """
    
    quiet = options.get("quiet", False)
    src_name = options.get("src_name", "Source")
    dest_name = options.get("dest_name", "Destination")
    version = options.get("version", None)

    def _connect_server(name, values, version, quiet):        

        server_conn = None
    
        # Try to connect to the MySQL database server.
        if not quiet:
            _print_connection(name, values)

        server_options = {
            'conn_info' : values,
            'role'      : name,
        }
        server_conn = Server(server_options)
        server_conn.connect()
    
        return server_conn
     
    def _check_version(conn, name, version):    
        if version is not None:
            major, minor, rel = version.split(".")
            if not conn.check_version_compat(major, minor, rel):
                raise MySQLUtilError("The %s version is incompatible. Utility "
                                     "requires version %s or higher." %
                                     (name, version))
        
    source = None
    destination = None

    # Fail if not the same types
    if not dest_val is None and not isinstance(src_val, type(dest_val)):
        raise MySQLUtilError("Connection paramters are not the same type.")

    # Get connection dictionaries if src_val,dest_val are not Server instances.
    if isinstance(src_val, Server):
        source = src_val
        destination = dest_val
    src_val = get_connection_dictionary(src_val)
    dest_val = get_connection_dictionary(dest_val)

    # Check for uniqueness - dictionary 
    if options.get("unique", False) and dest_val is not None:
        dupes = False
        if "unix_socket" in src_val and "unix_socket" in dest_val:
            dupes = (src_val["unix_socket"] == dest_val["unix_socket"])
        else:
            dupes = (src_val["port"] == dest_val["port"]) and \
                    (src_val["host"] == dest_val["host"])
        if dupes:
            raise MySQLUtilError("You must specify two different servers "
                                 "for the operation.")

    cloning = (src_val == dest_val) or dest_val is None
    # If we're cloning so use same server for faster copy
    if not cloning and dest_val is None:
        dest_val = src_val

    if source is None:
        source = _connect_server(src_name, src_val, version, quiet)
        if not quiet:
            print "connected."
    _check_version(source, src_name, version)

    if not cloning:
        if destination is None:
            destination = _connect_server(dest_name, dest_val, version, quiet)
            if not quiet:
                print "connected."
        _check_version(destination, dest_name, version)
    elif not quiet and dest_val is not None:
        _print_connection(dest_name, src_val)
        print "connected."

    servers = (source, destination)
    return servers


def test_connect(conn_info):
    """Test connection to a server.
    
    The method accepts one of the following types for conn_info:
    
        - dictionary containing connection information including:
          (user, passwd, host, port, socket)
        - connection string in the form: user:pass@host:port:socket
        - an instance of the Server class
        
    conn_info[in]          Connection information

    Returns True if connection success, False if error
    """
    from mysql.utilities.exception import FormatError
    
    # Parse source connection values
    src_val = get_connection_dictionary(conn_info)
    try:
        conn_options = {
            'quiet'     : True,
            'src_name'  : "test",
            'dest_name' : None,
        }
        s = connect_servers(src_val, None, conn_options)
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

    def __init__(self, options={}):
        """Constructor

        The method accepts one of the following types for options['conn_info']:
        
            - dictionary containing connection information including:
              (user, passwd, host, port, socket)
            - connection string in the form: user:pass@host:port:socket
            - an instance of the Server class
             
        options[in]        options for controlling behavior:
            conn_info      a dictionary containing connection information
                           (user, passwd, host, port, socket)
            role           Name or role of server (e.g., server, master)
            verbose        print extra data during operations (optional)
                           default value = False
            charset        Default character set for the connection.
                           (default latin1)
        """
        
        assert not options.get("conn_info") == None
        
        self.verbose = options.get("verbose", False)
        self.db_conn = None
        self.charset = options.get("charset", "latin1")
        self.role = options.get("role", "Server")
        conn_values = get_connection_dictionary(options.get("conn_info"))
        try:
            self.host = conn_values["host"]
            self.user = conn_values["user"]
            self.passwd = conn_values["passwd"]
            self.socket = conn_values["unix_socket"] \
                          if "unix_socket" in conn_values else None
            self.port = 3306
            if conn_values["port"] is not None:
                self.port = int(conn_values["port"])
        except KeyError:
            raise MySQLUtilError("Dictionary format not recognized.")
        self.connect_error = None


    def get_connection_values(self):
        """Return a dictionary of connection values for the server.
        
        Returns dictionary
        """
        conn_vals = {
            "user"   : self.user,
            "host"   : self.host
        }
        if self.passwd:
            conn_vals["passwd"] = self.passwd
        if self.socket:
            conn_vals["socket"] = self.socket
        if self.port:
            conn_vals["port"] = self.port

        return conn_vals


    def connect(self):
        """Connect to server

        Attempts to connect to the server as specified by the connection
        parameters.

        Note: This method must be called before executing queries.


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
            parameters['charset'] = self.charset
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

        query_options = {
            'fetch' : False
        }
        fkey_query = "SET foreign_key_checks = %s"
        res = self.show_server_variable("foreign_key_checks")
        fkey = (res[0][1] == "ON")
        if not fkey and turn_on:
            res = self.exec_query(fkey_query % "ON", query_options)
        elif fkey and not turn_on:
            res = self.exec_query(fkey_query % "OFF", query_options)
        return fkey


    def exec_query(self, query_str, options={}):
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

        Returns result set or cursor
        """
        params = options.get('params', ())
        columns = options.get('columns', False)
        fetch = options.get('fetch', True)
        raw = options.get('raw', True)

        # Guard for connect() prerequisite
        assert self.db_conn, "You must call connect before executing a query."

        results = ()
        # If we are fetching all, we need to use a buffered
        if fetch:
            if raw:
                cur = self.db_conn.cursor(
                    cursor_class=mysql.connector.cursor.MySQLCursorBufferedRaw)
            else:
                cur = self.db_conn.cursor(buffered)
        else:
            cur = self.db_conn.cursor(raw=True)

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


    def has_storage_engine(self, target):
        """Check to see if an engine exists and is supported.
        
        target[in]     name of engine to find
        
        Returns bool True - engine exists and is active, false = does not
                     exist or is not supported/not active/disabled
        """
        if len(target) == 0:
            return True # This says we will use default engine on the server.
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

        exist_engine = ''
        replace_msg = "# Replacing ENGINE=%s with ENGINE=%s for table %s."
        add_msg = "# Adding missing ENGINE=%s clause for table %s."
        if new_engine is not None or def_engine is not None:
            i = create_str.find("ENGINE=")
            if i > 0:
                j = create_str.find(" ", i)
                exist_engine = create_str[i+7:j]

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
                i = create_str.find(";")
                create_str = create_str[0:i] + " ENGINE=%s;"  % def_engine
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
        if new_engine is not None and \
           exist_engine.upper() != new_engine.upper() and \
           self.has_storage_engine(new_engine):
            if len(exist_engine) == 0:
                i = create_str.find(";")
                create_str = create_str[0:i] + " ENGINE=%s;"  % new_engine
            else:                
                create_str = create_str.replace("ENGINE=%s" % exist_engine,
                                                "ENGINE=%s" % new_engine)
            if not quiet:
                if len(exist_engine) > 0:
                    print replace_msg % (exist_engine, new_engine, tbl_name)
                else:
                    print add_msg % (new_engine, tbl_name)
        
        return create_str


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
                    query_options = {
                        'fetch' : False
                    }
                    res = self.exec_query(cmd, query_options)
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

