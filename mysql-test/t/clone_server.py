#!/usr/bin/env python

import os
import mutlib

from mysql.utilities.common.server import Server
from mysql.utilities.exception import MUTLibError

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
    
    def run(self):
        cmd_str = "mysqlserverclone.py --server=%s " % \
                  self.build_connection_string(self.servers.get_server(0))
       
        port1 = int(self.servers.get_next_port())
        cmd_str += " --new-port=%d --root-password=root " % port1

        comment = "Test case 1 - clone the current servers[0]"
        self.results.append(comment+"\n")
        full_datadir = os.path.join(os.getcwd(), "temp_%s" % port1)
        cmd_str += "--new-data=%s " % full_datadir
        res = self.exec_util(cmd_str, "start.txt")
        for line in open("start.txt").readlines():
            # Don't save lines that have [Warning]
            index = line.find("[Warning]")
            if index <= 0:
                self.results.append(line)
        if res:
            raise MUTLibError("%s: failed" % comment)
       
        # Create a new instance
        conn = {
            "user"   : "root",
            "passwd" : "root",
            "host"   : "localhost",
            "port"   : port1,
            "unix_socket" : full_datadir + "/mysql.sock"
        }
        if os.name != "posix":
            conn["unix_socket"] = None
        
        server_options = {
            'conn_info' : conn,
            'role'      : "cloned_server",
        }
        self.new_server = Server(server_options)
        if self.new_server is None:
            return False
        
        # Connect to the new instance
        try:
            self.new_server.connect()
        except MUTLibError, e:
            self.new_server = None
            raise MUTLibError("Cannot connect to spawned server.")
            return False
        
        self.replace_result("#  -uroot", "#  -uroot [...]\n")
        
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

