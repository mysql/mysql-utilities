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
import os
import mutlib

from mysql.utilities.common.server import Server
from mysql.utilities.exception import UtilError, MUTLibError

class test(mutlib.System_test):
    """clone server
    This test clones a server from a single server.
    """

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        # No setup needed
        self.new_server = None
        return True
    
    def check_connect(self, port, full_datadir, name="cloned_server"):

        new_server = None
        # Create a new instance
        conn = {
            "user"   : "root",
            "passwd" : "root",
            "host"   : "localhost",
            "port"   : port,
            "unix_socket" : full_datadir + "/mysql.sock"
        }
        if os.name != "posix":
            conn["unix_socket"] = None
        
        server_options = {
            'conn_info' : conn,
            'role'      : name,
        }
        new_server = Server(server_options)
        if new_server is None:
            return None
        
        # Connect to the new instance
        try:
            new_server.connect()
        except UtilError, e:
            raise MUTLibError("Cannot connect to spawned server.")
        
        return new_server

    def run(self):
        self.server0 = self.servers.get_server(0)
        cmd_str = "mysqlserverclone.py --server=%s --delete-data " % \
                  self.build_connection_string(self.server0)
       
        port1 = int(self.servers.get_next_port())
        cmd_str += " --new-port=%d --root-password=root " % port1

        comment = "Test case 1 - clone a running server"
        self.results.append(comment+"\n")
        full_datadir = os.path.join(os.getcwd(), "temp_%s" % port1)
        cmd_str += "--new-data=%s " % full_datadir
        res = self.exec_util(cmd_str, "start.txt")
        for line in open("start.txt").readlines():
            # Don't save lines that have [Warning]
            if "[Warning]" in line:
                continue
            self.results.append(line)
        if res:
            raise MUTLibError("%s: failed" % comment)
       
        self.new_server = self.check_connect(port1, full_datadir)

        basedir = ""
        # Get basedir
        rows = self.server0.exec_query("SHOW VARIABLES LIKE 'basedir'")
        if not rows:
            raise UtilError("Unable to determine basedir of running server.")

        basedir = rows[0][1]
        port2 = int(self.servers.get_next_port())
        cmd_str = "mysqlserverclone.py --root-password=root --delete-data "
        cmd_str += "--new-port=%d --basedir=%s " % (port2, basedir)

        comment = "Test case 2 - clone a server from basedir"
        self.results.append(comment+"\n")
        full_datadir = os.path.join(os.getcwd(), "temp_%s" % port2)
        cmd_str += "--new-data=%s " % full_datadir
        res = self.exec_util(cmd_str, "start.txt")
        for line in open("start.txt").readlines():
            # Don't save lines that have [Warning]
            if "[Warning]" in line:
                continue
            self.results.append(line)
        if res:
            raise MUTLibError("%s: failed" % comment)
       
        server = self.check_connect(port2, full_datadir,
                                    "cloned_server_basedir")
        
        self.servers.stop_server(server)
        self.servers.clear_last_port()
        
        self.replace_result("#  -uroot", "#  -uroot [...]\n")
        self.replace_result("# Cloning the MySQL server located at",
                            "# Cloning the MySQL server located at XXXX\n")
        
        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        if self.new_server:
            self.servers.add_new_server(self.new_server, True)
        else:
            self.servers.clear_last_port()
        if os.path.exists("start.txt"):
            try:
                os.unlink("start.txt")
            except:
                pass

        return True

