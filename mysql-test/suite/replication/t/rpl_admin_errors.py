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
import mutlib
import rpl_admin
import socket
from mysql.utilities.exception import MUTLibError

class test(rpl_admin.test):
    """test replication administration commands
    This test exercises the mysqlrpladmin utility known error conditions.
    It uses the rpl_admin test for setup and teardown methods.
    """

    def check_prerequisites(self):
        return rpl_admin.test.check_prerequisites(self)

    def setup(self):
        return rpl_admin.test.setup(self)

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
        self.server1.exec_query("GRANT SELECT, SUPER ON *.* TO 'jane'@'localhost'")
        mock_master1 = "--master=joe@localhost:%s" % self.server1.port
        mock_master2 = "--master=jane@localhost:%s" % self.server1.port
        slaves_str = "--slaves=" + \
                     ",".join([slave1_conn, slave2_conn, slave3_conn])
        candidates_str = "--candidates=" + \
                         ",".join([slave1_conn, slave2_conn, slave3_conn])

        # List of test cases for test
        test_cases = [
            # (comment, ret_val, option1, ...),
            ("Multiple commands issued.", 2, "switchover", "start"),
            ("No commands.", 2, ""),
            ("Invalid command.", 2, "NOTACOMMAND"),
            ("Switchover but no --master, --new-master,", 2, "switchover"),
            ("No slaves or discover-slaves-login", 2, "switchover", master_str),
            ("Force used with failover", 2, "failover", "--force", master_str,
             slaves_str),
            ("Bad --new-master connection string", 2, "switchover", master_str,
             slaves_str, "--new-master=whatmeworry?"),
            ("Bad --master connection string", 1, "switchover", slaves_str,
             "--new-master=%s" % master_conn, "--master=whatmeworry?"),
            ("Bad --slaves connection string", 1, "switchover", master_str,
             "--new-master=%s" % master_conn, "--slaves=what,me,worry?"),
            ("Bad --candidates connection string", 1, "failover", master_str,
             slaves_str, "--candidates=what,me,worry?"),
            ("Not enough privileges - health joe", 1, "health", mock_master1,
             slaves_str),
            ("Not enough privileges - health jane", 0, "health", mock_master2,
             slaves_str),
            ("Not enough privileges - switchover jane", 1, "switchover",
             mock_master2, slaves_str, "--new-master=%s" % slave3_conn),
        ]

        test_num = 1
        for case in test_cases:
            comment = "Test case %s - %s" % (test_num, case[0])
            parts = [base_cmd]
            for opt in case[2:]:
                parts.append(opt)
            cmd_str = " ".join(parts)
            res = mutlib.System_test.run_test_case(self, case[1], cmd_str,
                                                   comment)
            if not res:
                raise MUTLibError("%s: failed" % comment)
            test_num += 1

        # Now test to see what happens when master is listed as a slave
        comment = "Test case %s - Master listed as a slave - literal" % test_num
        cmd_str = "%s health %s %s,%s" % (base_cmd, master_str, slaves_str, master_conn)
        res = mutlib.System_test.run_test_case(self, 2, cmd_str,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        comment = "Test case %s - Master listed as a slave - alias"  % test_num
        cmd_str = "%s health %s %s" % (base_cmd, master_str,
                  "--slaves=root:root@%s:%s" % \
                    (socket.gethostname().split('.', 1)[0], self.server1.port))
        res = mutlib.System_test.run_test_case(self, 2, cmd_str,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        comment = "Test case %s - Master listed as a candiate - alias" % test_num
        cmd_str = "%s elect %s %s %s" % (base_cmd, master_str,
                  "--candidates=root:root@%s:%s" % \
                    (socket.gethostname().split('.', 1)[0], self.server1.port),
                  slaves_str)
        res = mutlib.System_test.run_test_case(self, 2, cmd_str,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        # Now we return the topology to its original state for other tests
        rpl_admin.test.reset_topology(self)

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)

        self.replace_result("mysqlrpladmin.py: error: New master connection "
                            "values invalid",
                            "mysqlrpladmin.py: error: New master connection "
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

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        try:
            self.server1.exec_query("DROP USER 'joe'@'localhost'")
        except:
            pass
        try:
            self.server1.exec_query("DROP USER 'jane'@'localhost'")
        except:
            pass
        return rpl_admin.test.cleanup(self)



