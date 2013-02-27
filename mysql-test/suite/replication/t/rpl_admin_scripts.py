#
# Copyright (c) 2013, Oracle and/or its affiliates. All rights reserved.
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
import rpl_admin_gtid
from mysql.utilities.exception import MUTLibError

_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --skip-slave-start '
                       '--log-slave-updates --gtid-mode=on '
                       '--enforce-gtid-consistency --report-host=localhost '
                       '--report-port=%s '
                       '--sync-master-info=1 --master-info-repository=table"')

_DEFAULT_MYSQL_OPTS_FILE = ('"--log-bin=mysql-bin --skip-slave-start '
                            '--log-slave-updates --gtid-mode=on '
                            '--enforce-gtid-consistency '
                            '--report-host=localhost --report-port=%s --sync'
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
        self.remove_result("localhost,%s,MASTER," % self.m_port)
        self.remove_result("localhost,%s,SLAVE," % self.s1_port)
        self.remove_result("localhost,%s,SLAVE," % self.s2_port)
        self.remove_result("localhost,%s,SLAVE," % self.s3_port)

        comment = "Test case %s - test failover scripts" % test_num
        slaves = ",".join(["root:root@127.0.0.1:%s" % self.server2.port,
                           slave2_conn, slave3_conn])
        script = os.path.join(os.getcwd(), "std_data/show_arguments.sh")
        command = " ".join(["mysqlrpladmin.py --master=%s " % master_conn,
                            "--candidates=%s  " % slave3_conn,
                            "--slaves=%s failover" % slaves,
                            "--exec-before=%s" % script,
                            "--exec-after=%s" % script, "-vvv"])
        res = mutlib.System_test.run_test_case(self, 0, command, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        # Now we return the topology to its original state for other tests
        rpl_admin_gtid.test.reset_topology(self)

        comment = "Test case %s - test switchover scripts" % test_num
        command = " ".join(["mysqlrpladmin.py --master=%s " % master_conn,
                            "--new-master=%s  " % slave3_conn, "switchover",
                            "--exec-before=%s" % script, "--demote-master",
                            "--exec-after=%s" % script, "-vvv",
                            "--slaves=%s" % slaves])
        res = mutlib.System_test.run_test_case(self, 0, command, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
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

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return rpl_admin_gtid.test.cleanup(self)
