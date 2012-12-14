#!/usr/bin/env python
import os
import mutlib
from mysql.utilities.exception import MUTLibError, UtilDBError
from mysql.utilities.common import tools
from mysql.utilities.exception import UtilError

class test(mutlib.System_test):
    """
    This test executes a script to verify the message for an unsupported server
    It test the message for the unsupported version of the First server passed
    as parameter..
    """

    def check_prerequisites(self):
        fail = None
        if not os.name == "nt":
            fail = True 
        self.old_server = None
        stop = self.servers.num_servers()
        for index in range(0, stop):
            server = self.servers.get_server(index)
            if not server.check_version_compat(5, 1, 21):
                self.old_server = index
        if (fail or 
            self.old_server is None): 
            raise MUTLibError("Test requires one server version prior %s" %
                              "to 5.1.21 and Windows OS ")

        self.server1 = None
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(self.old_server)
        return True
    
    def run(self):
        self.res_fname = "result.txt"
        num_test = 1
        comment = "Test case %s - get_tool mysqld-nt.exe \n" % num_test
        self.results.append(comment)
        try:
            basedir = self.server1.show_server_variable("basedir")
            #setting required=False to verify it founds mysqld-nt.exe 
            res = tools.get_tool_path(basedir[0][1], "mysqld", required=False)
            #ensuring it founds mysqld-nt.exe.           
            if ("mysqld-nt.exe" in res and
                not "Cannot find location of" in res):
                self.results.append("Pass\n")
        except UtilError, exc:
            raise MUTLibError("%s: failed" % comment)
         
        return True
          
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except:
                pass
        return True
