#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
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
import mysql.connector
from mysql.utilities.exception import UtilError, UtilDBError, UtilRplError
from mysql.utilities.common.options import parse_connection

_FOREIGN_KEY_SET = "SET foreign_key_checks = %s"
_GTID_ERROR = ("The server %s:%s does not comply to the latest GTID " 
               "feature support. Errors:")

def get_connection_dictionary(conn_info):
    """Get the connection dictionary.

    The method accepts one of the following types for conn_info:
    
        - dictionary containing connection information including:
          (user, passwd, host, port, socket)
        - connection string in the form: user:pass@host:port:socket or 
                                         login-path:port:socket
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
        conn_val = parse_connection(conn_info, None)
    else:
        raise UtilError("Cannot determine connection information type.")

    return conn_val


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


def get_local_servers(all=False, start=3306, end=3333, datadir_prefix=None):
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
    from mysql.utilities.common.tools import execute_script

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
        res = execute_script("netstat -anop tcp", "portlist")
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


def get_server(name, values, quiet):        
    """Connect to a server and return Server instance
    
    If the name is 'master' or 'slave', the connection will be made via the
    Master or Slave class else a normal Server class shall be used.
    
    name[in]           name of the server
    values[in]         dictionary of connection values
    quiet[in]          if True, do not print messages
    
    Returns Server class instance
    """
    from mysql.utilities.common.replication import Master
    from mysql.utilities.common.replication import Slave
    
    server_conn = None

    # Try to connect to the MySQL database server.
    if not quiet:
        _print_connection(name, values)

    server_options = {
        'conn_info' : values,
        'role'      : name,
    }
    if name.lower() == 'master':
        server_conn = Master(server_options)
    elif name.lower() == 'slave':
        server_conn = Slave(server_options)
    else:
        server_conn = Server(server_options)
    server_conn.connect()

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
    from mysql.utilities.common.tools import ping_host

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


def connect_servers(src_val, dest_val, options={}):
    """Connect to a source and destination server.

    This method takes two groups of --server=user:password@host:port:socket
    values and attempts to connect one as a source connection and the other
    as the destination connection. If the source and destination are the
    same server and the unique parameter is False, destination is set to None.
     
    The method accepts one of the following types for the src_val and dest_val:
    
        - dictionary containing connection information including:
          (user, passwd, host, port, socket)
        - connection string in the form: user:pass@host:port:socket or
                                         login-path:port:socket
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

    source = None
    destination = None

    # Get connection dictionaries
    src_dict = get_connection_dictionary(src_val)
    dest_dict = get_connection_dictionary(dest_val)

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
        source = get_server(src_name, src_dict, quiet)
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
            destination = get_server(dest_name, dest_dict, quiet)
            if not quiet:
                print "connected."
        if not _require_version(destination, version):
            raise UtilError("The %s version is incompatible. Utility "
                            "requires version %s or higher." %
                            (dest_name, version))
    elif not quiet and dest_dict is not None and \
         not isinstance(dest_val, Server):
        _print_connection(dest_name, src_dict)
        print "connected."
    return (source, destination)


def test_connect(conn_info, throw_errors=False):
    """Test connection to a server.
    
    The method accepts one of the following types for conn_info:
    
        - dictionary containing connection information including:
          (user, passwd, host, port, socket)
        - connection string in the form: user:pass@host:port:socket or
                                         login-path:port:socket
        - an instance of the Server class
        
    conn_info[in]          Connection information
    
    throw_errors           throw any errors found during the test,
                           false by default.
    
    Returns True if connection success, False if error
    """
    # Parse source connection values
    try:
        src_val = get_connection_dictionary(conn_info)
    except Exception as err:
        raise UtilError("Server connection values invalid: %s." % err.errmsg)
    try:
        conn_options = {
            'quiet'     : True,
            'src_name'  : "test",
            'dest_name' : None,
        }
        s = connect_servers(src_val, None, conn_options)
        s[0].disconnect()
    except UtilError:
        if throw_errors:
            raise
        return False
    return True


