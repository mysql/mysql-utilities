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
import time
import mutlib

from mysql.utilities.exception import MUTLibError


class test(mutlib.System_test):
    """simple db serverinfo
    This test executes the serverinfo utility.
    """

    def check_prerequisites(self):
        # Need at least one server.
        self.server1 = None
        self.server2 = None
        self.need_server = False
        if not self.check_num_servers(2):
            self.need_server = True
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        if self.need_server:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError, e:
                raise MUTLibError("Cannot spawn needed servers: " + e.errmsg)
        self.server2 = self.servers.get_server(1)
        return True

    def do_replacements(self):
        # Mask out this information to make result file deterministic
        self.replace_result("        version:", "        version: XXXX\n")
        self.replace_result("        datadir:", "        datadir: XXXX\n")
        self.replace_result("        basedir:", "        basedir: XXXX\n")
        self.replace_result("     plugin_dir:", "     plugin_dir: XXXX\n")
        self.replace_result("    config_file:", "    config_file: XXXX\n")
        self.replace_result("     binary_log:", "     binary_log: XXXX\n")
        self.replace_result(" binary_log_pos:", " binary_log_pos: XXXX\n")
        self.replace_result("      relay_log:", "      relay_log: XXXX\n")
        self.replace_result("  relay_log_pos:", "  relay_log_pos: XXXX\n")
        self.replace_result("         server: localhost:",
                            "         server: localhost: XXXX\n")

    def start_stop_newserver(self, delete_log=True, stop_server=True):
        port = int(self.servers.get_next_port())
        res = self.servers.start_new_server(self.server1,
                                            port,
                                            self.servers.get_next_id(),
                                            "root", "temp_server_info")
        self.server3 = res[0]
        if not self.server3:
            raise MUTLibError("Failed to create a new slave.")

        from_conn3 = "--server=" + self.build_connection_string(self.server3)
        cmd_str = "mysqlserverinfo.py %s " % from_conn3

        # Now, stop the server then run verbose test again
        res = self.server3.show_server_variable('basedir')
        self.basedir = res[0][1]
        res = self.server3.show_server_variable('datadir')
        self.datadir3 = res[0][1]
        if stop_server:
            self.servers.stop_server(self.server3, 12, False)
        if delete_log:
            self.remove_logs_from_server(self.datadir3)
        self.servers.remove_server(self.server3.role)
        return cmd_str

    def remove_logs_from_server(self, datadir):
        # restarting server fails if log is different, from the original
        # so we will delete them.  
        logs = ["ib_logfile0", "ib_logfile1"]
        while(logs):
            for log in tuple(logs):
                log_file = os.path.join(datadir, log)
                if os.path.exists(log_file):
                    try:
                        os.unlink(log_file)
                        time.sleep(1)
                        if not os.path.exists(log_file):
                            logs.remove(log)
                    except:
                        pass

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        s2_conn = "--server=" + self.build_connection_string(self.server2)

        cmd_str = "mysqlserverinfo.py %s " % s2_conn

        test_num = 1
        comment = "Test case %d - basic serverinfo " % test_num
        cmd_opts = " --format=vertical "
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append("\n")
        self.do_replacements()

        # NOTICE: Cannot test the -d option with a comparative result file
        #         because it is going to be different on every machine.
        #         Thus, this test case will have to be checked independently.
     
        self.res_fname_temp = "result2.txt"

        test_num += 1
        comment = "Test case %d - basic serverinfo with -d option" % test_num
        self.results.append(comment+'\n')
        cmd_opts = " --format=vertical -d "
        res = 0
        try:
            res = self.exec_util(cmd_str + cmd_opts, self.res_fname_temp)
        except MUTLibError, e:
            raise MUTLibError(e.errmsg)
        if res != 0:
            return False
        self.results.append("\n")

        cmd_str = self.start_stop_newserver()
        test_num += 1
        cmd_opts = (' --format=vertical --basedir=%s --datadir=%s --start' % 
                    (self.basedir, self.datadir3))
        comment = ("Test case %d - re-started server %s " % 
                   (test_num, "prints results"))
        #cmd_str_wrong = cmd_str.replace("root:root", "wrong:wrong")
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        time.sleep(2)
        self.do_replacements()
        return True

    def get_result(self):
        # First, check result of test case 2
        found = False
        file = open(self.res_fname_temp, 'r')
        for line in file.readlines():
            if line[0:19] == "Defaults for server":
                found = True
                break
        file.close()
        if self.res_fname_temp:
            os.unlink(self.res_fname_temp)
        if not found:
            raise MUTLibError("Test Case 2 failed. No defaults found.")
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        from mysql.utilities.common.tools import delete_directory
        if self.server3:
            delete_directory(self.datadir3)
            self.server3 = None
        return True




