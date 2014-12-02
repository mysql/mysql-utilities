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
rpl_admin_errors test.
"""

import os
import socket

import mutlib
import rpl_admin

from mysql.utilities.exception import MUTLibError

_LOGNAME = "temp_log.txt"


class test(rpl_admin.test):
    """test replication administration commands
    This test exercises the mysqlrpladmin utility known error conditions.
    It uses the rpl_admin test for setup and teardown methods.
    """

    server5 = None

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        if not rpl_admin.test.setup(self):
            return False

        # Spawn an independent server
        self.server5 = self.servers.spawn_server("alone_srv", kill=True,
                                                 mysqld="--sql_mode="
                                                 "NO_AUTO_CREATE_USER "
                                                 "--log-bin=mysqlbin")

        return True

    def run(self):
        self.res_fname = "result.txt"

        base_cmd = "mysqlrpladmin.py "
        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')

        master_str = "--master=" + master_conn

        # create a user for priv check
        self.server1.exec_query("CREATE USER 'joe'@'localhost'")
        self.server1.exec_query("GRANT SELECT, SUPER ON *.* TO "
                                "'jane'@'localhost'")
        mock_master1 = "--master=joe@localhost:{0}".format(
            self.server1.port)
        mock_master2 = "--master=jane@localhost:{0}".format(
            self.server1.port)
        slaves_str = "--slaves={0}".format(
            ",".join([slave1_conn, slave2_conn, slave3_conn]))

        # List of test cases for test
        test_cases = [
            # (comment, ret_val, option1, ...),
            ("Multiple commands issued.", 2, "switchover", "start"),
            ("No commands.", 2, ""),
            ("Invalid command.", 2, "NOTACOMMAND",
             "--discover-slaves-login=root"),
            ("Switchover but no --master, --new-master,", 2, "switchover",
             "--discover-slaves-login=root"),
            ("No slaves or discover-slaves-login", 2, "switchover",
             master_str),
            ("Bad --new-master connection string", 2, "switchover", master_str,
             slaves_str, "--new-master=whatmeworry?"),
            ("Bad --master connection string", 1, "switchover", slaves_str,
             "--new-master={0}".format(master_conn), "--master=whatmeworry?"),
            ("Bad --slaves connection string", 1, "switchover", master_str,
             "--new-master={0}".format(master_conn),
             "--slaves=what,me,worry?"),
            ("Bad --candidates connection string", 1, "failover",
             slaves_str, "--candidates=what,me,worry?"),
            ("Not enough privileges - health joe", 1, "health", mock_master1,
             slaves_str),
            ("Not enough privileges - health jane", 0, "health", mock_master2,
             slaves_str),
            ("Not enough privileges - switchover jane", 1, "switchover",
             mock_master2, slaves_str, "--new-master={0}".format(slave3_conn)),
            ("Failover command requires --slaves", 2, "failover"),
            ("Failover command cannot be used with --discover-slaves-login", 2,
             "--discover-slaves-login=root", "failover",)
        ]

        test_num = 1
        for case in test_cases:
            comment = "Test case {0} - {1}".format(test_num, case[0])
            parts = [base_cmd]
            for opt in case[2:]:
                parts.append(opt)
            cmd_str = " ".join(parts)
            res = mutlib.System_test.run_test_case(self, case[1], cmd_str,
                                                   comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))
            test_num += 1

        # Now test to see what happens when master is listed as a slave
        comment = ("Test case {0} - Master listed as a slave - "
                   "literal".format(test_num))
        cmd_str = "{0} health {1} {2},{3}".format(base_cmd, master_str,
                                                  slaves_str, master_conn)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        comment = "Test case {0} - Master listed as a slave - alias".format(
            test_num)
        cmd_str = ("{0} health {1} --slaves=root:root@{2}:{3}".format(
            base_cmd, master_str, socket.gethostname().split('.', 1)[0],
            self.server1.port))
        res = mutlib.System_test.run_test_case(self, 2, cmd_str,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        comment = ("Test case {0} - Master listed as a candidate - "
                   "alias".format(test_num))
        cmd_str = "{0} elect {1} --candidates=root:root@{2}:{3} {4}".format(
            base_cmd, master_str, socket.gethostname().split('.', 1)[0],
            self.server1.port, slaves_str)
        res = mutlib.System_test.run_test_case(self, 2, cmd_str,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        for command in ('start', 'stop', 'reset'):
            comment = ("Test case {0} - {1} without "
                       "--slaves".format(test_num, command.capitalize()))
            cmd_str = ("{0} {1} --discover-slaves-login="
                       "root:root".format(base_cmd, command))
            res = mutlib.System_test.run_test_case(self, 2, cmd_str, comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))
            test_num += 1

        # Test error using --discover and --slaves at the same time
        for command in ('start', 'stop', 'reset', 'health', 'failover',
                        'switchover'):
            comment = ("Test case {0} - {1} using --discover-slaves-login and "
                       "--slaves".format(test_num, command.capitalize()))
            cmd_str = ("{0} {1} {2} --discover-slaves-login="
                       "root:root".format(base_cmd, command, slaves_str))
            res = mutlib.System_test.run_test_case(self, 2, cmd_str, comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))
            test_num += 1

        # Test error switchover --new-master and --master are the same value.
        command = 'switchover'
        comment = ("Test case {0} - {1} using switchover new master is "
                   "the actual master with --discover-slaves"
                   "".format(test_num, command.capitalize()))
        cmd_str = ("{0} {1} {2} {3} --new-master={4} "
                   "--discover-slaves-login=root:root"
                   "".format(base_cmd, command, master_str,
                             "--rpl-user=rpl:rpl", master_conn))
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Test error switchover --new-master and --master are the same value,
        # replacing new-master host with alias.
        command = 'switchover'
        comment = ("Test case {0} - {1} using switchover new master is the "
                   "actual master, replacing new-master host with alias."
                   "".format(test_num, command.capitalize()))
        cmd_str = ("{0} {1} {2} {3},{4} --new-master={4}"
                   "".format(base_cmd, command, master_str, slaves_str,
                             master_conn.replace("localhost", "127.0.0.1")))
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Test switchover with a wrong slave (not in the topology)
        # Note: --rpl-user is required if master-info-repository is not TABLE
        alone_srv_conn = self.build_connection_string(self.server5).strip(' ')

        comment = ("Test case {0} - Switchover using a wrong slave (without "
                   "--force)".format(test_num))
        slaves_str = ",".join([slave2_conn, slave3_conn, alone_srv_conn])
        cmd_str = ("{0} --master={1} --new-master={2} --slaves={3} "
                   "switchover --rpl-user=rpl:rpl".format(base_cmd,
                                                          master_conn,
                                                          slave1_conn,
                                                          slaves_str))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Switchover using a wrong slave and with "
                   "--force".format(test_num))
        slaves_str = ",".join([slave2_conn, slave3_conn, alone_srv_conn])
        cmd_str = ("{0} --master={1} --new-master={2} --slaves={3} --force "
                   "switchover --rpl-user=rpl:rpl".format(base_cmd,
                                                          master_conn,
                                                          slave1_conn,
                                                          slaves_str))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Switchover using with --force and user "
                   "does not have grant priv".format(test_num))
        slaves_str = ",".join([slave2_conn, slave3_conn])
        cmd_str = ("{0} --master={1} --new-master={2} --force switchover -q "
                   "--rpl-user=rpl:rpl --slaves={3} --log={4} --log-age=1 "
                   "--rpl-user=notthere "
                   "--no-health".format(base_cmd, slave1_conn, alone_srv_conn,
                                        slaves_str, _LOGNAME))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Connect failure".format(test_num))
        slaves_str = ",".join([slave2_conn, slave3_conn])
        cmd_str = ("{0} --master={1} --new-master=nope@notthere "
                   " --force switchover -q "
                   "--rpl-user=rpl:rpl --slaves={2} --log={3} --log-age=1 "
                   "--rpl-user=notthere "
                   "--no-health".format(base_cmd, alone_srv_conn,
                                        slaves_str, _LOGNAME))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Check log file for error.
        # Now check the log and dump its entries for debugging
        log_file = open(_LOGNAME, "r")
        rows = log_file.readlines()
        log_file.close()
        for row in rows:
            if self.debug:
                print("> {0}".format(row))
            if "Cannot grant replication slave" in row:
                self.results.append("Error found in log file. \n")
                break
        else:
            self.results.append("Error NOT found in the log.\n")
        # log file removed by the cleanup method

        # Test path to script file not being valid
        option_scripts = ['--exec-after', '--exec-before']

        non_valid_path = os.path.normpath("./std_data/does_not_exist.bat")
        for opt in option_scripts:
            test_num += 1
            comment = ("Test case {0} - script passed to the '{1}' option "
                       "does not exist".format(test_num, opt))
            cmd_str = "mysqlrpladmin.py failover "
            cmd_opts = (" --master={0} --slaves={1} {2}={3}".format(
                master_conn, slave1_conn, opt, non_valid_path))
            res = mutlib.System_test.run_test_case(self, 2, cmd_str + cmd_opts,
                                                   comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))

        test_num += 1

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)

        self.replace_result("ERROR: Can't connect to",
                            "ERROR: Can't connect to XXXXXXX\n")

        self.replace_substring(str(self.server5.port), "PORT5")
        self.replace_substring('std_data\\does_not_exist.bat',
                               'std_data/does_not_exist.bat')

        self.replace_substring(socket.gethostname().split('.', 1)[0],
                               "<hostname>")

        self.replace_result("mysqlrpladmin: error: New master connection "
                            "values invalid",
                            "mysqlrpladmin: error: New master connection "
                            "values invalid\n")
        self.replace_result("ERROR: Master connection values invalid or "
                            "cannot be parsed",
                            "ERROR: Master connection values invalid or "
                            "cannot be parsed\n")
        self.replace_result("ERROR: Slave connection values invalid or "
                            "cannot be parsed",
                            "ERROR: Slave connection values invalid or "
                            "cannot be parsed\n")
        self.replace_result("ERROR: Candidate connection values invalid or "
                            "cannot be parsed",
                            "ERROR: Candidate connection values invalid or "
                            "cannot be parsed\n")

        self.replace_result("| localhost  | PORT1  | MASTER  | UP     "
                            "| NO         | OK      |",
                            "| localhost  | PORT1  | MASTER  | UP     "
                            "| OFF        | OK      |\n")
        self.replace_result("| localhost  | PORT2  | SLAVE   | UP     "
                            "| NO         | OK      |",
                            "| localhost  | PORT2  | SLAVE   | UP     "
                            "| OFF        | OK      |\n")
        self.replace_result("| localhost  | PORT3  | SLAVE   | UP     "
                            "| NO         | OK      |",
                            "| localhost  | PORT3  | SLAVE   | UP     "
                            "| OFF        | OK      |\n")
        self.replace_result("| localhost  | PORT4  | SLAVE   | UP     "
                            "| NO         | OK      |",
                            "| localhost  | PORT4  | SLAVE   | UP     "
                            "| OFF        | OK      |\n")
        self.replace_result("| localhost  | PORT2  | MASTER  | UP     "
                            "| NO         | OK      |",
                            "| localhost  | PORT2  | MASTER  | UP     "
                            "| OFF        | OK      |\n")
        self.replace_result("| localhost  | PORT5  | SLAVE   | UP     "
                            "| NO         | OK      |",
                            "| localhost  | PORT5  | SLAVE   | UP     "
                            "| OFF        | OK      |\n")

        self.remove_result("NOTE: Log file")

        # Remove warning when using test servers without GTID enabled.
        self.remove_result("# WARNING: Errant transactions check skipped")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):

        # Kill independent server
        self.kill_server("alone_srv")

        # Kill all remaining servers (to avoid problems for other tests).
        self.kill_server("rep_master")
        self.kill_server("rep_slave1")
        self.kill_server("rep_slave2")
        self.kill_server("rep_slave3")

        # Remove log file (here to delete the file even if some test fails)
        try:
            os.unlink(_LOGNAME)
        except OSError:
            pass

        return rpl_admin.test.cleanup(self)