def check_hostname_alias(server1_vals, server2_vals):
    """Check to see if the servers are the same machine by host name.
    
    server1_vals[in]   connection dictionary for server1
    server2_vals[in]   connection dictionary for server2
    
    Returns bool - true = server1 and server2 are the same host
    """
    server1 = Server({'conn_info' : server1_vals})
    server2 = Server({'conn_info' : server2_vals})

    return (server1.is_alias(server2.host) and
            int(server1.port) == int(server2.port))


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
                           (default latin1)
        """
        assert not options.get("conn_info") == None
        
        self.verbose = options.get("verbose", False)
        self.db_conn = None
        self.host = None
        self.charset = options.get("charset", "latin1")
        self.role = options.get("role", "Server")
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
        except KeyError:
            raise UtilError("Dictionary format not recognized.")
        self.connect_error = None
        # Set to TRUE when foreign key checks are ON. Check with
        # foreign_key_checks_enabled.
        self.fkeys = None
        self.read_only = False
        self.aliases = []
        self.is_alias("")
        

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


    def is_alias(self, host_or_ip):
        """Determine if host_or_ip is an alias for this host
        
        host_or_ip[in] host or IP number to check
        
        Returns bool - True = host_or_ip is an alias
        """
        from mysql.utilities.common.options import hostname_is_ip
        import socket
        
        if self.aliases:
            return host_or_ip.lower() in self.aliases

        # First, get the local information
        try:
            local_info = socket.gethostbyname_ex(socket.gethostname())
            local_aliases = [local_info[0].lower()]
            # if dotted host name, take first part and use as an alias
            try:
                local_aliases.append(local_info[0].split('.')[0])
            except:
                pass
            local_aliases.extend(['127.0.0.1', 'localhost'])
            local_aliases.extend(local_info[1])
            local_aliases.extend(local_info[2])
        except (socket.herror, socket.gaierror):
            local_aliases = []
        
        # Check for local
        if self.host in local_aliases:
            self.aliases.extend(local_aliases)
        else:
            self.aliases.append(self.host)
            if hostname_is_ip(self.host): # IP address
                try:
                    my_host = socket.gethostbyaddr(self.host)
                    self.aliases.append(my_host[0])
                    host_ip = socket.gethostbyname_ex(my_host[0])
                except Exception, e:
                    host_ip = ([],[],[])
                    if self.verbose:
                        print "WARNING: IP lookup failed", e
            else:
                try:
                    host_ip = socket.gethostbyname_ex(self.host)
                    self.aliases.append(host_ip[0])
                except Exception, e:
                    host_ip = ([],[],[])
                    if self.verbose:
                        print "WARNING: Hostname lookup failed", e

            self.aliases.extend(host_ip[1])
            self.aliases.extend(host_ip[2])

        return host_or_ip.lower() in self.aliases


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
        res = self.exec_query("SELECT host FROM mysql.user WHERE user = '%s' AND '%s' LIKE host " % (user, host_or_ip))
        if res:
            return res[0][0]
        return None
        

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


        Raises UtilError if error during connect
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
            # Reset any previous value if the connection cannot be established,
            # before raising an exception. This prevents the use of a broken
            # database connection.
            self.db_conn = None
            raise UtilError("Cannot connect to the %s server.\n"
                            "Error %s" % (self.role, e.msg), e.errno)
        self.connect_error = None
        self.read_only = self.show_server_variable("READ_ONLY")[0][1]
        

    def disconnect(self):
        """Disconnect from the server.
        """
        try:
            self.db_conn.disconnect()
        except:
            pass


    def get_version(self):
        """Return version number of the server.

        Returns string - version string or None if error
        """
        version_str = None
        try:
            res = self.show_server_variable("VERSION")
            if res:
                version_str = res[0][1]
        except:
            pass
            
        return version_str


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
                cur = self.db_conn.cursor(buffered=True)
        else:
            cur = self.db_conn.cursor(raw=True)

        try:
            if params == ():
                res = cur.execute(query_str)
            else:
                res = cur.execute(query_str, params)
        except mysql.connector.Error, e:
            cur.close()
            raise UtilDBError("Query failed. " + e.__str__())
        except Exception, e:
            cur.close()
            raise UtilError("Unknown error. Command: %s" % query_str)
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
        version_ok = self.check_version_compat(5,6,5)
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
        if not self.supports_gtid() == "ON":
            errors.append("    GTID is not enabled.")
        if not self.check_version_compat(5, 6, 9):
            errors.append("    Server version must be 5.6.9 or greater.")
        res = self.exec_query("SHOW VARIABLES LIKE 'gtid_executed'")
        if res == [] or not res[0][0] == "gtid_executed":
            errors.append("    Missing gtid_executed system variable.")
        if errors:
            errors = "\n".join(errors)
            errors = "\n".join([_GTID_ERROR % (self.host, self.port), errors])
            raise UtilRplError(errors)
            
            
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


    def get_gtid_status(self):
        """Get the GTID information for the server.
        
        This method attempts to retrieve the GTID lists. If the server
        does not have GTID turned on or does not support GTID, the method
        will throw and exception.
        
        Returns [list, list, list]
        """
        # Check servers for GTID support
        if not self.supports_gtid():
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
        
        from mysql.utilities.common.user import User
        
        errors = []
        if host == '127.0.0.1':
            host = 'localhost'
        result = self.user_host_exists(user, host)
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

   
    def foreign_key_checks_enabled(self):
        """Check foreign key status for the connection.
        
        Returns bool - True - foreign keys are enabled
        """
        if self.fkeys is None:
            res = self.show_server_variable("foreign_key_checks")
            self.fkeys = (res is not None) and (res[0][1] == "ON")
        return self.fkeys


    def disable_foreign_key_checks(self, disable=True):
        """Enable or disable foreign key checks for the connection.
        
        disable[in]        if True, turn off foreign key checks
                           elif False turn foreign key checks on
        """
        value = None
        if self.fkeys is None:
            self.foreign_key_checks_enabled()
        if disable and self.fkeys:
            value = "OFF"
        elif not self.fkeys:
            value = "ON"
        if value is not None:
            res = self.exec_query(_FOREIGN_KEY_SET % value, {'fetch':'false'})


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

    
    def get_binary_logs(self, options={}):
        """Return a list of the binary logs.
        
        options[in]        query options
        
        Returns list - binlogs or None if binary logging turned off
        """
        if self.binlog_enabled():
            return self.exec_query("SHOW BINARY LOGS", options)
            
        return None
    

    def set_read_only(self, on=False):
        """Turn read only mode on/off
        
        on[in]         if True, turn read_only ON
                       Default is False
        """
        # Only turn on|off read only if it were off at connect()
        if not self.read_only:
            return self.exec_query("SET @@GLOBAL.READ_ONLY = %s" %
                                   "ON" if on else "OFF")
        return None

