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
failover_errors test.
"""

import os
import socket
import time

import mutlib
import rpl_admin_gtid

from mysql.utilities.exception import MUTLibError


class test(rpl_admin_gtid.test):
    """test replication failover utility
    This test exercises the mysqlfailover utility known error conditions.
    Note: this test requires GTID enabled servers.
    """

    def check_prerequisites(self):
        return rpl_admin_gtid.test.check_prerequisites(self)

    def setup(self):
        return rpl_admin_gtid.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')
        slave4_conn = self.build_connection_string(self.server5).strip(' ')

        test_num = 1
        comment = "Test case {0} - No master".format(test_num)
        cmd_str = "mysqlfailover.py "
        cmd_opts = " --discover-slaves-login=root:root"
        res = mutlib.System_test.run_test_case(self, 2, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - No slaves or "
                   "discover-slaves-login".format(test_num))
        cmd_str = "mysqlfailover.py "
        cmd_opts = " --master=root:root@localhost"
        res = mutlib.System_test.run_test_case(self, 2, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - Low value for interval.".format(test_num)
        cmd_str = "mysqlfailover.py --interval=1"
        cmd_opts = " --master=root:root@localhost"
        res = mutlib.System_test.run_test_case(self, 2, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - elect mode but no "
                   "candidates".format(test_num))
        cmd_str = "mysqlfailover.py "
        cmd_opts = (" --master=root:root@localhost --failover-mode=elect "
                    "--slaves={0} ".format(slave1_conn))
        res = mutlib.System_test.run_test_case(self, 2, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Test for missing --rpl-user

        # Add server5 to the topology
        conn_str = " --slave={0}  --master={1} ".format(
            self.build_connection_string(self.server5), master_conn)

        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl {0}".format(conn_str)
        res = self.exec_util(cmd, self.res_fname)
        if res != 0:
            return False

        test_num += 1
        comment = ("Test case {0} - FILE/TABLE mix and missing "
                   "--rpl-user".format(test_num))
        cmd_str = "mysqlfailover.py "
        cmd_opts = " --master={0} --log=a.txt --slaves={1} ".format(
            master_conn, ",".join([slave1_conn, slave2_conn, slave3_conn,
                                   slave4_conn]))
        res = mutlib.System_test.run_test_case(self, 1, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Now test to see what happens when master is listed as a slave
        test_num += 1
        comment = ("Test case {0} - Master listed as a slave - "
                   "literal".format(test_num))
        cmd_str = "mysqlfailover.py health "
        cmd_opts = " --master={0}  --slaves={1} ".format(
            master_conn, ",".join([slave1_conn, slave2_conn, slave3_conn,
                                   master_conn]))
        res = mutlib.System_test.run_test_case(self, 2, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Master listed as a slave - "
                   "alias".format(test_num))
        cmd_str = "mysqlfailover.py health "
        cmd_opts = " --master={0}  --slaves=root:root@{1}:{2} ".format(
            master_conn, socket.gethostname().split('.', 1)[0],
            self.server1.port)
        res = mutlib.System_test.run_test_case(self, 2, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Master listed as a candidate - "
                   "alias".format(test_num))
        cmd_str = "mysqlfailover.py health "
        cmd_opts = (" --master={0} --slaves={1} --candidates=root:root@{2}:"
                    "{3} ".format(master_conn,
                                  ",".join([slave1_conn, slave2_conn]),
                                  socket.gethostname().split('.', 1)[0],
                                  self.server1.port))
        res = mutlib.System_test.run_test_case(self, 2, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Connection failure".format(test_num))
        cmd_str = "mysqlfailover.py health "
        cmd_opts = (" --master={0} --slaves={1} --candidates=root:root@{2}:"
                    "{3} ".format(master_conn,
                                  "nope@notthere:90125",
                                  "nothere",
                                  self.server2.port))
        res = mutlib.System_test.run_test_case(self, 1, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.reset_topology()

        self.replace_substring(str(self.m_port), "PORT1")
        self.replace_substring(str(self.s1_port), "PORT2")
        self.replace_substring(str(self.s2_port), "PORT3")
        self.replace_substring(str(self.s3_port), "PORT4")
        self.replace_substring(str(self.s4_port), "PORT5")

        self.remove_result("NOTE: Log file")

        self.replace_result("ERROR: Can't connect to MySQL server on",
                            "ERROR: Can't connect to MySQL server on XXXX\n")

        self.remove_result("{0}".format(time.localtime()[0]))

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
                os.unlink("a.txt")
            except OSError:
                pass

        # Kill the servers that are only used for this test
        kill_list = ['rep_master_gtid', 'rep_slave1_gtid', 'rep_slave2_gtid',
                     'rep_slave3_gtid', 'rep_slave4_gtid']
        return self.kill_server_list(kill_list)
