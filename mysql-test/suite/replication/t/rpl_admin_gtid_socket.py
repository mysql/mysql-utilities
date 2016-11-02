#
# Copyright (c) 2016, Oracle and/or its affiliates. All rights reserved.
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
rpl_admin_gtid_socket test.
"""

import os
import rpl_admin_gtid

from mysql.utilities.exception import MUTLibError


_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --skip-slave-start '
                       '--log-slave-updates --gtid-mode=on '
                       '--enforce-gtid-consistency --report-host=localhost '
                       '--report-port={port} '
                       '--sync-master-info=1 --master-info-repository=table"')

_DEFAULT_MYSQL_OPTS_FILE = ('"--log-bin=mysql-bin --skip-slave-start '
                            '--log-slave-updates --gtid-mode=on '
                            '--enforce-gtid-consistency '
                            '--report-host=localhost --report-port={port} '
                            '--sync-master-info=1 '
                            '--master-info-repository=file"')

_MYSQL_OPTS_INFO_REPO_TABLE = ('"--log-bin=mysql-bin --skip-slave-start '
                               '--log-slave-updates --gtid-mode=ON '
                               '--enforce-gtid-consistency '
                               '--report-host=localhost --report-port={port} '
                               '--sync-master-info=1 '
                               '--master-info-repository=TABLE '
                               '--relay-log-info-repository=TABLE"')

TIMEOUT = 30


class test(rpl_admin_gtid.test):
    """test replication administration commands
    This test runs the mysqlrpladmin utility on a known topology.

    Note: this test requires GTID enabled servers.
    """

    server5 = None
    s4_port = None

    def check_prerequisites(self):
        if os.name == "nt":
            raise MUTLibError("Test requires non-Windows platform.")
        return rpl_admin_gtid.test.check_prerequisites(self)

    def setup(self):
        return rpl_admin_gtid.test.setup(self)

    def run(self):
        test_num = 1
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
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

        slave_socket = self.server2.show_server_variable('socket')
        self.server2.exec_query("SET sql_log_bin = 0")
        try:
            self.server2.exec_query("DROP USER 'root_me'@'localhost'")
        except:
            pass   # Ok if user doesn't exist
        self.server2.exec_query("CREATE USER 'root_me'@'localhost'")
        self.server2.exec_query("GRANT ALL ON *.* TO 'root_me'@'localhost'"
                                "WITH GRANT OPTION")
        self.server2.exec_query("SET sql_log_bin = 1")
        self.create_login_path_data('test_slave_socket', 'root_me',
                                    'localhost', None,
                                    "'{0}'".format(slave_socket[0][1]))

        cmd_str = ("mysqlrpladmin.py --master=test_master_socket elect "
                   "--disc=root:root --candidates=test_slave_socket")
        comment = ("Test case {0} - elect with discovery and socket"
                   "".format(test_num))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Now we return the topology to its original state for other tests
        rpl_admin_gtid.test.reset_topology(self)

        test_num += 1
        cmd_str = ("mysqlrpladmin.py failover --slaves={0} "
                   "--candidates=test_slave_socket --rpl-user=rpl:rpl "
                   "--force ".format(slave1_conn))
        comment = ("Test case {0} - failover with discovery and socket"
                   "".format(test_num))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Now we return the topology to its original state for other tests
        rpl_admin_gtid.test.reset_topology(self)

        # Mask out non-deterministic data
        rpl_admin_gtid.test.do_replacements(self)

        # Cleanup for login paths
        self.remove_login_path_data('test_master_socket')
        self.remove_login_path_data('test_slave_socket')

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return rpl_admin_gtid.test.cleanup(self)
