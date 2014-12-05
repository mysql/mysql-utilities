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
rpl_admin_basic_ssl_opt_gtid test.
"""

import rpl_admin_basic_ssl_gtid

from mutlib.ssl_certs import ssl_c_ca

from mysql.utilities.exception import MUTLibError


class test(rpl_admin_basic_ssl_gtid.test):
    """test replication administration commands
    This test runs the mysqlrpladmin utility on a known topology with ssl=1
    and ca certificate.

    Note: this test requires GTID enabled servers.
    """

    def run(self):
        test_num = 1

        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')
        ssl1 = "--ssl=1"
        ssl_ca = "--ssl-ca={0}".format(ssl_c_ca)

        comment = ("Test case {0} - SSL mysqlrplshow OLD Master "
                   "before demote".format(test_num))
        cmd_str = "mysqlrplshow.py --master={0} {1} {2}".format(master_conn,
                                                                ssl1, ssl_ca)
        cmd_opts = "--discover-slaves={0} ".format(master_conn.split('@')[0])
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - SSL "
                   "switchover demote-master ".format(test_num))
        cmd_str = ("mysqlrpladmin.py --master={0} {1} {2} "
                   ).format(master_conn, ssl1, ssl_ca)
        cmd_opts = (" --new-master={0} --discover-slaves={1} "
                    "--rpl-user=rpluser:hispassword --demote-master "
                    "switchover".format(slave1_conn,
                                        master_conn.split('@')[0]))
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplshow "
                   "NEW Master after demote".format(test_num))
        cmd_str = "mysqlrplshow.py --master={0} {1} {2}".format(slave1_conn,
                                                                ssl1, ssl_ca)
        cmd_opts = " --discover-slaves={0} ".format(master_conn.split('@')[0])
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplcheck "
                   "NEW Master after demote".format(test_num))
        cmd_opts = "--slave={0} --show-slave-status".format(master_conn)
        cmd_str = "mysqlrplcheck.py --master={0} {1} {2}".format(slave1_conn,
                                                                 ssl1, ssl_ca)
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplcheck "
                   "NEW Master after demote".format(test_num))
        cmd_opts = "--slave={0} --show-slave-status".format(slave2_conn)
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplcheck "
                   "NEW Master after demote".format(test_num))
        cmd_opts = "--slave={0} --show-slave-status".format(slave3_conn)
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - SSL "
                   "failover ".format(test_num))
        cmd_str = "mysqlrpladmin.py {0} {1} ".format(ssl1, ssl_ca)
        slaves = ",".join([slave2_conn, slave3_conn,
                           master_conn])
        cmd_opts = (" --slaves={0} --rpl-user=rpluser:hispassword "
                    "failover".format(slaves))
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplshow "
                   "NEW Master after failover".format(test_num))
        cmd_str = "mysqlrplshow.py --master={0} {1} {2}".format(slave2_conn,
                                                                ssl1, ssl_ca)
        cmd_opts = " --discover-slaves={0} ".format(master_conn.split('@')[0])
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplcheck "
                   "NEW Master after demote".format(test_num))
        cmd_str = "mysqlrplcheck.py --master={0} {1} {2}".format(slave2_conn,
                                                                 ssl1, ssl_ca)
        cmd_opts = "--slave={0} --show-slave-status".format(master_conn)
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - SSL mysqlrplcheck "
                   "NEW Master after demote".format(test_num))
        cmd_opts = "--slave={0} --show-slave-status".format(slave3_conn)
        cmds = "{0} {1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(0, cmds, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        self.mask_results()
        return True
