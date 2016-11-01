#
# Copyright (c) 22016, Oracle and/or its affiliates. All rights reserved.
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
rpl_admin test.
"""

import os
import time

import mutlib
import rpl_admin

from mysql.utilities.exception import MUTLibError, UtilError


_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --report-host=localhost '
                       '--report-port={0} "')


class test(rpl_admin.test):
    """test replication administration commands
    This test runs the mysqlrpladmin utility on a known topology.

    Note: this test will run against servers without GTID enabled.
    See rpl_admin_gtid test for test cases for GTID enabled servers.
    """

    server0 = None
    server1 = None
    server2 = None
    server3 = None
    server4 = None
    s1_port = None
    s2_port = None
    s3_port = None
    m_port = None
    master_str = None

    def check_prerequisites(self):
        if os.name == "nt":
            raise MUTLibError("Test requires Posix platform.")
        return rpl_admin.test.check_prerequisites(self)

    def setup(self):
        return rpl_admin.test.setup(self)

    def run(self):
        rpl_admin.test.mask_global = False  # Turn off global masks
        cmd_str = "mysqlrpladmin.py {0} ".format(self.master_str)

        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')

        slaves_str = ",".join([slave1_conn, slave2_conn, slave3_conn])

        test_num = 1
        rpl_admin.test.reset_topology(self)
        master_socket = self.server1.show_server_variable('socket')
        self.server1.exec_query("SET sql_log_bin = 0")
        try:
            self.server1.exec_query("DROP USER 'root_me'@'localhost'")
        except:
            pass   # Ok if user doesn't exist
        self.server1.exec_query("CREATE USER 'root_me'@'localhost'")
        self.server1.exec_query("GRANT ALL ON *.* TO 'root_me'@'localhost' "
                                "WITH GRANT OPTION")
        self.server1.exec_query("SET sql_log_bin = 1")
        self.create_login_path_data('test_master_socket', 'root_me',
                                    'localhost', None,
                                    "'{0}'".format(master_socket[0][1]))

        cmd_str = ("mysqlrpladmin.py --master=test_master_socket health "
                   "--disc=root:root")
        comment = ("Test case {0} - health with discovery and socket"
                   "".format(test_num))
        res = rpl_admin.test.run_test_case(self, 0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1

        slave_socket = self.server2.show_server_variable('socket')
        self.server2.exec_query("SET sql_log_bin = 0")
        try:
            self.server2.exec_query("DROP USER 'root_me'@'localhost'")
        except:
            pass   # Ok if user doesn't exist
        self.server2.exec_query("CREATE USER 'root_me'@'localhost'")
        self.server2.exec_query("GRANT ALL ON *.* TO 'root_me'@'localhost'")
        self.server2.exec_query("SET sql_log_bin = 1")
        self.create_login_path_data('test_slave_socket', 'root_me',
                                    'localhost', None,
                                    "'{0}'".format(slave_socket[0][1]))

        cmd_str = ("mysqlrpladmin.py --master=test_master_socket health "
                   "--slaves=test_slave_socket")
        comment = ("Test case {0} - health with sockets"
                   "".format(test_num))
        res = rpl_admin.test.run_test_case(self, 0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Now we return the topology to its original state for other tests
        rpl_admin.test.reset_topology(self)

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)

        # Remove warning when using test servers without GTID enabled.
        self.remove_result("# WARNING: Errant transactions check skipped")

        # Cleanup for login paths
        self.remove_login_path_data('test_master_socket')
        self.remove_login_path_data('test_slave_socket')

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return rpl_admin.test.cleanup(self)
