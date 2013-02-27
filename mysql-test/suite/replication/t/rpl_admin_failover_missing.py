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
import mutlib
import rpl_admin
import tempfile
from mysql.utilities.exception import MUTLibError, UtilRplError
from mysql.utilities.common.format import format_tabular_list

_DEFAULT_MYSQL_OPTS = ' '.join(['"--log-bin=mysql-bin --skip-slave-start',
                                '--log-slave-updates --gtid-mode=on',
                                '--enforce-gtid-consistency',
                                '--report-host=localhost',
                                '--report-port=%s --sync-master-info=1',
                                '--master-info-repository=table"'])

_GTID_WAIT = "SELECT WAIT_UNTIL_SQL_THREAD_AFTER_GTIDS('%s', %s)"

_GRANT_QUERY = "GRANT REPLICATION SLAVE ON *.* TO 'rpl'@'rpl'"


class test(rpl_admin.test):
    """test replication administration commands
    This test runs the mysqlrpladmin utility on a known topology.

    Note: this test requires GTID enabled servers.
    """

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 9):
            raise MUTLibError("Test requires server version 5.6.9")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers
        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS % self.servers.view_next_port()
        self.server1 = self.spawn_server("rep_master_gtid", mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS % self.servers.view_next_port()
        self.server2 = self.spawn_server("rep_slave1_gtid", mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS % self.servers.view_next_port()
        self.server3 = self.spawn_server("rep_slave2_gtid", mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS % self.servers.view_next_port()
        self.server4 = self.spawn_server("rep_slave3_gtid", mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS % self.servers.view_next_port()
        self.server5 = self.spawn_server("rep_slave4_gtid", mysqld, True)

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
        except:
            pass

        cmd = " ".join(["mysqlreplicate.py --rpl-user=rpl:rpl ",
                        " --slave=%s" % self.slave4_conn,
                        " --master=%s" % self.master_conn])
        res = self.exec_util(cmd, self.res_fname)

        self.servers = [self.server1, self.server2, self.server3,
                        self.server4, self.server5]

        return True

    def wait_for_slave(self, master, slave):
        master_gtid = master.exec_query("SELECT @@GLOBAL.GTID_EXECUTED")
        master_gtids = master_gtid[0][0].split('\n')
        for gtid in master_gtids:
            try:
                res = slave.exec_query(_GTID_WAIT % (gtid.strip(','), 300))
            except UtilRplError, e:
                raise MUTLibError("Error executing %s: %s" %
                                   ((_GTID_WAIT % (gtid.strip(','), 300)),
                                   e.errmsg))
        return

    def dump_table(self, server):
        header = "# Dump of table test_relay.t1 for server %s:\n" % server.role
        self.results.append(header)
        if self.debug:
            print header
        rows = server.exec_query("SELECT * FROM test_relay.t1")
        f_out = tempfile.TemporaryFile()
        format_tabular_list(f_out, ['a', 'b'], rows, {"separator" : ","})
        f_out.seek(0)
        for row in f_out.readlines():
            self.results.append(row)
            if self.debug:
                print row,

    def run(self):

        test_num = 1

        self.server2.exec_query(_GRANT_QUERY)
        self.server3.exec_query(_GRANT_QUERY)
        self.server4.exec_query(_GRANT_QUERY)
        self.server5.exec_query(_GRANT_QUERY)

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
        for server in self.servers:
            self.dump_table(server)

        comment = "Test case %s - failover to %s:%s with relay log entries" % \
                  (test_num, self.server2.host, self.server2.port)
        slaves = ",".join([self.slave2_conn, self.slave3_conn,
                           self.slave4_conn])
        cmd_str = "mysqlrpladmin.py --master=%s " % self.master_conn
        cmd_opts = " --candidates=%s  " % self.slave1_conn
        cmd_opts += " --slaves=%s failover -vvv" % slaves
        res = mutlib.System_test.run_test_case(self, 0, cmd_str+cmd_opts,
                                               comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        # Wait for slaves
        for slave in [self.server3, self.server4, self.server5]:
            self.wait_for_slave(self.server2, slave)

        # Show contents of server
        for server in self.servers:
            self.dump_table(server)

        comment = ("Test case %s - failover to %s:%s with skipping slaves" %
                   (test_num, self.server3.host, self.server3.port))
        slaves = ",".join([self.slave3_conn, self.slave4_conn])
        cmd_str = ("mysqlrpladmin.py --master=%s --candidates=%s --slaves=%s "
                   "failover -vvv" %
                   (self.slave1_conn, self.slave2_conn, slaves))
        res = mutlib.System_test.run_test_case(self, 0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

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

    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        try:
            res = server.exec_query("DROP DATABASE `%s`" % db)
        except:
            return False
        return True

    def cleanup(self):
        for server in self.servers:
            self.drop_db(server, "test_relay")
        return rpl_admin.test.cleanup(self)
