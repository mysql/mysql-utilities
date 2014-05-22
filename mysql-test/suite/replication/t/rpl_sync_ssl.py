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
rpl_sync test using ssl.
"""

import threading
import time

import rpl_sync
from mutlib.ssl_certs import (ssl_pass, ssl_user, ssl_util_opts, ssl_c_ca,
                              ssl_c_cert, ssl_c_key, SSL_OPTS)

from mysql.utilities.common.server import Server
from mysql.utilities.common.user import grant_proxy_ssl_privileges
from mysql.utilities.exception import MUTLibError, UtilError


MYSQL_OPTS_DEFAULT = ('"--log-bin=mysql-bin --skip-slave-start '
                      '--log-slave-updates --gtid-mode=on '
                      '--enforce-gtid-consistency '
                      '--report-host=localhost --report-port={port} '
                      '--sync-master-info=1 --master-info-repository=TABLE '
                      '{ssl}"').format(port='{port}', ssl=SSL_OPTS)

TEST_DB_NUM_TABLES = 4
TEST_DB_NUM_ROWS = 20

RPL_TIMEOUT = 300
RPL_CHECK_INTERVAL = 5


class test(rpl_sync.test):
    """Test replication synchronization checker using SSL.

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

        for server in [self.server1, self.server2, self.server3]:
            try:
                grant_proxy_ssl_privileges(server, ssl_user, ssl_pass)
            except UtilError as err:
                raise MUTLibError("{0} on:{1}".format(err.errmsg,
                                                      server.role))
        conn_info = {
            'user': ssl_user,
            'passwd': ssl_pass,
            'host': self.server0.host,
            'port': self.server0.port,
            'ssl_ca': ssl_c_ca,
            'ssl_cert': ssl_c_cert,
            'ssl_key': ssl_c_key,
        }

        conn_info['port'] = self.server1.port
        conn_info['port'] = self.server1.port
        self.server1 = Server.fromServer(self.server1, conn_info)
        self.server1.connect()

        conn_info['port'] = self.server2.port
        conn_info['port'] = self.server2.port
        self.server2 = Server.fromServer(self.server2, conn_info)
        self.server2.connect()

        conn_info['port'] = self.server3.port
        conn_info['port'] = self.server3.port
        self.server3 = Server.fromServer(self.server3, conn_info)
        self.server3.connect()

        # Reset spawned servers (clear binary log and GTID_EXECUTED set)
        self.reset_master([self.server1, self.server2, self.server3])

        # Set replication topology.
        self.reset_topology([self.server2, self.server3])

        return True

    def run(self):
        cmd_base = "mysqlrplsync.py"
        master_con = self.build_connection_string(self.server1).strip(' ')
        slave1_con = self.build_connection_string(self.server2).strip(' ')
        slave2_con = self.build_connection_string(self.server3).strip(' ')
        slaves_con = "{0},{1}".format(slave1_con, slave2_con)

        # Check the data consistency of empty servers.
        test_num = 1
        comment = ("Test case {0} - check empty servers."
                   "").format(test_num)
        cmd = "{0} --master={1} --slaves={2} {3}".format(cmd_base, master_con,
                                                         slaves_con,
                                                         ssl_util_opts())
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Create example database on master and wait for it to be replicated
        # on all slaves.
        if self.debug:
            print("\nCreate test database and tables on master.")
        rpl_sync.create_test_db(self.server1)

        # Wait for slaves to catch up, otherwise mysqlrplsync might find tables
        # missing on slaves (which is normal).
        if self.debug:
            print("\nWait for slaves to catch up with master.")
        self.wait_for_slaves()

        # Load data on the master in a separated thread to perform the data
        # consistency checks at the same time.
        load_thread = threading.Thread(target=rpl_sync.load_test_data,
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
        cmd = ("{0} --master={1} --discover-slaves-login=root:root {2}"
               "").format(cmd_base, master_con, ssl_util_opts())
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
        rpl_sync.drop_test_db(self.server1)
        if self.debug:
            print("\nCreate test database and tables on master.")
        rpl_sync.create_test_db(self.server1)

        # Wait for slaves to catch up (avoiding non-deterministic results).
        if self.debug:
            print("\nWait for slaves to catch up with master.")
        self.wait_for_slaves()

        # Start a new thread to load/insert data (can only be started once).
        load_thread = threading.Thread(target=rpl_sync.load_test_data,
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
        cmd = "{0} --slaves={1} {2}".format(cmd_base, slaves_con,
                                            ssl_util_opts())
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
        cmd = "{0} --master={1} --slaves={2} {3}".format(cmd_base, master_con,
                                                         slaves_con,
                                                         ssl_util_opts())
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask out non-deterministic data
        self.do_masks()

        return True
