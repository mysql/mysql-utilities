#!/usr/bin/env python

import os
import mutlib
from mysql.utilities.exception import MUTLibError

class test(mutlib.System_test):
    """Process grep
    This test executes the process grep tool on a single server.
    """

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        # Need at least one server.
        self.server1 = None
        self.need_servers = False
        if not self.check_num_servers(2):
            self.need_servers = True
        return self.check_num_servers(1)

    def setup(self):
        num_server = self.servers.num_servers()
        if self.need_servers:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError, e:
                raise MUTLibError("Cannot spawn needed servers: %s" % \
                                   e.errmsg)
        else:
            num_server -= 1 # Get last server in list
        self.server1 = self.servers.get_server(num_server)
        data_file = os.path.normpath("./std_data/basic_data.sql")
        self.drop_all()
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
        except MUTLibError, e:
            raise MUTLibError("Failed to read commands from file %s: " % \
                               data_file + e.errmsg)
        return True
    
    def run(self):
        self.res_fname = "result.txt"
        
        from_conn = self.build_connection_string(self.server1)
        conn_val = self.get_connection_values(self.server1)
        
        cmd = "mysqlprocgrep.py --server=%s " % from_conn
        cmd += " --match-user=%s " % conn_val[0]
        
        test_case_num = 1
        
        _FORMATS = ("CSV","TAB","VERTICAL","GRID")
        for format in _FORMATS:
            comment = "Test case %d - find processes for current user" % \
                      test_case_num + " format=%s" % format
            test_case_num += 1
            cmd += " --format=%s " % format
            res = self.run_test_case(0, cmd, comment)
            if not res:
                raise MUTLibError("%s: failed" % comment)
            self.results.append("\n")

        # CSV masks
        self.mask_column_result("root:*@localhost", ",", 1, "root[...]")
        self.mask_column_result("root[...]", ",", 2, "XXXXX")
        self.mask_column_result("root[...]", ",", 4, "localhost")
        self.mask_column_result("root[...]", ",", 7, "XXXXX")

        # TAB masks
        self.mask_column_result("root:*@localhost", "\t", 1, "root[...]")
        self.mask_column_result("root[...]", "\t", 2, "XXXXX")
        self.mask_column_result("root[...]", "\t", 4, "localhost")
        self.mask_column_result("root[...]", "\t", 7, "XXXXX")
         
        # Vertical masks
        self.replace_result(" Connection: ", " Connection: XXXXX\n")
        self.replace_result("         Id: ", "         Id: XXXXX\n")
        self.replace_result("       Host: ", "       Host: localhost\n")
        self.replace_result("       Time: ", "       Time: XXXXX\n")
        
        # Grid masks
        # Here, we truncate all horizontal bars for deterministic results
        self.replace_result("+---", "+---+\n")
        self.mask_column_result("| root", "|", 2, " root[...]  ")
        self.mask_column_result("| root[...] ", "|", 3, " XXXXX ")
        self.mask_column_result("| root[...] ", "|", 5, " localhost  ")
        self.mask_column_result("| root[...] ", "|", 8, " XXXXX ")
        self.replace_result("| Connection",
                            "| Connection | Id   | User | Host       "
                            "| Db    | Command  | Time  | State      "
                            "| Info [...] |\n")
        
        return True
          
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        try:
            res = server.exec_query("SHOW DATABASES LIKE 'util_%%'")
        except:
            return True # Ok to exit here as there weren't any dbs to drop
        try:
            res = server.exec_query("DROP DATABASE %s" % db)
        except:
            return False
        return True
    
    def drop_all(self):
        try:
            self.drop_db(self.server1, "util_test")
        except:
            return False
        return True

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()




