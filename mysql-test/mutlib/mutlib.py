#
# Copyright (c) 2010, 2013 Oracle and/or its affiliates. All rights reserved.
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
import string
import subprocess
import tempfile

from mysql.utilities.common.my_print_defaults import MyDefaultsReader
from mysql.utilities.common.my_print_defaults import my_login_config_path
from mysql.utilities.common.tools import get_tool_path

from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import UtilDBError
from mysql.utilities.exception import UtilError


# Constants
MAX_SERVER_POOL = 10

def _exec_util(cmd, file_out, utildir, debug=False, abspath=False):
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
    
    Returns return value of process run.
    """
    if not abspath:
        run_cmd = "python " + utildir + "/" + cmd
    else:
        run_cmd = cmd
    f_out = open(file_out, 'w+')
    if debug:
        print 
        print "exec_util command=", run_cmd
        proc = subprocess.Popen(run_cmd, shell=True)
    else:
        proc = subprocess.Popen(run_cmd, shell=True,
                                stdout = f_out, stderr = f_out)
    ret_val = proc.wait()
    if debug:
        print "ret_val=", ret_val
    f_out.close()
    return ret_val


class Server_list(object):
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
        new_port = self.new_port
        self.new_port += 1
        return new_port


    def clear_last_port(self):
        """Return last port used to available status.
        """
        self.new_port -= 1
        
        
    def get_next_id(self):
        """Get the next available server id.
        """
        new_id = self.new_id
        self.new_id += 1
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
        
        from mysql.utilities.common.server import Server
                    
        new_server = (None, None)
        
        # Set data directory for new server so that it is unique
        full_datadir = os.getcwd() + "/temp_%s" % port
        
        # Attempt to clone existing server
        cmd = "mysqlserverclone.py --delete-data --server="
        cmd += self.get_connection_string(cur_server)
        if passwd:
           cmd += " --root-password=%s " % passwd
        cmd += " --new-port=%s " % port
        cmd += "--new-id=%s " % server_id
        cmd += "--new-data=%s " % os.path.normpath(full_datadir)
        if parameters is not None:
            cmd += "--mysqld=%s" % parameters
            
        res = _exec_util(cmd, "cmd.txt", self.utildir)
        
        # Create a new instance
        conn = {
            "user"   : "root",
            "passwd" : passwd,
            "host"   : "localhost",
            "port"   : port,
            "unix_socket" : full_datadir + "/mysql.sock"
        }
        if os.name != "posix":
            conn["unix_socket"] = None
            
        server_options = {
            'conn_info' : conn,
            'role'      : role,
        }
        self.new_server = Server(server_options)
        
        server = (self.new_server, None)

        # Connect to the new instance
        try:
            self.new_server.connect()
        except UtilError, e:
            raise MUTLibError("Cannot connect to spawned server: %s" % \
                               e.errmsg)
            
        # If connected user is not root, clone it to the new instance.
        conn_val = self.get_connection_values(cur_server)
        if conn_val["user"].lower() != "root":
            user_str = conn_val["user"]
            if conn_val.get("passwd") is not None:
                user_str += ":%s" % conn_val["passwd"]
            user_str += "@%s" % conn_val["host"]
            cmd = "mysqluserclone.py -s --source=%s --destination=%s" % \
                  (self.get_connection_string(cur_server),
                   self.get_connection_string(self.new_server)) + \
                  "%s %s" % (user_str, user_str)
            res = _exec_util(cmd, "cmd.txt", self.utildir)
            if res != 0:
                raise MUTLibError("Cannot clone connected user.")

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
        
        from mysql.utilities.common.tools import delete_directory

        # Build the shutdown command
        cmd = ""
        res = server.show_server_variable("basedir")
        mysqladmin_client = "mysqladmin"
        if not os.name == "posix":
            mysqladmin_client = "mysqladmin.exe"
        mysqladmin_path= os.path.normpath(os.path.join(res[0][1], "bin",
                                                   mysqladmin_client))
        if not os.path.exists(mysqladmin_path):
            mysqladmin_path= os.path.normpath(os.path.join(res[0][1], "client",
                                                       mysqladmin_client))
        if not os.path.exists(mysqladmin_path) and not os.name == 'posix':
            mysqladmin_path= os.path.normpath(os.path.join(res[0][1],
                                                       "client/debug",
                                                       mysqladmin_client))
        if not os.path.exists(mysqladmin_path) and not os.name == 'posix':
            mysqladmin_path= os.path.normpath(os.path.join(res[0][1],
                                                       "client/release",
                                                       mysqladmin_client))
        cmd += mysqladmin_path
        cmd += " shutdown "
        cmd += self.get_connection_parameters(server)
        res = server.show_server_variable("datadir")
        datadir = res[0][1]

        # Kill all connections so shutdown will work correctly
        res = server.exec_query("SHOW PROCESSLIST")
        for row in res:
            if not row[7] or not row[7].upper().startswith("SHOW PROCESS"):
                try:
                    server.exec_query("KILL CONNECTION %s" % row[0])
                except UtilDBError: # Ok to ignore KILL failures
                    pass

        # disconnect user
        server.disconnect()
        
        # Stop the server
        file = os.devnull
        f_out = open(file, 'w')
        proc = subprocess.Popen(cmd, shell=True, 
                                stdout = f_out, stderr = f_out)
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

    
    def spawn_new_servers(self, num_servers):
        """Spawn new servers to match the number needed.
        
        num_servers[in]    The minimal number of Server objects required
        
        Returns True - servers available, False - not enough servers
        """

        if int(num_servers) > MAX_SERVER_POOL:
            raise MUTLibError("Request for servers exceeds maximum of " \
                                 "%d servers." % MAX_SERVER_POOL)
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
        port1 = int(self.get_next_port())
        try:
            res = self.start_new_server(orig_server, port1, server_id,
                                        "root", name, mysqld)
        except MUTLibError, e:
            raise MUTLibError("Cannot spawn %s: %s" % (name, e.errmsg))

        return res


    def shutdown_spawned_servers(self):
        """Shutdown all spawned servers.
        """
        import subprocess
        for server in self.server_list:
            if server[1] and server[0] is not None and server[0].is_alive():
                try:
                    print "  Shutting down server %s..." % server[0].role,
                    if self.stop_server(server[0]):
                        print "success."
                    elif server[2] is not None and server[2] > 1:
                        print "WARN - attempting SIGTERM - pid = %s" % server[2] 
                        # try signal termination
                        if os.name == "posix":
                            retval = os.kill(int(server[2]),
                                             subprocess.signal.SIGTERM)
                        else:
                            retval = subprocess.Popen("taskkill /F /T /PID %i" %
                                                      int(server[2]),
                                                      shell=True)
                    else:
                        print "ERROR"
                except MUTLibError, e:
                    print "ERROR"
                    print "    Unable to shutdown server %s." % server[0].role
            
            
    def add_new_server(self, new_server, spawned=False, id=-1):
        """Add an existing server to the server lists.

        new_server[in]     Server object to add.
        spawned[in]        If True, this is a spawned server
        id[in]             The process id if known
        """
        if new_server is not None:
            if id == -1:
                datadir = new_server.show_server_variable("datadir")[0][1]
                id = self.get_process_id(datadir)
            self.server_list.append((new_server, spawned, id))


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


    def get_connection_parameters(self, server):
        """Return a string that comprises the normal connection parameters
        common to MySQL utilities for a particular server.
        
        server[in]         A Server object
        
        Returns string
        """

        str1 = "--user=%s --host=%s " % (server.user, server.host)
        if server.passwd:
            str1 += "--password=%s " % server.passwd
        if server.socket:
            str2 = "--socket=%s " % (server.socket)
        else:
            str2 = "--port=%s " % (server.port)
        return str1 + str2
        

    def get_connection_string(self, server):
        """Return a string that comprises the normal connection parameters
        common to MySQL utilities for a particular server in the form of
        user:pass@host:port:socket.
        
        server[in]         A Server object
        
        Returns string
        """

        conn_str = "%s" % server.user
        if server.passwd:
            conn_str += ":%s" % server.passwd
        conn_str += "@%s:" % server.host
        if server.port:
            conn_str += "%s" % server.port
        if server.socket is not None and server.socket != "":
            conn_str += ":%s " % server.socket
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
                except:
                    pass
                

class System_test(object):
    """The System_test class is used by the MySQL Utilities Test (MUT) facility
    to perform system tests against MySQL utilitites. This class is the base
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
        utildir[in]        Path to utilty scripts 
        verbose[in]        print extra data during operations (optional)
                           default value = False
        debug[in]          Turn on debugging mode for a single test
                           default value = False
        """
        
        self.res_fname = None       # Name of intermediate result file
        self.results = []           # List for storing results
        self.servers = servers      # Server_list class
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

            
    def check_gtid_unsafe(self, on = False):
        """Check for gtid enabled base server
        
        If on is True, method ensures server0 has the server variable
        DISABLE_GTID_UNSAFE_STATEMENTS=ON, else if on is False, method ensures
        server0 does not have DISABLE_GTID_UNSAFE_STATEMENTS=ON.
        
        Returns bool - False if no DISABE_GTID_UNSAFE_STATEMENTS variable
                       found, else throws exception if criteria not met.
        """
        if on:
            # Need servers with DISABLE_GTID_UNSAFE_STATEMENTS
            self.server0 = self.servers.get_server(0)
            res = self.server0.show_server_variable("DISABLE_GTID_UNSAFE_"
                                                    "STATEMENTS")
            if res != [] and res[0][1] != "ON":
                raise MUTLibError("Test requires DISABLE_GTID_UNSAFE_STATEMENTS"
                                  " = ON")
        else:
            # Need servers without DISABLE_GTID_UNSAFE_STATEMENTS
            self.server0 = self.servers.get_server(0)
            res = self.server0.show_server_variable("DISABLE_GTID_UNSAFE_"
                                                    "STATEMENTS")
            if res != [] and res[0][1] == "ON":
                raise MUTLibError("Test requires DISABLE_GTID_UNSAFE_STATEMENTS"
                                  " = OFF or a server prior to version 5.6.5.")

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
            raise MUTLibError("ERROR: the used my_print_defaults tool does not "
                            "support login-path options. Used tool: %s"
                            % self.login_reader.tool_path)

        try:
            self.edit_tool_path = get_tool_path(None, "mysql_config_editor",
                                                search_PATH=True)
        except UtilError as err:
            raise MUTLibError("MySQL client tools must be accessible to run "
                              "this test (%s). E.g. Add the location of the "
                              "MySQL client tools to your PATH." % err.errmsg)

    def create_login_path_data(self, login_path, user, host):
        """Add the specified login-path data to .mylogin.cnf.

        Execute mysql_config_editor tool to create a new login-path
        entry to the .mylogin.cnf file.

        Note: the use of password is not supported because it is not read from
        the stdin by the tool (apparently for security reasons).
        """

        assert self.edit_tool_path, ("The tool mysql_config_editor is not "
                                     "accessible. First, use method "
                                     "check_mylogin_requisites.")

        cmd = [self.edit_tool_path]
        cmd.append('set')
        cmd.append('--login-path=%s' % login_path)
        cmd.append('--host=%s' % host)
        cmd.append('--user=%s' % user)

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
        cmd.append('--login-path=%s' % login_path)

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

    def exec_util(self, cmd, file_out, abspath=False):
        """Execute Utility
        
        This method executes a MySQL utility using the utildir specified in
        MUT. It returns the return value from the completion of the command
        and writes the output to the file supplied.
        
        cmd[in]            The command to execute including all parameters
        file_out[in]       Path and filename of a file to write output
        abspath[in]        Use absolute path and not current directory
        
        Returns return value of process run.
        """
        return _exec_util(cmd, file_out, self.utildir, self.debug, abspath)
    

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

        str1 = "--user=%s --host=%s " % (server.user, server.host)
        if server.passwd:
            str1 += "--password=%s " % server.passwd
        if server.socket:
            str2 = "--socket=%s " % (server.socket)
        else:
            str2 = "--port=%s " % (server.port)
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
        
        Returns string of the form user:password@host:port:socket
        """
        conn_val = self.get_connection_values(server)
        conn_str = "%s" % conn_val[0]
        if conn_val[1]:
            conn_str += ":%s" % conn_val[1]
        conn_str += "@%s:" % conn_val[2]
        if conn_val[3]:
            conn_str += "%s" % conn_val[3]
        if conn_val[4] is not None and conn_val[4] != "":
            conn_str += ":%s " % conn_val[4]

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
            print "\n%s" % comments
        res = self.exec_util(command, self.res_fname)
        if comments:
            self.results.append(comments + "\n")
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
            print "\n%s" % comments
        res = self.exec_util(command, self.res_fname)
        if comments:
            self.results.append(comments + "\n")
        self.record_results(self.res_fname)
        return res


    def replace_result(self, prefix, str):
        """Replace a string in the results with a new, deterministic string.

        prefix[in]         starting prefix of string to mask
        str[in]            replacement string
        """
        linenum = 0
        for line in self.results:
            index = line.find(prefix)
            if index == 0:
                self.results.pop(linenum)
                self.results.insert(linenum, str)
            linenum += 1

    
    def remove_result(self, prefix):
        """Remove a string in the results.

        prefix[in]         starting prefix of string to mask
        """
        linenums = []
        linenum = 0
        for line in self.results:
            index = line.find(prefix)
            if index == 0:
                linenums.append(int(linenum))
            linenum += 1
        # Must remove lines in reverse order
        for linenum in range(len(linenums)-1, -1, -1):
            self.results.pop(linenums[linenum])

    def remove_result_and_lines_before(self, prefix, lines=1):
        """Remove lines in the results.
    
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
                for line2rm in range(linenum-lines,linenum):
                    if line2rm > - 1:
                        linenums.append(int(line2rm))
            linenum += 1
        linenums.sort()
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
            if line.find(target):
                self.results.pop(linenum)
                replace_line = line.replace(target, replacement)
                self.results.insert(linenum, replace_line)
            linenum += 1

 
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
                        next = line.find(separator, loc)
                        if next < 0:
                            start = len(line)
                        else:
                            start = next
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

        from mysql.utilities.common.database import Database

        db_source = Database(server, db)
        db_source.init()
        res = db_source.get_db_objects("TABLE")
        str = "OBJECT COUNTS: tables = %s, " % (len(res))
        res = db_source.get_db_objects("VIEW")
        str += "views = %s, " % (len(res))
        res = db_source.get_db_objects("TRIGGER")
        str += "triggers = %s, " % (len(res))
        res = db_source.get_db_objects("PROCEDURE")
        str += "procedures = %s, " % (len(res))
        res = db_source.get_db_objects("FUNCTION")
        str += "functions = %s, " % (len(res))
        if events:
            res = db_source.get_db_objects("EVENT")
            str += "events = %s \n" % (len(res))
        return str


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
        res_fname = os.path.normpath(os.path.join(self.res_dir, name + ".result"))
        if not os.access(res_fname, os.F_OK):
            actual.insert(0, "Result file missing - actual results:\n\n")
            return (False, actual)
            
        #
        # Use ndiff to compare to known result file
        #
        res_file = open(res_fname)
        diff = difflib.ndiff(res_file.readlines(), actual)
        #
        # Now convert the diff to a string list and write reject file
        #
        rej_fname = os.path.normpath(os.path.join(self.res_dir, name + ".reject"))
        rej_file = open(rej_fname, 'w+')
        rej_list = []
        try:
            while 1:
                str = diff.next()
                if str[0] in ['-', '+', '?']:
                    rej_list.append(str)
                rej_file.write(str)
        except:
            pass
        rej_file.close()

        # Write preamble if there are differences
        if not rej_list == []:
            rej_list.insert(0, "Result file mismatch:\n")
        
        # If test passed, delete the reject file if it exists
        elif os.access(rej_fname, os.F_OK):
            os.unlink(rej_fname)
            
        return (rej_list == [], rej_list)

        
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
            for str in results:
                res_file.write(str)
            res_file.close()
        return True
    
    def is_long(self):
        """Is test marked as a long running test?
        
        Override this method to specify the test is a long-running test.
        """
        return False

    
    @abstractmethod
    def check_prerequisites(self):
        """Check preprequisites for test.
        
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

