#!/usr/bin/env python

import os
import mysql_test

from mysql.utilities.common.server import Server
from mysql.utilities.exception import MySQLUtilError, MUTException

class test(mysql_test.System_test):
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
        self.res_fname = self.testdir + "result.txt"
        cmd_str = "mysqlserverclone.py --server=%s " % \
                  self.build_connection_string(self.servers.get_server(0))
       
        port1 = int(self.servers.get_next_port())
        newport = "--new-port=%d " % port1
        comment = "Test case 1 - show help"
        res = self.run_test_case(0, cmd_str + " --help", comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        comment = "Test case 2 - error: no --new-data option"
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        comment = "Test case 3 - error: no login"
        res = self.run_test_case(1, "mysqlserverclone.py " +
                                 "--server=root:root@nothere --new-data=/nada "
                                 "--new-id=7 " + newport, comment)
        if not res:
            raise MUTException("%s: failed" % comment)
        
        comment = "Test case 4 - error: cannot connect"
        res = self.run_test_case(1, "mysqlserverclone.py --server=root:nope@" +
                                 "nothere --new-data=/nada --new-id=7 " +
                                 "--root-password=nope " + newport,
                                 comment)
        if not res:
            raise MUTException("%s: failed" % comment)

        # Mask known platform-dependent lines
        self.mask_result("Error 2003:", "2003", "####")
        self.replace_result("Error ####: Can't connect to MySQL server",
                            "Error ####: Can't connect to MySQL server"
                            " on 'nothere:####'\n")
       
        cmd_str += "--new-id=%d " % self.servers.get_next_id() + newport + \
                   " --root-password=root "
        comment = "Test case 5 - cannot create directory"
        res = self.run_test_case(1, cmd_str + "--new-data=/not/there/yes",
                                 comment)
        if not res:
            raise MUTException("%s: failed" % comment)
        
        comment = "Test case 6 - clone the current servers[0]"
        full_datadir = os.path.join(os.getcwd(), "temp_%s" % port1)
        cmd_str += "--new-data=%s " % full_datadir
        res = self.exec_util(cmd_str, "start.txt")
        for line in open("start.txt").readlines():
            # Don't save lines that have [Warning]
            index = line.find("[Warning]")
            if index <= 0:
                self.results.append(line)
        if res:
            raise MUTException("%s: failed" % comment)
       
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
        
        self.new_server = Server(conn, "cloned_server")
        if self.new_server is None:
            return False
        
        # Connect to the new instance
        try:
            self.new_server.connect()
        except MySQLUtilError, e:
            self.new_server = None
            raise MUTException("Cannot connect to spawned server.")
            return False
        
        self.replace_result("#  -uroot", "#  -uroot [...]\n")
        
        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
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

