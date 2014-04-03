#
# Copyright (c) 2010, 2014, Oracle and/or its affiliates. All rights reserved.
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
rpl_admin_parameters test.
"""

import os

import mutlib
import rpl_admin

from mysql.utilities.exception import MUTLibError


_LOGNAME = "temp_log.txt"
_LOG_ENTRIES = [
    "2012-03-11 15:55:33 PM INFO TEST MESSAGE 1.\n",
    "2022-04-21 15:55:33 PM INFO TEST MESSAGE 2.\n",
]


class test(rpl_admin.test):
    """test replication administration commands
    This test exercises the mysqlrpladmin utility parameters.
    It uses the rpl_admin test for setup and teardown methods.
    """

    # Some of the parameters cannot be tested because they are threshold
    # values used in timing. These include --ping, --timeout, --max-position,
    # and --seconds-behind. We include a test case for regression that
    # specifies these options but does not test them.

    server5 = None

    def check_prerequisites(self):
        rpl_admin.test.check_prerequisites(self)
        return True

    def setup(self):
        self.server0 = self.servers.get_server(0)
        self.server5 = self.spawn_server("no_slaved")
        return rpl_admin.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        base_cmd = ("mysqlrpladmin.py --ping=5 --timeout=7 --rpl-user=rpl:rpl "
                    "--seconds-behind=30 --max-position=100 ")

        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')
        no_slaved_conn = self.build_connection_string(self.server5).strip(' ')

        master_str = "--master={0}".format(master_conn)

        test_num = 1
        comment = "Test case {0} - show help".format(test_num)
        cmd_str = base_cmd + " --help"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqlrpladmin "
                                           "version", 6)

        test_num += 1
        comment = "Test case {0} - test slave discovery".format(test_num)
        cmd_str = "{0} {1} ".format(base_cmd, master_str)
        cmd_opts = " --discover-slaves-login=root:root health"
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.server2.exec_query("GRANT REPLICATION SLAVE ON *.* TO "
                                "'rpl'@'localhost' IDENTIFIED BY 'rpl'")

        test_num += 1
        comment = "Test case {0} - switchover with verbosity".format(test_num)
        cmd_str = "{0} {1} ".format(base_cmd, master_str)
        cmd_opts = (" --discover-slaves-login=root:root --verbose switchover "
                    "--demote-master --no-health "
                    "--new-master={0}".format(slave1_conn))
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - switchover with quiet".format(test_num)
        cmd_str = "{0} --master={1} ".format(base_cmd, slave1_conn)
        cmd_opts = (" --discover-slaves-login=root:root --quiet switchover "
                    "--demote-master --new-master={0}  --log={1} "
                    "--log-age=1 ".format(master_conn, _LOGNAME))
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Now check the log and dump its entries
        with open(_LOGNAME, "r") as log_file:
            num_log_lines = len(log_file.readlines())
            if num_log_lines > 0:
                self.results.append("Switchover has written to the log.\n")
            else:
                self.results.append("ERROR! Nothing written to the log.\n")

        # Now overwrite the log file and populate with known 'old' entries
        with open(_LOGNAME, "w+") as log_file:
            log_file.writelines(_LOG_ENTRIES)
            self.results.append("There are (before) {0} entries in the "
                                "log.\n".format(len(_LOG_ENTRIES)))
            num_log_lines = len(_LOG_ENTRIES)

        test_num += 1
        comment = "Test case {0} - switchover with logs".format(test_num)
        cmd_str = "{0} {1} ".format(base_cmd, master_str)
        cmd_opts = (" --discover-slaves-login=root:root switchover "
                    "--demote-master --new-master={0} "
                    "--log={1} ".format(slave1_conn, _LOGNAME))
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Now check the log and dump its entries
        with open(_LOGNAME, "r") as log_file:
            if len(log_file.readlines()) > num_log_lines:
                self.results.append("There are additional entries in the "
                                    "log.\n")
            else:
                self.results.append("ERROR: Nothing else written to the "
                                    "log.\n")
        # log file removed by the cleanup method

        test_num += 1
        comment = ("Test case {0} - attempt switchover with stranger server "
                   "without using --force option".format(test_num))
        cmd_str = "{0} --master={1} ".format(base_cmd, slave2_conn)
        slaves = ",".join([master_conn, slave1_conn, slave3_conn])
        new_slaves = " --slaves={0}".format(slaves)
        cmd_opts = "{0} switchover --new-master={1} ".format(new_slaves,
                                                             no_slaved_conn)
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - attempt switchover with stranger server "
                   "using --force option".format(test_num))
        cmd_str = "{0} --master={1} --force".format(base_cmd, slave2_conn)
        slaves = ",".join([master_conn, slave1_conn, slave3_conn])
        new_slaves = " --slaves={0}".format(slaves)
        cmd_opts = "{0} switchover --new-master={1} ".format(new_slaves,
                                                             no_slaved_conn)
        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - attempt master switchover it "
                   "self".format(test_num))
        base_cmd = ("mysqlrpladmin.py --timeout=7 --rpl-user=rpl:rpl "
                    "--seconds-behind=30 --max-position=100 ")
        cmd_str = "{0} --master={1} --force ".format(base_cmd, no_slaved_conn)
        slaves = ",".join([master_conn, slave1_conn, slave3_conn])
        new_slaves = " --slaves={0}".format(slaves)
        cmd_opts = "{0} switchover --new-master={1}".format(new_slaves,
                                                            no_slaved_conn)
        res = self.run_test_case(2, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Now we return the topology to its original state for other tests
        rpl_admin.test.reset_topology(self)

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)

        self.replace_substring(self.server1.get_version(),
                               "XXXXXXXXXXXXXXXXXXXXXX")
        self.replace_result("# CHANGE MASTER TO MASTER_HOST",
                            "# CHANGE MASTER TO MASTER_HOST [...]\n")

        self.replace_substring(str(self.server5.port), "PORT5")

        # Add mask - WARNING not issued with 5.1. servers
        self.remove_result("# WARNING: You may be mixing host names and "
                           "IP addresses. ")
        self.remove_result("NOTE: Log file")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Remove log file (here to delete the file even if some test fails)
        try:
            os.unlink(_LOGNAME)
        except OSError:
            pass
        try:
            os.rmdir("watchout_here")
        except OSError:
            pass
        try:
            os.rmdir("watchout_here_too")
        except OSError:
            pass
        # Kill the servers that are only for this test.
        kill_list = ['no_slaved']
        return (rpl_admin.test.cleanup(self)
                and self.kill_server_list(kill_list))
