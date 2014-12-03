#
# Copyright (c) 2014, Oracle and/or its affiliates. All rights reserved.
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
binlog_rotate_privileges test.
"""

import mutlib
from binlog_rotate import binlog_file_exists

from mysql.utilities.common.user import change_user_privileges
from mysql.utilities.exception import MUTLibError


class test(mutlib.System_test):
    """Tests required privileges to run the the rotate binlog utility
    This test executes the rotate binlog utility on a single server using a
    user with a mix of required privileges to run the utility.
    This test verify the privileges required to execute the mysqlbinlogrotate
    utility. REPLICATION CLIENT and RELOAD privileges are required to run the
    utility.
    """

    server2 = None
    mask_ports = []
    server2_datadir = None

    def check_prerequisites(self):
        # Need at least one server.
        return self.check_num_servers(1)

    def setup(self):
        mysqld = ("--log-bin=mysql-bin --report-port={0}"
                  ).format(self.servers.view_next_port())
        self.server2 = self.servers.spawn_server("server2_binlog_rotate",
                                                 mysqld, True)

        # Get datadir
        rows = self.server2.exec_query("SHOW VARIABLES LIKE 'datadir'")
        if not rows:
            raise MUTLibError("Unable to determine datadir of cloned server "
                              "at {0}:{1}".format(self.server2.host,
                                                  self.server2.port))
        self.server2_datadir = rows[0][1]

        self.mask_ports.append(self.server2.port)

        return True

    def run(self):
        self.res_fname = "result.txt"
        cmd_str = "mysqlbinlogrotate.py "
        serv_conn = self.build_custom_connection_string(self.server2,
                                                          'a_user', 'a_pwd')

        test_num = 1
        test_cases = (
            {"comment": "with no privileges",
             "grant_list": None,
             "revoke_list": None,
             "exp_cmd_res": 1,
             "rotation_expected": False,},
            {"comment": "with RELOAD privilege only",
             "grant_list": ['RELOAD'],
             "revoke_list": None,
             "exp_cmd_res": 1,
             "rotation_expected": False,},
            {"comment": "with REPLICATION CLIENT privilege only",
             "grant_list": ['REPLICATION CLIENT'],
             "revoke_list": ['RELOAD'],
             "exp_cmd_res": 1,
             "rotation_expected": False,},
            {"comment": "with RELOAD and REPLICATION CLIENT privileges",
             "grant_list": ['RELOAD'],
             "revoke_list": None,
             "exp_cmd_res": 0,
             "rotation_expected": True,}
        )

        create_user = True
        for test_case in test_cases:
            # Create user if has not been created, also grant and revoke
            # privileges as required by the test case.
            if self.debug:
                print("\nChanging user privileges\n  granting: {0}\n  "
                      "revoking: {1}".format(test_case["grant_list"],
                                             test_case["revoke_list"]))
            change_user_privileges(self.server2, 'a_user', 'a_pwd',
                                   self.server2.host,
                                   grant_list=test_case["grant_list"],
                                   revoke_list=test_case["revoke_list"],
                                   disable_binlog=True,
                                   create_user=create_user)
            create_user = False

            rot_exp = test_case["rotation_expected"]
            comment = ("Test case {0} - rotate on server {1} "
                       "and -vv".format(test_num, test_case["comment"]))
            cmd = "{0} --server={1} -vv".format(cmd_str, serv_conn)
            res = self.run_test_case(test_case["exp_cmd_res"], cmd, comment)
            if not res or \
               (rot_exp ^ binlog_file_exists(self.server2_datadir,
                                            "mysql-bin.000002", self.debug)):
                raise MUTLibError("{0}: failed".format(comment))
            test_num += 1

        self.replace_substring("localhost", "XXXX-XXXX")
        p_n = 0
        for port in self.mask_ports:
            p_n += 1
            self.replace_substring(repr(port), "PORT{0}".format(p_n))

        self.replace_result(
            "# Active binlog file: ",
            "# Active binlog file: 'XXXXX-XXX:XXXXXX' (size: XXX bytes)\n"
        )

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Kill the servers that are only for this test.
        return self.kill_server_list(['server2_binlog_rotate'])
