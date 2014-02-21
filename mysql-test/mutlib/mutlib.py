#
# Copyright (c) 2010, 2014 Oracle and/or its affiliates. All rights reserved.
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
This module contains a test framework for testing MySQL Utilities.
"""

# TODO: Make it possible to stop and delete a specific server from the Server
#       class.

from abc import abstractmethod, ABCMeta
import commands
import difflib
import os
import platform
import re
import string
import subprocess
import tempfile

from mysql.utilities.common.database import Database
from mysql.utilities.common.my_print_defaults import MyDefaultsReader
from mysql.utilities.common.server import stop_running_server, Server
from mysql.utilities.common.table import quote_with_backticks
from mysql.utilities.common.tools import get_tool_path, check_port_in_use
from mysql.utilities.command.serverclone import clone_server

from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import UtilError

# Constants
MAX_SERVER_POOL = 10
MAX_NUM_RETRIES = 50


def _exec_util(cmd, file_out, utildir, debug=False, abspath=False,
               file_in=None):
    """Execute Utility

    This method executes a MySQL utility using the utildir specified in
    MUT. It returns the return value from the completion of the command
    and writes the output to the file supplied.

    cmd[in]            The command to execute including all parameters
    file_out[in]       Path and filename of a file to write output
    utildir[in]        Path to utilities directory
    debug[in]          Prints debug information during execution of
                       utility
    abspath[in]        Use absolute path and not current directory
    file_in[in]        A file-like object for sending data to STDIN

    Returns return value of process run.
    """
    # Support both cmd as string and list
    if isinstance(cmd, list) and abspath is True:
        shell = False
    else:
        shell = True

    if file_in:
        stdin = subprocess.PIPE
    else:
        stdin = None

    if not abspath:
        # Use unbuffered flag to ensure output is not buffered thus preventing
        # issues regarding the order of the output
        run_cmd = "python -u {0}/{1}".format(utildir, cmd)
    else:
        run_cmd = cmd
    with open(file_out, 'w+') as f_out:
        if debug:
            print
            print("exec_util command={0}".format(run_cmd))
            proc = subprocess.Popen(run_cmd, shell=shell, stdin=stdin)
        else:
            proc = subprocess.Popen(run_cmd, shell=shell, stdin=stdin,
                                    stdout=f_out, stderr=f_out)

        if file_in:
            try:
                proc.communicate(''.join(file_in))
            except AttributeError:
                raise MUTLibError("file_in parameter must be "
                                  "a file-like object")

        ret_val = proc.wait()
        if debug:
            print "ret_val=", ret_val
    return ret_val


def get_port(process_id):
    """Returns the port number where the server with pid=process_id is
    accepting new connections

    process_id[in]   The process id (pid) of the process whose listening port
                     we want to find out about

    Returns str - The port number where the server is listening
    """
    plat = platform.system()

    if plat == "Linux":
        cmd = "netstat -anop --tcp | grep {0} | grep LISTEN".format(process_id)
        pid_column = 6
        port_column = 3
    elif plat == "Darwin":
        cmd = "lsof -n -i | grep {0} | grep LISTEN".format(process_id)
        pid_column = 1
        port_column = 7
    elif plat == "Windows":
        cmd = ('netstat -ano | find /I "{0}" | find /I '
               '"LISTEN"'.format(process_id))
        pid_column = 4
        port_column = 1
    else:
        raise MUTLibError("# ERROR: Platform {0} is unsupported".format(plat))
    with tempfile.TemporaryFile() as f:
        ret_code = subprocess.call(cmd, shell=True, stdout=f, stderr=f)
        if not ret_code:  # if it ran successfully
            f.seek(0)
            for line in f:
                try:
                    columns = line.split()
                    #  Getting pid only, because of Linux
                    if columns[pid_column].split('/')[0] == str(process_id):
                        return columns[port_column].rsplit(':', 1)[-1]
                except IndexError:  # we might be reading some warning messages
                    pass
            else:
                # Unable to find the port number
                raise MUTLibError("# ERROR: Unable to retrieve port "
                                  "information")
        else:
            raise MUTLibError("# ERROR: Unable to retrieve port information")


class ServerList(object):
    """The Server_list class is used by the MySQL Utilities Test (MUT)
    facility to gather all the servers used by the tests.

    The following utilities are provided:

        - start/stop a new server
        - shutdown all new servers
        - manage ports and server_ids
    """

    def __init__(self, servers, startport, utildir, verbose=False):
        """Constructor

        servers[in]        List of existing servers (may be None)
        startport[in]      Starting port for spawned servers
        util_dir[in]       Path to utilities directory
        verbose[in]        print extra data during operations (optional)
                           default value = False
        """

        self.cloning_host = "localhost"
        self.utildir = utildir      # Location of utilities being tested
        self.new_port = startport   # Starting port for spawned servers
        self.verbose = verbose      # Option for verbosity
        self.new_id = 100           # Starting server id for spawned servers
        self.server_list = servers  # List of servers available
        self.cleanup_list = []      # List of files to remove at shutdown
        if servers is None:
            self.server_list = []

    def view_next_port(self):
        """View the next available server port but don't consume it.
        """
        return self.new_port

    def get_next_port(self):
        """Get the next available server port.
        """
        new_port, self.new_port = self.new_port, self.new_port + 1
        return new_port

    def clear_last_port(self):
        """Return last port used to available status.
        """
        self.new_port -= 1

    def get_next_id(self):
        """Get the next available server id.
        """
        new_id, self.new_id = self.new_id, self.new_id + 1
        return new_id

    def find_server_by_name(self, name):
        """Retrieve index of the server with the name indicated.

        name[in]            Name of the server (also used as role)

        Note: This finds the first server with the name. Server names are
        not unique.

        Returns -1 if not found, index if found.
        """
        stop = len(self.server_list)
        for index in range(0, stop):
            if self.server_list[index][0].role == name:
                return index
        return -1

    def get_server(self, index):
        """Retrieve the server located at index.

        index[in]           Index (starting at 0)

        Returns - None if index > maximum servers in list or
                  Server class for server at position index
        """
        if index > len(self.server_list):
            return None
        else:
            return self.server_list[index][0]

    def start_new_server(self, cur_server, port, server_id, passwd,
                         role="server", parameters=None):
        """Start a new server with optional parameters

        This method will start a new server with the supplied optional
        parameters using the mysqlserverclone.py utility by cloning the
        server passed. It will also connect to the new server.

        cur_server[in]      Server instance to clone
        port[in]            Port
        server_id[in]       Server id
        password[in]        Root password for new server
        role[in]            Name to give for new server
        parameters[in]      Parameters to use on startup

        Returns tuple (server, msg) [(server, None) | (None, error_str)]:
                    server = Server class instance or None if error
                    msg = None or error message if error
        """
        full_datadir = os.path.join(os.getcwd(), "temp_{0}".format(port))

        # if port is in use, try to get another one which isn't to spawn the
        # new server.
        for i in xrange(port, port+MAX_NUM_RETRIES):
            if check_port_in_use("localhost", i):
                self.new_port = i+1
                port = i
                break
        else:
            raise UtilError("Ports {0} through {1} are in use. Please choose "
                            "an available port"
                            ".".format(port, port + MAX_NUM_RETRIES))

        clone_options = {
            'new_data': full_datadir,
            'new_port': port,
            'new_id': server_id,
            'root_pass': passwd,
            'mysqld_options': parameters,
            'delete': True,
        }
        if self.verbose:
            clone_options['quiet'] = False
            clone_options['verbosity'] = 3
        else:
            clone_options['quiet'] = True
            clone_options['verbosity'] = 0
        connection_params = self.get_connection_parameters(
            cur_server, asdict=True)
        clone_server(connection_params, clone_options)

        # Create a new instance
        conn = {
            "user": "root",
            "passwd": passwd,
            "host": self.cloning_host,
            "port": port,
        }
        # to work properly with ports, we must convert "localhost" to
        # "127.0.0.1"
        if conn["host"] == "localhost":
            conn["host"] = "127.0.0.1"

        server_options = {
            'conn_info': conn,
            'role': role or 'server_{0}'.format(port),
        }

        new_server = Server(server_options)
        # Connect to the new instance
        try:
            new_server.connect()
        except UtilError as err:
            raise MUTLibError("Cannot connect to spawned server: "
                              "{0}".format(err.errmsg))

        # If connected user is not root, clone it to the new instance.
        conn_val = self.get_connection_values(cur_server)
        if conn_val["user"].lower() != "root":
            user_str = conn_val["user"]
            if conn_val.get("passwd") is not None:
                user_str = "{0}:{1}".format(user_str, conn_val["passwd"])
            user_str = "{0}@{1}".format(user_str, conn_val["host"])
            cmd = ("mysqluserclone.py -s --source={0} --destination={1} {2} "
                   "{2}".format(self.get_connection_string(cur_server),
                                self.get_connection_string(new_server),
                                user_str))
            res = _exec_util(cmd, "cmd.txt", self.utildir)
            if res != 0:
                raise MUTLibError("Cannot clone connected user.")

        server = (new_server, None)
        return server

    def stop_server(self, server, wait=10, drop=True):
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

        return stop_running_server(server, wait, drop)

    def spawn_new_servers(self, num_servers):
        """Spawn new servers to match the number needed.

        num_servers[in]    The minimal number of Server objects required

        Returns True - servers available, False - not enough servers
        """

        if int(num_servers) > MAX_SERVER_POOL:
            raise MUTLibError("Request for servers exceeds maximum of "
                              "{0} servers.".format(MAX_SERVER_POOL))
        orig_server = self.server_list[0][0]
        num_to_add = num_servers - len(self.server_list)

        cur_num_servers = self.num_servers()
        for server_num in range(0, num_to_add):
            cur_num_servers += 1
            server = self.start_new_server(orig_server,
                                           self.get_next_port(),
                                           self.get_next_id(), "root")
            datadir = server[0].show_server_variable('datadir')[0][1]
            self.server_list.append((server[0], True,
                                     self.get_process_id(datadir)))

    def spawn_new_server(self, orig_server, server_id, name, mysqld=None):
        """Spawn a new server with options.

        orig_server[in]    Existing server
        server_id[in]      New server id
        name[in]           Name of spawned server
        mysqld[in]         Options for new server

        Returns True - success False - failed
        """
        port1 = self.get_next_port()
        try:
            res = self.start_new_server(orig_server, port1, server_id,
                                        "root", name, mysqld)
        except MUTLibError as err:
            raise MUTLibError("Cannot spawn {0}: {1}".format(name, err.errmsg))

        return res

    def shutdown_spawned_servers(self):
        """Shutdown all spawned servers.
        """
        for server in self.server_list:
            if server[1] and server[0] is not None and server[0].is_alive():
                try:
                    print("  Shutting down server "
                          "{0}...".format(server[0].role)),
                    if self.stop_server(server[0]):
                        print("success.")
                    elif server[2] is not None and server[2] > 1:
                        print("WARN - attempting SIGTERM - pid = "
                              "{0}".format(server[2])),
                        # try signal termination
                        retval = 0
                        if os.name == "posix":
                            try:
                                os.kill(int(server[2]),
                                        subprocess.signal.SIGTERM)
                            except OSError as err:
                                retval = err.errno
                        else:
                            retval = subprocess.call("taskkill /F /T /PID "
                                                     "{0}".format(server[2],
                                                     shell=True))
                        if retval in (0, 128):
                            print("success.")
                    else:
                        print("ERROR")
                except MUTLibError as err:
                    print "ERROR"
                    print("    Unable to shutdown server "
                          "{0}.".format(server[0].role))

    def add_new_server(self, new_server, spawned=False, id_=-1):
        """Add an existing server to the server lists.

        new_server[in]     Server object to add.
        spawned[in]        If True, this is a spawned server
        id[in]             The process id if known
        """
        if new_server is not None:
            if id_ == -1:
                datadir = new_server.show_server_variable("datadir")[0][1]
                id_ = self.get_process_id(datadir)
            self.server_list.append((new_server, spawned, id_))

    def remove_server(self, name):
        """Remove a server from the server lists.

        name[in]           Name (role) of the server to remove.
        """
        index = self.find_server_by_name(name)
        if index == -1:
            return False
        self.server_list.pop(index)
        return True

    def num_servers(self):
        """Return number of servers in the list.
        """
        return len(self.server_list)

    def num_spawned_servers(self):
        """Return number of spawned (new) servers.
        """
        num_spawned_servers = 0
        for server in self.server_list:
            if server[1]:
                num_spawned_servers += 1
        return num_spawned_servers

    def get_connection_values(self, server):
        """Return a dictionary of connection values for a particular server.

        server[in]         A Server object

        Returns dictionary
        """
        return server.get_connection_values()

    def get_connection_parameters(self, server, aslist=False, asdict=False):
        """Return connection parameters for a server.

        Return a string that comprises the normal connection parameters
        common to MySQL utilities for a particular server.

        When aslist is True, the parameters are returned as a list. When
        asdict is True, the parameters are returned as a dictionary.

        server[in]         A Server object

        Returns string
        """
        if asdict:
            return {
                'host': server.host,
                'user': server.user,
                'passwd': server.passwd,
                'socket': server.socket,
                'port': server.port
            }

        if aslist:
            params = [
                '--user={0}'.format(server.user),
                '--host={0}'.format(server.host),
            ]
            if server.passwd:
                params.append('--password={0}'.format(server.passwd))
            if server.socket:
                params.append('--socket={0}'.format(server.socket))
            params.append('--port={0}'.format(server.port))
            return params

        str1 = "--user={0} --host={1} ".format(server.user, server.host)
        if server.passwd:
            str1 = "{0}--password={1} ".format(str1, server.passwd)
        if server.socket:
            str2 = "--socket={0} ".format(server.socket)
        str2 = "--port={0} ".format(server.port)
        return str1 + str2

    def get_connection_string(self, server):
        """Return a string that comprises the normal connection parameters
        common to MySQL utilities for a particular server in the form of
        user:pass@host:port:socket.

        server[in]         A Server object

        Returns string
        """

        conn_str = "{0}".format(server.user)
        if server.passwd:
            conn_str = "{0}:{1}".format(conn_str, server.passwd)
        conn_str = "{0}@{1}:".format(conn_str, server.host)
        if server.port:
            conn_str = "{0}{1}".format(conn_str, server.port)
        if server.socket is not None and server.socket != "":
            conn_str = "{0}:{1} ".format(conn_str, server.socket)
        return conn_str

    def get_process_id(self, datadir):
        """Return process id of new process.

        datadir[in]        The data directory of the process

        Returns (int) process id or -1 if not found
        """
        if os.name == "posix":
            output = commands.getoutput("ps -f|grep mysqld")
            lines = output.splitlines()
            for line in lines:
                proginfo = string.split(line)
                for arg in proginfo[8:]:
                    if arg.find(datadir) >= 0:
                        return proginfo[1]
        return -1

    def add_cleanup_file(self, filename):
        """Add a file to the list of files to cleanup at shutdown.

        filename[in]       The file to remove
        """
        self.cleanup_list.append(filename)

    def remove_files(self):
        """Remove temporary files added during tests.
        """
        for item in self.cleanup_list:
            if item is not None:
                try:
                    os.unlink(item)
                except OSError:
                    pass


class System_test(object):
    """The System_test class is used by the MySQL Utilities Test (MUT) facility
    to perform system tests against MySQL utilities This class is the base
    class from which all tests are derived.

    The following utilities are provided:

        - Execute a utility as a subprocess and return result and populate
          a text file to capture output
        - Check number of servers for a test
        - Check a result file

    To create a test, subclass this class and supply definitions for the
    following abstract methods:

        - check_prerequisites - check conditions for test
        - setup - perform any database setup here
        - run - execute test cases
        - get_result - return result to MUT
        - cleanup - perform any tear down here

    Note: Place test case comments in the class documentation section. This
          will be printed by the --verbose option.
    """
    __metaclass__ = ABCMeta   # Register abstract base class

    def __init__(self, servers, res_dir, utildir, verbose=False, debug=False):
        """Constructor

        servers[in]        A list of Server objects
        res_dir[in]        Path to test result files
        utildir[in]        Path to utility scripts
        verbose[in]        print extra data during operations (optional)
                           default value = False
        debug[in]          Turn on debugging mode for a single test
                           default value = False
        """

        self.res_fname = None       # Name of intermediate result file
        self.results = []           # List for storing results
        self.servers = servers      # ServerList class
        self.res_dir = res_dir      # Current test result directory
        self.utildir = utildir      # Location of utilities being tested
        self.verbose = verbose      # Option for verbosity
        self.debug = debug          # Option for diagnostic work

    def __del__(self):
        """Destructor

        Reset all parameters.
        """
        for result in self.results:
            del result

    def check_gtid_unsafe(self, on=False):
        """Check for gtid enabled base server

        If on is True, method ensures server0 has the server variable
        DISABLE_GTID_UNSAFE_STATEMENTS=ON, else if on is False, method ensures
        server0 does not have DISABLE_GTID_UNSAFE_STATEMENTS=ON.

        Returns bool - False if no DISABLE_GTID_UNSAFE_STATEMENTS variable
                       found, else throws exception if criteria not met.
        """
        if on:
            # Need servers with DISABLE_GTID_UNSAFE_STATEMENTS
            server0 = self.servers.get_server(0)
            res = server0.show_server_variable("DISABLE_GTID_UNSAFE_"
                                                "STATEMENTS")
            if res != [] and res[0][1] != "ON":
                raise MUTLibError("Test requires DISABLE_GTID_UNSAFE_"
                                  "STATEMENTS = ON")
        else:
            # Need servers without DISABLE_GTID_UNSAFE_STATEMENTS
            server0 = self.servers.get_server(0)
            res = server0.show_server_variable("DISABLE_GTID_UNSAFE"
                                               "_STATEMENTS")
            if res != [] and res[0][1] == "ON":
                raise MUTLibError("Test requires DISABLE_GTID_UNSAFE_"
                                  "STATEMENTS = OFF or a server prior to "
                                  "version 5.6.5.")

        return False

    def check_mylogin_requisites(self):
        """ Check if the tools to manipulate mylogin.cnf are accessible.

        This method verifies if the MySQL client tools my_print_defaults and
        mysql_config_editor are accessible.

        A MUTLibError exception is raised if the requisites are not met.
        """
        try:
            self.login_reader = MyDefaultsReader(
                find_my_print_defaults_tool=True)
        except UtilError as err:
            raise MUTLibError("MySQL client tools must be accessible to run "
                              "this test (%s). E.g. Add the location of the "
                              "MySQL client tools to your PATH." % err.errmsg)

        if not self.login_reader.check_login_path_support():
            raise MUTLibError("ERROR: the used my_print_defaults tool does "
                              "not support login-path options. Used tool: "
                              "{0}".format(self.login_reader.tool_path))

        try:
            self.edit_tool_path = get_tool_path(None, "mysql_config_editor",
                                                search_PATH=True)
        except UtilError as err:
            raise MUTLibError("MySQL client tools must be accessible to run "
                              "this test ({0}). E.g. Add the location of the "
                              "MySQL client tools to your "
                              "PATH.".format(err.errmsg))

    def create_login_path_data(self, login_path, user, host, port=None,
                               socket=None):
        """Add the specified login-path data to .mylogin.cnf.

        Execute mysql_config_editor tool to create a new login-path
        entry to the .mylogin.cnf file.

        Note: the use of password is not supported because it is not read from
        the stdin by the tool (apparently for security reasons).
        """

        assert self.edit_tool_path, ("The tool mysql_config_editor is not "
                                     "accessible. First, use method "
                                     "check_mylogin_requisites.")
        # Check version to see if it supports socket and port
        supports_port_and_socket = False
        minimum_version = [5, 6, 11]
        proc = subprocess.Popen([self.edit_tool_path, "--version"],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        if out:
            match = re.search(r'mysql_config_editor(?:\.exe)? ver \d+\.\d+ distrib '
                              r'(\d+\.\d+\.\d+)', out, re.IGNORECASE)
            if match:
                version = map(int, match.group(1).split('.'))
                assert (len(version) == len(minimum_version),
                        "Unsupported version")
                # If current version is greater or equal than 5.6.11 then
                # the tool supports the use of port and socket
                if version >= minimum_version:
                    supports_port_and_socket = True

        cmd = [self.edit_tool_path]
        cmd.append('set')
        cmd.append('--login-path={0}'.format(login_path))
        if host:
            cmd.append('--host={0}'.format(host))
        if user:
            cmd.append('--user={0}'.format(user))

        if supports_port_and_socket:
            if socket:
                cmd.append("--socket={0}".format(socket))
            if port:
                cmd.append("--port={0}".format(port))
        # Create a temporary file to redirect stdout
        out_file = tempfile.TemporaryFile()

        # Execute command to create login-path data
        proc = subprocess.Popen(cmd, stdout=out_file,
                                stdin=subprocess.PIPE)
        # Overwrite login-path if already exists (i.e. answer 'y' to question)
        proc.communicate('y')

    def remove_login_path_data(self, login_path):
        """Remove the specified login-path data from .mylogin.cnf.

        Execute mysql_config_editor tool to remove the specified login-path
        entry from the .mylogin.cnf file.
        """
        assert self.edit_tool_path, ("The tool mysql_config_editor is not "
                                     "accessible. First, use method "
                                     "check_mylogin_requisites.")

        cmd = [self.edit_tool_path]
        cmd.append('remove')
        cmd.append('--login-path={0}'.format(login_path))

        # Create a temporary file to redirect stdout
        out_file = tempfile.TemporaryFile()

        # Execute command to remove login-path data
        if self.verbose:
            subprocess.call(cmd, stdout=out_file)
        else:
            # Redirect stderr to null
            null_file = open(os.devnull, "w+b")
            subprocess.call(cmd, stdout=out_file,
                            stderr=null_file)

    def exec_util(self, cmd, file_out, abspath=False, file_in=None):
        """Execute Utility

        This method executes a MySQL utility using the utildir specified in
        MUT. It returns the return value from the completion of the command
        and writes the output to the file supplied.

        cmd[in]            The command to execute including all parameters
        file_out[in]       Path and filename of a file to write output
        abspath[in]        Use absolute path and not current directory
        file_in[in]        A file-like object for sending data to STDIN

        Returns return value of process run.
        """
        return _exec_util(cmd, file_out, self.utildir, self.debug,
                          abspath, file_in)

    def check_num_servers(self, num_servers):
        """Check the number of servers available.

        num_servers[in]    The minimal number of Server objects required

        Returns True - servers available, False - not enough servers
        """
        if self.servers.num_servers() >= num_servers:
            return True
        return False

    def get_connection_parameters(self, server):
        """Return a string that comprises the normal connection parameters
        common to MySQL utilities for a particular server.

        server[in]         A Server object

        Returns string
        """

        str1 = "--user={0} --host={1} ".format(server.user, server.host)
        if server.passwd:
            str1 = "{0}--password={1} ".format(str1, server.passwd)
        if server.socket:
            str2 = "--socket={0} ".format(server.socket)
        else:
            str2 = "--port={0} ".format(server.port)
        return str1 + str2

    def get_connection_values(self, server):
        """Return a tuple that comprises the connection parameters for a
        particular server.

        server[in]         A Server object

        Returns (user, password, host, port, socket)
        """
        if server is None:
            raise MUTLibError("Server not initialized!")
        return (server.user, server.passwd, server.host,
                server.port, server.socket, server.role)

    def build_connection_string(self, server):
        """Return a connection string

        server[in]         A Server object

        Returns string of the form user:password@host:port
        """
        conn_val = self.get_connection_values(server)
        conn_str = "{0}".format(conn_val[0])
        if conn_val[1]:
            conn_str = "{0}:{1}".format(conn_str, conn_val[1])
        if ":" in conn_val[2] and not "]" in conn_val[2]:
            conn_str = "{0}@[{1}]:".format(conn_str,  conn_val[2])
        else:
            conn_str = "{0}@{1}:".format(conn_str, conn_val[2])
        if conn_val[3]:
            conn_str = "{0}{1}".format(conn_str, conn_val[3])

        return conn_str

    def run_test_case(self, exp_result, command, comments, debug=False):
        """Execute a test case and save the results.

        Call this method to run a test case and save the results to the
        results list.

        exp_result[in]     The expected result (returns True if matches)
        command[in]        Execution command (e.g. ./mysqlclonedb.py --help)
        comments[in]       Comments to put in result list
        debug[in]          Print debug information during execution

        Returns True if result matches expected result
        """
        if self.debug or debug:
            print "\n{0}".format(comments)
        res = self.exec_util(command, self.res_fname)
        if comments:
            self.results.append("{0}\n".format(comments))
        self.record_results(self.res_fname)
        return res == exp_result

    def run_test_case_result(self, command, comments, debug=False):
        """Execute a test case and save the results returning actual result.

        Call this method to run a test case and save the results to the
        results list.

        command[in]        Execution command (e.g. ./mysqlclonedb.py --help)
        comments[in]       Comments to put in result list
        debug[in]          Print debug information during execution

        Returns int - actual result
        """
        if self.debug or debug:
            print "\n{0}".format(comments)
        res = self.exec_util(command, self.res_fname)
        if comments:
            self.results.append("{0}\n".format(comments))
        self.record_results(self.res_fname)
        return res

    def replace_result(self, prefix, replacement_str):
        """Replace a string in the results with a new, deterministic string.

        prefix[in]         starting prefix of string to mask
        replacement_str[in]            replacement string
        """
        linenum = 0
        for line in self.results:
            index = line.find(prefix)
            if index == 0:
                self.results[linenum] = replacement_str
            linenum += 1

    def replace_any_result(self, prefix_list, replacement_str):
        """ If any of the prefixes in prefix_list is found on a line from
        the results, that line is replaced with replacement_str.

        prefix_list[in]      list of starting prefixes of strings to mask
        replacement_str[in]  Replacement string
        """
        for linenum, line in enumerate(self.results):
            for prefix in prefix_list:
                index = line.find(prefix)
                if index == 0:
                    self.results[linenum] = replacement_str
                    break

    def remove_result(self, prefix):
        """Remove a string in the results.

        prefix[in]         starting prefix of string to mask
        """
        linenums = []
        linenum = 0
        for line in self.results:
            index = line.find(prefix)
            if index == 0:
                linenums.append(linenum)
            linenum += 1
        # Must remove lines in reverse order
        for linenum in reversed(linenums):
            self.results.pop(linenum)

    def remove_many_result(self, prefix_list):
        """ If any of the prefixes in prefix_list is found on a line on
        the results, removes that line from the results

        prefix_list[in]      list of starting prefixes of strings remove
        """
        linenums = []
        for linenum, line in enumerate(self.results):
            for prefix in prefix_list:
                index = line.find(prefix)
                if index == 0:
                    linenums.append(linenum)
                    break
        # Remove lines in reverse order
        for linenum in reversed(linenums):
            self.results.pop(linenum)

    def remove_result_and_lines_before(self, prefix, lines=1):
        """Remove lines in the results with lines before prefix.

        prefix[in]         starting prefix of string to mask
        lines[in]          number of lines to remove previously
                           to the prefix line.
        """
        linenums = []
        linenum = 0
        for line in self.results:
            index = line.find(prefix)
            if index == 0:
                linenums.append(int(linenum))
                for line2rm in range(linenum-lines, linenum):
                    if line2rm > - 1:
                        linenums.append(int(line2rm))
            linenum += 1
        linenums.sort()
        # Must remove lines in reverse order
        for linenum in range(len(linenums) - 1, - 1, - 1):
            self.results.pop(linenums[linenum])

    def remove_result_and_lines_after(self, prefix, lines=0):
        """Remove lines in the results and lines after prefix.

        prefix[in]         starting prefix of string to mask
        lines[in]          number of lines to remove after the prefix line.
        """
        linenums = []
        linenum = 0
        del_lines = 9999999
        for line in self.results:
            index = line.find(prefix)
            if index == 0:
                linenums.append(int(linenum))
                del_lines = 0
            elif del_lines < lines:
                linenums.append(int(linenum))
                del_lines += 1
            linenum += 1
        # Must remove lines in reverse order
        for linenum in range(len(linenums) - 1, - 1, - 1):
            self.results.pop(linenums[linenum])

    def replace_substring(self, target, replacement):
        """Replace a target substring in the entire result file.

        target[in]         target string to replace
        replacement[in]    string to replace
        """
        linenum = 0
        for line in self.results:
            if line.find(target) >= 0:
                self.results.pop(linenum)
                replace_line = line.replace(target, replacement)
                self.results.insert(linenum, replace_line)
            linenum += 1

    def replace_substring_portion(self, substring_start, substring_end,
                                  replacement):
        """Replace a sub-string in all results specifying its start and end.

        This method replaces a sub-string portion in all result lines,
        specifying its start and end (without requiring any specific prefix).
        This allow the substitution of non deterministic sub-strings, with a
        variable value/text in the middle but surrounded by known and fixed
        sub-strings.

        substring_start[in] start of the substring to be replaced.
        substring_end[in]   end of the substring to be replaced.
        replacement[in]     replacing string.
        """
        for i, line in enumerate(self.results):
            # Search for the substring portion start.
            start_idx = line.find(substring_start)
            if start_idx != -1:  # Substring start found
                # Search for the substring portion end.
                next_search_idx = start_idx + len(substring_start)
                substr_end_idx = line.find(substring_end, next_search_idx)
                if substr_end_idx != -1:  # Substring end found.
                    # Get substring portion and replace it.
                    end_idx = substr_end_idx + len(substring_end)
                    substr_portion = line[start_idx:end_idx]
                    self.results[i] = line.replace(substr_portion, replacement)

    def mask_result(self, prefix, target, mask):
        """Mask out a portion of a string for the results.

        str[in]            string to mask
        prefix[in]         starting prefix of string to mask
        target[in]         substring to search for to mask
        mask[in]           mask string (e.g. '######")
        """
        linenum = 0
        for line in self.results:
            index = line.find(prefix)
            if index == 0:
                loc = line.find(target)
                if loc >= 0:
                    start = loc + len(mask)
                    self.results.pop(linenum)
                    if start > len(line):
                        self.results.insert(linenum,
                                            line[0:loc] + mask + "\n")
                    else:
                        self.results.insert(linenum,
                                            line[0:loc] + mask + line[start:])
            linenum += 1

    def mask_result_portion(self, prefix, target, end_target, mask):
        """Mask out a portion of a string for the results using
        a end target to make the masked area a specific length.

        str[in]            string to mask
        prefix[in]         starting prefix of string to mask
        target[in]         substring to search for to mask
        end_target[in]     substring to mark end of mask
        mask[in]           mask string (e.g. '######")
        """
        linenum = 0
        for line in self.results:
            index = line.find(prefix)
            if index == 0:
                loc = line.find(target)
                if loc >= 0:
                    end = line.find(end_target)
                    if end >= 0:
                        self.results.pop(linenum)
                        if end > len(line):
                            self.results.insert(linenum,
                                                line[0:loc] + mask + "\n")
                        else:
                            self.results.insert(linenum,
                                                line[0:loc] + mask +
                                                line[end:])
            linenum += 1

    def mask_column_result(self, prefix, separator, num_col, mask):
        """Mask out a column portion of a string for the results.

        str[in]            string to mask
        prefix[in]         starting prefix of string to mask
        separator[in]      separator for columns (e.g. ',')
        num_col[in]        number of column to mask
        mask[in]           mask string (e.g. '######")
        """
        linenum = 0
        for line in self.results:
            index = line.find(prefix)
            if index == 0:
                pos = 0
                for i in range(0, num_col):
                    loc = line.find(separator, pos)
                    if i+1 == num_col:
                        next_ = line.find(separator, loc)
                        if next_ < 0:
                            start = len(line)
                        else:
                            start = next_
                        self.results.pop(linenum)
                        if start >= len(line):
                            self.results.insert(linenum,
                                                line[0:pos] + mask + "\n")
                        else:
                            self.results.insert(linenum,
                                                line[0:pos] + mask +
                                                line[start:])
                    else:
                        pos = loc + 1
                    if loc < 0:
                        break
            linenum += 1

    def check_objects(self, server, db, events=True):
        """Check number of objects.

        Creates a string containing the number of objects for a given database.

        server[in]         Server object to query
        db[in]             name of database to check

        Returns string
        """
        db_source = Database(server, db)
        db_source.init()
        res = db_source.get_db_objects("TABLE")
        str_ = "OBJECT COUNTS: tables = %s, " % (len(res))
        res = db_source.get_db_objects("VIEW")
        str_ += "views = %s, " % (len(res))
        res = db_source.get_db_objects("TRIGGER")
        str_ += "triggers = %s, " % (len(res))
        res = db_source.get_db_objects("PROCEDURE")
        str_ += "procedures = %s, " % (len(res))
        res = db_source.get_db_objects("FUNCTION")
        str_ += "functions = %s, " % (len(res))
        if events:
            res = db_source.get_db_objects("EVENT")
            str_ += "events = %s \n" % (len(res))
        return str_

    def compare(self, name, actual):
        """Compare an actual set of return values to the result file
        for this test.

        name[in]           test name (use __name__)
        actual[in]         String list of the actual results

        Returns: (bool, diff) where:
            (True, None) = results identical
            (False, "result file missing") = result file missing
            (False, <string list>) = results differ
        """
        #
        # Check to see if result file exists first.
        #
        res_fname = os.path.normpath(os.path.join(self.res_dir,
                                                  "{0}.result".format(name)))
        if not os.access(res_fname, os.F_OK):
            actual.insert(0, "Result file missing - actual results:\n\n")
            return False, actual

        #
        # Use ndiff to compare to known result file
        #
        res_file = open(res_fname)
        diff = difflib.ndiff(res_file.readlines(), actual)
        #
        # Now convert the diff to a string list and write reject file
        #
        rej_fname = os.path.normpath(os.path.join(self.res_dir,
                                                  "{0}.reject".format(name)))
        rej_file = open(rej_fname, 'w+')
        rej_list = []
        try:
            while 1:
                str_ = diff.next()
                if str_[0] in ['-', '+', '?']:
                    rej_list.append(str_)
                rej_file.write(str_)
        except StopIteration:
            pass
        rej_file.close()

        # Write preamble if there are differences
        if not rej_list == []:
            rej_list.insert(0, "Result file mismatch:\n")

        # If test passed, delete the reject file if it exists
        elif os.access(rej_fname, os.F_OK):
            os.unlink(rej_fname)

        return rej_list == [], rej_list

    def record_results(self, fname):
        """Saves the results from a file to the self.results list.

        fname[in]          Name of results file from exec_util
        """
        f_res = open(fname)
        for line in f_res.readlines():
            self.results.append(line)
        f_res.close()

    def save_result_file(self, name, results):
        """Saves a result file for the test.

        name[in]           Test name (use __name__)
        results[in]        String list of the results

        Returns True - success, False - fail
        """
        if results:
            res_fname = os.path.normpath(os.path.join(self.res_dir, name +
                                                      ".result"))
            res_file = open(res_fname, 'w+')
            if not res_file:
                return False
            for str_ in results:
                res_file.write(str_)
            res_file.close()
        return True

    def is_long(self):
        """Is test marked as a long running test?

        Override this method to specify the test is a long-running test.
        """
        return False

    def kill_server(self, name):
        """This method kill (i.e. stop and remove) the referred server.

            name[in]    Name of the server to kill.

            Returns True if the server was found and killed successfully,
            otherwise False.
        """
        index = self.servers.find_server_by_name(name)
        if index >= 0:
            server = self.servers.get_server(index)
            if self.debug:
                print "# Killing server {0}.".format(server.role)
            self.servers.stop_server(server)
            self.servers.remove_server(server.role)
            return True
        else:
            if self.debug:
                print "# Kill failed! Server '{0}' was not found.".format(name)
            return False

    def kill_server_list(self, servers):
        """Stop (kill) a list of servers and remove from list.

        servers[in]     List of servers (by role) to kill

        Returns - results of calling kill_server() for each server in list
        """
        kill_results = [self.kill_server(srv_role) for srv_role in servers]
        return all(kill_results)

    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        res = server.exec_query("SHOW DATABASES LIKE '{0}'".format(db))
        if not res:
            return True  # Ok to exit here as there weren't any dbs to drop
        try:
            q_db = quote_with_backticks(db)
            server.exec_query("DROP DATABASE {0}".format(q_db))
        except UtilError:
            return False
        return True

    @abstractmethod
    def check_prerequisites(self):
        """Check prerequisites for test.

        This method is used to check any prerequisites for a test such as
        the number of servers needed, environment variables, etc.

        Returns: True = servers available, False = not enough servers, skip
        """
        pass

    @abstractmethod
    def setup(self):
        """Setup conditions for test.

        This method is used to setup any conditions for a test such as
        loading test data or setting server variables.

        Note: if setup fails, cleanup() is still called. Consider this
              when implementing complex setup procedures.

        Returns: True = no errors, False = errors, skip test
        """
        pass

    @abstractmethod
    def run(self):
        """Execute a test.

        This method is used to execute the test cases in the test. One or
        more calls to exec_util() may be performed here, but results are
        saved here and checked later.

        Returns: True = no errors, False = errors occurred
        """
        pass

    @abstractmethod
    def get_result(self):
        """Return results of test to MUT.

        This method is used to decided if the test passed. It is in this
        method where the results of the run() method are checked. This
        allows separation of the evaluation of the test form the execution
        and other steps.

        Returns: tuple (bool, string list) where:
            (True, None) = test passed
            (False, <string list>) - test failed. String list to be displayed

            Note: Formatting for string list should be done by the callee.
                  The caller prints exactly what is returned.
        """
        pass

    @abstractmethod
    def record(self):
        """Record test results for comparison.

        This method is used to record any test results for a result compare-
        type test. To do so, call self.save_result_file(__name__, strlist)
        where strlist is the output the test will compare to determine
        success.

        Note: If your test is not a comparative test, you can simply return
              True (success). In this case, the --record option has no effect.

        Returns: True - success, False - error
        """
        pass

    @abstractmethod
    def cleanup(self):
        """Perform any post-test cleanup.

        This method is used to remove the setup conditions from the server.

        Returns: True = no errors, False = errors occurred
        """
        pass
