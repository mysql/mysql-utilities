#
# Copyright (c) 2013, 2014, Oracle and/or its affiliates. All rights reserved.
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
import rpl_admin
import rpl_admin_gtid
from mysql.utilities.exception import MUTLibError

_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --skip-slave-start '
                       '--log-slave-updates --gtid-mode=on '
                       '--enforce-gtid-consistency --report-host=127.0.0.1 '
                       '--report-port={0} '
                       '--sync-master-info=1 --master-info-repository=table"')

_DEFAULT_MYSQL_OPTS_FILE = ('"--log-bin=mysql-bin --skip-slave-start '
                            '--log-slave-updates --gtid-mode=on '
                            '--enforce-gtid-consistency '
                            '--report-host=127.0.0.1 --report-port={0} --sync'
                            '-master-info=1 --master-info-repository=file"')


class test(rpl_admin_gtid.test):
    """test replication administration commands
    This test runs the mysqlrpladmin utility on a known topology.

    Note: this test requires GTID enabled servers.
    """

    def check_prerequisites(self):
        # Need non-Windows platform
        if os.name == "nt":
            raise MUTLibError("Test requires a non-Windows platform.")
        if not self.servers.get_server(0).check_version_compat(5, 6, 9):
            raise MUTLibError("Test requires server version 5.6.9")
        return self.check_num_servers(1)

    def setup(self):
        return rpl_admin_gtid.test.setup(self)

    def run(self):

        test_num = 1

        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')

        # Remove GTIDs here because they are not deterministic when run with
        # other tests that reuse these servers.
        self.remove_result("127.0.0.1,{0},MASTER,".format(self.m_port))
        self.remove_result("127.0.0.1,{0},SLAVE,".format(self.s1_port))
        self.remove_result("127.0.0.1,{0},SLAVE,".format(self.s2_port))
        self.remove_result("127.0.0.1,{0},SLAVE,".format(self.s3_port))

        slaves = ",".join(["root:root@127.0.0.1:{0}".format(self.server2.port),
                           slave2_conn, slave3_conn])
        script = os.path.join(os.getcwd(), "std_data/show_arguments.sh")

        master_str = "--master={0}".format(master_conn)
        new_master_str = "--new-master={0} ".format(slave3_conn)
        exec_before_str = "--exec-before={0}".format(script)
        exec_after_str = "--exec-after={0}".format(script)
        slaves_str = "--slaves={0}".format(slaves)
        candidates_str = "--candidates={0}".format(slave3_conn)

        comment = "Test case {0} - test failover scripts".format(test_num)
        command = " ".join(["mysqlrpladmin.py ", candidates_str, slaves_str,
                            "failover", exec_before_str, exec_after_str,
                            "-vvv"])
        res = self.run_test_case(0, command, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Now we return the topology to its original state for other tests
        rpl_admin_gtid.test.reset_topology(self)

        comment = "Test case {0} - test switchover scripts".format(test_num)
        command = " ".join(["mysqlrpladmin.py", master_str, new_master_str,
                            "switchover", exec_before_str, exec_after_str,
                            "--demote-master", "-vvv", slaves_str])
        res = self.run_test_case(0, command, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Run test cases for testing:
        # a) before/after script fail for switchover, failover
        # b) border cases for threshold parameter

        script_exit = os.path.join(os.getcwd(), "std_data/check_threshold.sh")
        script_test_cases = [("<", 11, 0), ("=", 10, 1), (">", 9, 1)]
        script_options = [(script_exit, script), (script, script_exit)]

        com_fmt = "Test case {0} - test script exit {1} threshold {2}"
        switch_fmt = " ".join(["mysqlrpladmin.py", master_str, "switchover",
                               "--exec-before={0} ", new_master_str,
                               slaves_str, "--demote-master",
                               "--exec-after={1} ", "-vvv",
                               "--script-threshold={2}"])
        fail_fmt = " ".join(["mysqlrpladmin.py ", candidates_str, slaves_str,
                             "--exec-before={0} ", "--exec-after={1} ",
                             "-vvv", "--script-threshold={2}", "failover"])
        commands = [("switchover", switch_fmt), ("failover", fail_fmt)]
        for command in commands:
            for opt in script_options:
                for test_case in script_test_cases:
                    # Now we return the topology to its original state
                    # for other tests
                    rpl_admin_gtid.test.reset_topology(self)
                    comment = com_fmt.format(test_num, test_case[0],
                                             command[0])
                    cmd_str = command[1].format(opt[0], opt[1], test_case[1])
                    res = self.run_test_case(test_case[2], cmd_str, comment)
                    if not res:
                        raise MUTLibError("{0}: failed".format(comment))
                    test_num += 1

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)
        self.replace_substring(str(self.s4_port), "PORT5")

        # don't need health report
        self.remove_result("+")
        self.remove_result("|")

        # fix non-deterministic statements
        self.replace_result("# SCRIPT EXECUTED:",
                            "# SCRIPT EXECUTED: XXXXXXX\n")
        self.replace_result("# QUERY = SELECT WAIT_UNTIL_SQL_THREAD_AFTER_",
                            "# QUERY = SELECT WAIT_UNTIL_SQL_THREAD[...]\n")
        self.replace_result("# Return Code =", "# Return Code = XXX\n")
        self.replace_result("ERROR: External script",
                            "ERROR: External script XXXXXXX\n")
        self.replace_result("ERROR: {0}".format(script),
                            "ERROR: XXX Script failed.\n")
        self.replace_result("ERROR: {0}".format(script_exit),
                            "ERROR: XXX Script failed.\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return rpl_admin_gtid.test.cleanup(self)
