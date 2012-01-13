#!/usr/bin/env python

import os
import server_info

from mysql.utilities.exception import MUTLibError

class test(server_info.test):
    """check errors for serverinfo
    This test executes a series of error tests using a variety of
    parameters. It uses the server_info test as a parent for setup and teardown
    methods.
    """

    def check_prerequisites(self):
        return server_info.test.check_prerequisites(self)

    def setup(self):
        self.server3 = None
        return server_info.test.setup(self)

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        from_conn2 = "--server=" + self.build_connection_string(self.server2)
        cmd_str = "mysqlserverinfo.py "

        test_num = 1
        comment = "Test case %d - no server" % test_num
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append("\n")

        test_num += 1
        cmd_opts = " --server=xewkjsdd:21"
        comment = "Test case %d - bad server" % test_num
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append("\n")

        cmd_str = "mysqlserverinfo.py %s " % from_conn2

        test_num += 1
        cmd_opts = " --format=ASDASDASD"
        comment = "Test case %d - bad format" % test_num
        res = self.run_test_case(2, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append("\n")

        self.port = int(self.servers.get_next_port())
        res = self.servers.start_new_server(self.server1, 
                                            self.port,
                                            self.servers.get_next_id(),
                                            "root", "temp_server_info")
        self.server3 = res[0]
        if not self.server3:
            raise MUTLibError("%s: Failed to create a new slave." % comment)

        from_conn3 = "--server=" + self.build_connection_string(self.server3)
        cmd_str = "mysqlserverinfo.py %s " % from_conn3

        # Now, stop the server then run verbose test again
        res = self.server3.show_server_variable('basedir')
        self.basedir = res[0][1]
        res = self.server3.show_server_variable('datadir')
        self.datadir3 = res[0][1]
        
        self.servers.stop_server(self.server3, 10, False)
        self.servers.clear_last_port()
        
        test_num += 1
        cmd_opts = " --format=vertical "
        comment = "Test case %d - offline server" % test_num
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)        

        server_info.test.do_replacements(self)
        
        self.replace_result("+---", "+---------+\n")
        self.replace_result("|", "| XXXX ...|\n")
        self.replace_result("localhost:", "localhost:XXXX [...]\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        from mysql.utilities.common.tools import delete_directory
        if self.server3:
            delete_directory(self.datadir3)
            self.server3 = None
        return server_info.test.cleanup(self)
