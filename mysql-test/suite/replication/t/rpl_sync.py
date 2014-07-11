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
rpl_sync test.
"""

import os
import random
import string
import threading
import time

import rpl_admin

from mysql.utilities.common.server import Server
from mysql.utilities.exception import MUTLibError


MYSQL_OPTS_DEFAULT = ('"--log-bin=mysql-bin --skip-slave-start '
                      '--log-slave-updates --gtid-mode=on '
                      '--enforce-gtid-consistency '
                      '--report-host=localhost --report-port={port} '
                      '--sync-master-info=1 --master-info-repository=TABLE"')

TEST_DB_NUM_TABLES = 4
TEST_DB_NUM_ROWS = 20

RPL_TIMEOUT = 300
RPL_CHECK_INTERVAL = 5


def create_test_db(server, db_num=1):
    """Create test databases and tables.

    server[in]      Target server to create the test databases and tables.
    db_num[in]      Number of databases to create (by default: 1).
    """
    for db_index in xrange(db_num):
        db_name = '`test_rplsync_db{0}`'.format(
            '' if db_num == 1 else db_index
        )
        server.exec_query('CREATE DATABASE {0}'.format(db_name))
        # Need USE statement otherwise filtering rules will not be applied
        # correctly with statement based replication.
        server.exec_query("USE {0}".format(db_name))
        columns = []
        for table_index in xrange(TEST_DB_NUM_TABLES):
            columns.append('rnd_txt{0} VARCHAR(20)'.format(table_index))
            create_tbl_query = (
                'CREATE TABLE {0}.`t{1}` '
                '(id int UNSIGNED NOT NULL AUTO_INCREMENT, {2}, '
                'PRIMARY KEY(id)) '
                'ENGINE=INNODB').format(db_name, table_index,
                                        ', '.join(columns))
            server.exec_query(create_tbl_query)


def drop_test_db(server, db_num=1):
    """Drop the test databases.

    server[in]      Target server to create the test databases and tables.
    db_num[in]      Number of databases to create (by default: 1).
                    It is assumed that a matching number of test databases
                    have been previously created.
    """
    for db_index in xrange(db_num):
        db_name = '`test_rplsync_db{0}`'.format(
            '' if db_num == 1 else db_index
        )
        server.exec_query('DROP DATABASE {0}'.format(db_name))


def load_test_data(server, db_num=1):
    """Load/insert data into the test databases.

    A considerable amount of data should be considered in order to take some
    time to load, allowing mysqlrplsync to be executed at the same time the
    data is still being inserted.

    server[in]      Target server to load the test data.
    db_num[in]      Number of databases to load the data (by default: 1).
                    It is assumed that a matching number of test databases
                    have been previously created.

    Note: method prepared to be invoked by a different thread.
    """
    # Create a new server instance with a new connection (for multithreading).
    srv = Server({'conn_info': server})
    srv.connect()

    for db_index in xrange(db_num):
        db_name = '`test_rplsync_db{0}`'.format(
            '' if db_num == 1 else db_index
        )
        # Insert random data on all tables.
        random_values = string.letters + string.digits
        for _ in xrange(TEST_DB_NUM_ROWS):
            columns = []
            values = []
            for table_index in xrange(TEST_DB_NUM_TABLES):
                columns.append('rnd_txt{0}'.format(table_index))
                rnd_text = "".join(
                    [random.choice(random_values) for _ in xrange(20)]
                )
                values.append("'{0}'".format(rnd_text))
                insert = ("INSERT INTO {0}.`t{1}` ({2}) VALUES ({3})"
                          "").format(db_name, table_index, ', '.join(columns),
                                     ', '.join(values))
                srv.exec_query(insert)
                srv.commit()


class test(rpl_admin.test):
    """Test replication synchronization checker.

    This test runs the mysqlrplsync utility to test base sync features.

    NOTE: Test requires servers of version >= 5.6.14 (like the utility),
    because there is a known issue for START SLAVE UNTIL with the
    SQL_AFTER_GTIDS option for versions prior to 5.6.14. More information:
    https://dev.mysql.com/doc/refman/5.6/en/start-slave.html
    """

    def check_prerequisites(self):
        # Check required server version.
        if not self.servers.get_server(0).check_version_compat(5, 6, 14):
            raise MUTLibError("Test requires server version >= 5.6.14")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers
        self.server0 = self.servers.get_server(0)
        mysqld = MYSQL_OPTS_DEFAULT.format(port=self.servers.view_next_port())
        self.server1 = self.servers.spawn_server("rep_master_gtid", mysqld,
                                                 True)
        mysqld = MYSQL_OPTS_DEFAULT.format(port=self.servers.view_next_port())
        self.server2 = self.servers.spawn_server("rep_slave1_gtid", mysqld,
                                                 True)
        mysqld = MYSQL_OPTS_DEFAULT.format(port=self.servers.view_next_port())
        self.server3 = self.servers.spawn_server("rep_slave2_gtid", mysqld,
                                                 True)

        # Reset spawned servers (clear binary log and GTID_EXECUTED set)
        self.reset_master([self.server1, self.server2, self.server3])

        # Set replication topology.
        self.reset_topology([self.server2, self.server3])

        return True

    def run(self):
        self.mask_global = False  # Turn off global masks
        cmd_base = "mysqlrplsync.py"
        master_con = self.build_connection_string(self.server1).strip(' ')
        slave1_con = self.build_connection_string(self.server2).strip(' ')
        slave2_con = self.build_connection_string(self.server3).strip(' ')
        slaves_con = "{0},{1}".format(slave1_con, slave2_con)

        # Check the data consistency of empty servers.
        test_num = 1
        comment = ("Test case {0} - check empty servers."
                   "").format(test_num)
        cmd = "{0} --master={1} --slaves={2}".format(cmd_base, master_con,
                                                     slaves_con)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Create example database on master and wait for it to be replicated
        # on all slaves.
        if self.debug:
            print("\nCreate test database and tables on master.")
        create_test_db(self.server1)

        # Wait for slaves to catch up, otherwise mysqlrplsync might find tables
        # missing on slaves (which is normal).
        if self.debug:
            print("\nWait for slaves to catch up with master.")
        self.wait_for_slaves()

        # Load data on the master in a separated thread to perform the data
        # consistency checks at the same time.
        load_thread = threading.Thread(target=load_test_data,
                                       args=(self.server1,))
        load_thread.daemon = True
        load_thread.start()
        if self.debug:
            print("\nThread to load/insert data started.")
            start_time = time.time()
            end_time = None

        # Check data consistency specifying the master and using discovery.
        test_num += 1
        comment = ("Test case {0} - data consistency check with active "
                   "replication using master and slaves discovery."
                   "").format(test_num)
        cmd = ("{0} --master={1} --discover-slaves-login=root:root"
               "").format(cmd_base, master_con)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        if self.debug:
            alive = load_thread.is_alive()
            print("\nIs thread (loading data) still alive? "
                  "{0}.".format(alive))
            if not alive and not end_time:
                end_time = time.time()
                print("\nTime to load data took less than: {0} "
                      "sec.".format(end_time - start_time))
            else:
                print("\nWaiting for thread (loading data) to finish.")

        # Wait for all the data to finish to be loaded.
        load_thread.join()
        if self.debug and not end_time:
            end_time = time.time()
            print("\nTime to load data: {0} "
                  "sec.".format(end_time - start_time))

        # Drop test database and recreate it on master.
        if self.debug:
            print("\nDrop test database on master.")
        drop_test_db(self.server1)
        if self.debug:
            print("\nCreate test database and tables on master.")
        create_test_db(self.server1)

        # Wait for slaves to catch up (avoiding non-deterministic results).
        if self.debug:
            print("\nWait for slaves to catch up with master.")
        self.wait_for_slaves()

        # Start a new thread to load/insert data (can only be started once).
        load_thread = threading.Thread(target=load_test_data,
                                       args=(self.server1,))
        load_thread.daemon = True
        load_thread.start()
        if self.debug:
            print("\nThread to load/insert data started.")
            start_time = time.time()
            end_time = None

        # Check data consistency specifying only the slaves.
        test_num += 1
        comment = ("Test case {0} - data consistency check with active "
                   "replication only between slaves (no master)."
                   "").format(test_num)
        cmd = "{0} --slaves={1}".format(cmd_base, slaves_con)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        if self.debug:
            alive = load_thread.is_alive()
            print("\nIs thread (loading data) still alive? "
                  "{0}.".format(alive))
            if not alive and not end_time:
                end_time = time.time()
                print("\nTime to load data took less than: {0} "
                      "sec.".format(end_time - start_time))
            else:
                print("Waiting for thread (loading data) to finish.")

        # Wait for all the data to finish to be loaded.
        load_thread.join()
        if self.debug and not end_time:
            end_time = time.time()
            print("\nTime to load data: {0} "
                  "sec.".format(end_time - start_time))

        # Perform data consistency check after loading all data.
        test_num += 1
        comment = ("Test case {0} - data consistency check between master and "
                   "specified slaves.").format(test_num)
        cmd = "{0} --master={1} --slaves={2}".format(cmd_base, master_con,
                                                     slaves_con)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask out non-deterministic data
        self.do_masks()

        return True

    def wait_for_slaves(self, slaves=None, master=None):
        """Wait for slaves to catch up with the master.
        """
        if not master:
            master = self.server1
        master_gtid_exec = master.get_gtid_executed()
        if not slaves:
            slaves = [self.server2, self.server3]
        tick = 0
        while tick <= RPL_TIMEOUT and slaves:
            slave = random.choice(slaves)
            slave_gtid_exec = slave.get_gtid_executed()
            if slave_gtid_exec == master_gtid_exec:
                slaves.remove(slave)
            else:
                time.sleep(RPL_CHECK_INTERVAL)
                tick += RPL_CHECK_INTERVAL

        if tick > RPL_TIMEOUT:
            raise MUTLibError("Timeout reached waiting for slaves to catch-up "
                              "with master")

    def do_masks(self):
        self.replace_substring(str(self.server1.port), "PORT1")
        self.replace_substring(str(self.server2.port), "PORT2")
        self.replace_substring(str(self.server3.port), "PORT3")

        self.remove_result("# - Slave '")

        # Force order of checksum results (due to multithreading).
        self.force_lines_order(
            ("#   [OK] `test_rplsync_db`.`t0` checksum for server "
             "'localhost@PORT2'.\n",
             "#   [OK] `test_rplsync_db`.`t0` checksum for server "
             "'localhost@PORT3'.\n")
        )
        self.force_lines_order(
            ("#   [OK] `test_rplsync_db`.`t1` checksum for server "
             "'localhost@PORT2'.\n",
             "#   [OK] `test_rplsync_db`.`t1` checksum for server "
             "'localhost@PORT3'.\n")
        )
        self.force_lines_order(
            ("#   [OK] `test_rplsync_db`.`t2` checksum for server "
             "'localhost@PORT2'.\n",
             "#   [OK] `test_rplsync_db`.`t2` checksum for server "
             "'localhost@PORT3'.\n")
        )
        self.force_lines_order(
            ("#   [OK] `test_rplsync_db`.`t3` checksum for server "
             "'localhost@PORT2'.\n",
             "#   [OK] `test_rplsync_db`.`t3` checksum for server "
             "'localhost@PORT3'.\n")
        )

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except OSError:
                pass
        # Kill all spawned servers.
        self.kill_server_list(
            ['rep_master_gtid', 'rep_slave1_gtid', 'rep_slave2_gtid']
        )
        return True
