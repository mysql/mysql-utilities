#!/usr/bin/env python

import os
import mutlib

from mysql.utilities.common.server import Server
from mysql.utilities.exception import MUTLibError

class test(mutlib.System_test):
    """clone server parameters
    This test exercises the parameters for mysqlserverclone
    """

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        # No setup needed
        self.new_server = None
        return True

    def _test_server_clone(self, cmd_str, comment, kill=True):
        self.results.append(comment+"\n")
        port1 = int(self.servers.get_next_port())
        cmd_str += " --new-port=%d " % port1
        full_datadir = os.path.join(os.getcwd(), "temp_%s" % port1)
        cmd_str += " --new-data=%s " % full_datadir
        res = self.exec_util(cmd_str, "start.txt")
        for line in open("start.txt").readlines():
            # Don't save lines that have [Warning] or don't start with #
            index = line.find("[Warning]")
            if index <= 0 and line[0] == '#':
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
            'role'      : "cloned_server_2",
        }
        self.new_server = Server(server_options)
        if self.new_server is None:
            return False
        
        if kill:
            # Connect to the new instance
            try:
                self.new_server.connect()
            except MUTLibError, e:
                self.new_server = None
                raise MUTLibError("Cannot connect to spawned server.")
                return False
            self.servers.stop_server(self.new_server)

        self.servers.clear_last_port()

        return True
    
    def run(self):
        self.res_fname = "result.txt"
        base_cmd = "mysqlserverclone.py --server=%s --root-password=root " % \
                    self.build_connection_string(self.servers.get_server(0))
       
        test_cases = [
            # (comment, command options, kill running server)
            ("show help", " --help ", False),
            ("write command to file", " --write-command=startme.sh ", True),
            ("write command to file shortcut", " -w startme.sh ", True),
            ("verbosity = -v", " -v ", True),
            ("verbosity = -vv", " -vv ", True),
            ("verbosity = -vvv", " -vvv ", True),
            ("-vvv and write command to file shortcut",
             " -vvv -w startme.sh ", True),
        ]
        
        test_num = 1
        for row in test_cases:
            new_comment = "Test case %d : %s" % (test_num, row[0])
            if not self._test_server_clone(base_cmd + row[1],
                                           new_comment, row[2]):
                raise MUTLibError("%s: failed" % new_comment)
            test_num += 1

        self.replace_result("#  -uroot", "#  -uroot [...]\n")
        self.replace_result("#                       mysqld:",
                            "#                       mysqld: XXXXXXXXXXXX\n")
        self.replace_result("#                   mysqladmin:",
                            "#                   mysqladmin: XXXXXXXXXXXX\n")
        self.replace_result("#      mysql_system_tables.sql:",
                            "#      mysql_system_tables.sql: XXXXXXXXXXXX\n")
        self.replace_result("# mysql_system_tables_data.sql:",
                            "# mysql_system_tables_data.sql: XXXXXXXXXXXX\n")
        self.replace_result("# mysql_test_data_timezone.sql:",
                            "# mysql_test_data_timezone.sql: XXXXXXXXXXXX\n")
        self.replace_result("#         fill_help_tables.sql:",
                            "#         fill_help_tables.sql: XXXXXXXXXXXX\n")
        
        self.remove_result("# trying again...")
        
        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)

    def _remove_file(self, filename):
        try:
            os.unlink(filename)
        except:
            pass
    
    def cleanup(self):
        files = [self.res_fname, "start.txt", "startme.sh"]
        for file in files:
            self._remove_file(file)
        return True
