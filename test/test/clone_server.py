#!/usr/bin/env python

import os
import mysql.utilities.common as mysql_util
import mysql_test

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
        cmd_str = "mysqlserverclone.py %s " % \
                  (self.get_connection_parameters(self.servers.get_server(0)))
       
        newport = "--new-port=%d " % int(self.servers.get_next_port())
        comment = "Test case 1 - show help"
        res = self.run_test_case(0, cmd_str + " --help", comment)
        if not res:
            return False

        comment = "Test case 2 - error: no login"
        res = self.run_test_case(1, "mysqlserverclone.py " +
                                 "-hnothere --new-data=/nada --new-id=7 " +
                                 "--root-password=nope " + newport,
                                 comment)
        if not res:
            return False
        
        comment = "Test case 3 - error: cannot connect"
        res = self.run_test_case(1, "mysqlserverclone.py -uroot -pnope " +
                                 "-hnothere --new-data=/nada --new-id=7 " +
                                 "--root-password=nope " + newport,
                                 comment)
        if not res:
            return False

        # Mask known platform-dependent lines
        self.mask_result("Error 2005:", "(1", '#######')
       
        cmd_str += "--new-id=%d " % self.servers.get_next_id() + newport + \
                   " --root-password=root "
        comment = "Test case 4 - cannot create directory"
        res = self.run_test_case(1, cmd_str + "--new-data=/not/there/yes",
                                 comment)
        if not res:
            return False
        
        comment = "Test case 5 - clone the current servers[0]"
        full_datadir = os.path.join(os.getcwd(), "tempdir1")
        cmd_str += "--new-data=%s " % full_datadir
        res = self.exec_util(cmd_str, "start.txt")
        for line in open("start.txt").readlines():
            # Don't save lines that have [Warning]
            index = line.find("[Warning]")
            if index <= 0:
                self.results.append(line)
        if res:
            return False
       
        self.servers.clear_last_port()
        
        # Create a new instance
        conn = {
            "user"   : "root",
            "passwd" : "root",
            "host"   : "localhost",
            "port"   : int(self.servers.get_next_port()),
            "socket" : full_datadir + "/mysql.sock"
        }
        if os.name != "posix":
            conn["socket"] = None
        
        self.new_server = mysql_util.Server(conn, "clonedserver")
        if self.new_server is None:
            return False
        
        # Connect to the new instance
        try:
            self.new_server.connect()
        except:
            self.new_server = None
            return False
        
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
            os.unlink("start.txt")

        return True

