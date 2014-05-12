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

"""
rpl_admin_failover_missing test.
"""

import tempfile

import mutlib
import rpl_admin

from mysql.utilities.exception import MUTLibError, UtilRplError, UtilError
from mysql.utilities.common.format import format_tabular_list


_DEFAULT_MYSQL_OPTS = ' '.join(['"--log-bin=mysql-bin --skip-slave-start',
                                '--log-slave-updates --gtid-mode=on',
                                '--enforce-gtid-consistency',
                                '--report-host=localhost',
                                '--report-port={0} --sync-master-info=1',
                                '--master-info-repository=table"'])

_GTID_WAIT = "SELECT WAIT_UNTIL_SQL_THREAD_AFTER_GTIDS('{0}', {1})"

_GRANT_QUERY = "GRANT REPLICATION SLAVE ON *.* TO 'rpl'@'rpl'"
_SET_SQL_LOG_BIN = "SET SQL_LOG_BIN = {0}"


class test(rpl_admin.test):
    """test replication administration commands
    This test runs the mysqlrpladmin utility on a known topology.

    Note: this test requires GTID enabled servers.
    """

    master_conn = None
    slave1_conn = None
    slave2_conn = None
    slave3_conn = None
    slave4_conn = None
    s4_port = None
    server5 = None
    servers_list = None

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 9):
            raise MUTLibError("Test requires server version 5.6.9")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers
        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server1 = self.servers.spawn_server("rep_master_gtid", mysqld,
                                                 True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server2 = self.servers.spawn_server("rep_slave1_gtid", mysqld,
                                                 True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server3 = self.servers.spawn_server("rep_slave2_gtid", mysqld,
                                                 True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server4 = self.servers.spawn_server("rep_slave3_gtid", mysqld,
                                                 True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server5 = self.servers.spawn_server("rep_slave4_gtid", mysqld,
                                                 True)

        # Reset spawned servers (clear binary log and GTID_EXECUTED set)
        self.reset_master([self.server1, self.server2, self.server3,
                           self.server4, self.server5])

        self.m_port = self.server1.port
        self.s1_port = self.server2.port
        self.s2_port = self.server3.port
        self.s3_port = self.server4.port
        self.s4_port = self.server5.port

        rpl_admin.test.reset_topology(self)

        build_str = self.build_connection_string
        self.master_conn = build_str(self.server1).strip(' ')
        self.slave1_conn = build_str(self.server2).strip(' ')
        self.slave2_conn = build_str(self.server3).strip(' ')
        self.slave3_conn = build_str(self.server4).strip(' ')
        self.slave4_conn = build_str(self.server5).strip(' ')

        try:
            self.server5.exec_query("STOP SLAVE")
            self.server5.exec_query("RESET SLAVE")
        except UtilError:
            raise MUTLibError("Unable to reset slave")

        cmd = " ".join(["mysqlreplicate.py --rpl-user=rpl:rpl ",
                        " --slave={0}".format(self.slave4_conn),
                        " --master={0}".format(self.master_conn)])
        self.exec_util(cmd, self.res_fname)

        self.servers_list = [self.server1, self.server2, self.server3,
                             self.server4, self.server5]

        return True

    @staticmethod
    def wait_for_slave(master, slave):
        """Waits for slave.

        master[in]     Master instance.
        slave[in]      Slave instance.
        """
        master_gtid = master.exec_query("SELECT @@GLOBAL.GTID_EXECUTED")
        master_gtids = master_gtid[0][0].split('\n')
        for gtid in master_gtids:
            try:
                slave.exec_query(_GTID_WAIT.format(gtid.strip(','), 300))
            except UtilRplError as err:
                raise MUTLibError("Error executing {0}: {1}".format(
                    _GTID_WAIT.format(gtid.strip(','), 300), err.errmsg))
        return

    def dump_table(self, server):
        """Dumps the test_relay table.

        server[in]     Server instance.
        """
        header = "# Dump of table test_relay.t1 for server {0}:\n".format(
            server.role)
        self.results.append(header)
        if self.debug:
            print header
        rows = server.exec_query("SELECT * FROM test_relay.t1")
        f_out = tempfile.TemporaryFile()
        format_tabular_list(f_out, ['a', 'b'], rows, {"separator": ","})
        f_out.seek(0)
        for row in f_out.readlines():
            self.results.append(row)
            if self.debug:
                print row,

    def run(self):
        test_num = 1

        self.server2.exec_query(_SET_SQL_LOG_BIN.format('0'))
        self.server2.exec_query(_GRANT_QUERY)
        self.server2.exec_query(_SET_SQL_LOG_BIN.format('1'))
        self.server3.exec_query(_SET_SQL_LOG_BIN.format('0'))
        self.server3.exec_query(_GRANT_QUERY)
        self.server3.exec_query(_SET_SQL_LOG_BIN.format('1'))
        self.server4.exec_query(_SET_SQL_LOG_BIN.format('0'))
        self.server4.exec_query(_GRANT_QUERY)
        self.server4.exec_query(_SET_SQL_LOG_BIN.format('1'))
        self.server5.exec_query(_SET_SQL_LOG_BIN.format('0'))
        self.server5.exec_query(_GRANT_QUERY)
        self.server5.exec_query(_SET_SQL_LOG_BIN.format('1'))

        # create a database then add data shutting down slaves to create
        # a scenario where the candidate slave has fewer transactions than
        # the slaves to execute the relay log execution logic and the
        # check for transactions to skip connecting candidate to slaves as
        # its master

        self.server1.exec_query("CREATE DATABASE test_relay")
        self.server1.exec_query("CREATE TABLE test_relay.t1"
                                "(a int, b char(20)) ENGINE=INNODB")
        self.server1.exec_query("INSERT INTO test_relay.t1 VALUES (1, 'one')")

        self.wait_for_slave(self.server1, self.server2)
        self.wait_for_slave(self.server1, self.server3)

        # Stop the candidate and one other slave
        self.server2.exec_query("STOP SLAVE")
        self.server3.exec_query("STOP SLAVE")

        self.server1.exec_query("INSERT INTO test_relay.t1 VALUES (2, 'two')")

        self.wait_for_slave(self.server1, self.server4)

        # Stop the third slave
        self.server4.exec_query("STOP SLAVE SQL_THREAD")

        self.server1.exec_query("INSERT INTO test_relay.t1 "
                                "VALUES (3, 'three')")
        self.server1.exec_query("INSERT INTO test_relay.t1 "
                                "VALUES (4, 'four')")

        self.wait_for_slave(self.server1, self.server5)

        # Show contents of server
        for server in self.servers_list:
            self.dump_table(server)

        comment = ("Test case {0} - failover to {1}:{2} with relay log "
                   "entries".format(test_num, self.server2.host,
                                    self.server2.port))
        slaves = ",".join([self.slave2_conn, self.slave3_conn,
                           self.slave4_conn])
        cmd_str = "mysqlrpladmin.py --master={0} ".format(self.master_conn)
        cmd_opts = (" --candidates={0} --slaves={1} failover -vvv "
                    "--force".format(self.slave1_conn, slaves))

        res = mutlib.System_test.run_test_case(self, 0, cmd_str + cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Wait for slaves
        for slave in [self.server3, self.server4, self.server5]:
            self.wait_for_slave(self.server2, slave)

        # Show contents of server
        for server in self.servers_list:
            # ROLLBACK just to close any pending transaction, otherwise
            # dump_table() can return inconsistent values.
            server.rollback()
            self.dump_table(server)

        comment = ("Test case {0} - failover to {1}:{2} with skipping "
                   "slaves".format(test_num, self.server3.host,
                                   self.server3.port))
        slaves = ",".join([self.slave3_conn, self.slave4_conn])
        cmd_str = ("mysqlrpladmin.py --master={0} --candidates={1} "
                   "--slaves={2} failover -vvv"
                   "".format(self.slave1_conn, self.slave2_conn, slaves))
        res = mutlib.System_test.run_test_case(self, 0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Now we return the topology to its original state for other tests
        rpl_admin.test.reset_topology(self)

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)
        self.replace_substring(str(self.s4_port), "PORT5")

        # Strip health report - not needed.
        self.remove_result("+-")
        self.remove_result("| ")

        # Strip GTID detailed information
        self.replace_result("# QUERY = SELECT WAIT_UNTIL_SQL_THREAD_AFTER",
                            "# QUERY = SELECT WAIT_UNTIL_SQL_THREAD_AFTER"
                            "_GTIDS(XXXXXXXXX)\n")
        self.replace_result("# Return Code", "# Return Code = XXXX\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        for server in self.servers_list:
            self.drop_db(server, "test_relay")
        return rpl_admin.test.cleanup(self)
