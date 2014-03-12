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

import os

import rpl_sync

from mysql.utilities.exception import MUTLibError


_MYSQL_OPTS_GTID_OFF = ('"--log-bin=mysql-bin --skip-slave-start '
                        '--report-host=localhost --report-port={port} '
                        '--sync-master-info=1 --master-info-repository=TABLE"')


class test(rpl_sync.test):
    """Test replication synchronization checker options and the correct
    identification of consistency issues.

    NOTE: Test extend the base rpl_sync test and it has the same prerequisites.
    """

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers.
        self.server0 = self.servers.get_server(0)
        mysqld = rpl_sync.MYSQL_OPTS_DEFAULT.format(
            port=self.servers.view_next_port()
        )
        self.server1 = self.spawn_server("rep_master_gtid", mysqld, True)
        mysqld = rpl_sync.MYSQL_OPTS_DEFAULT.format(
            port=self.servers.view_next_port()
        )
        self.server2 = self.spawn_server("rep_slave1_gtid", mysqld, True)
        mysqld = rpl_sync.MYSQL_OPTS_DEFAULT.format(
            port=self.servers.view_next_port()
        )
        self.server3 = self.spawn_server("rep_slave2_gtid", mysqld, True)
        mysqld = _MYSQL_OPTS_GTID_OFF.format(
            port=self.servers.view_next_port()
        )
        self.server4 = self.spawn_server("rep_slave3_no_gtid", mysqld, True)

        # Reset spawned servers (clear binary log and GTID_EXECUTED set).
        self.reset_master([self.server1, self.server2, self.server3])

        # Set replication topology.
        self.reset_topology([self.server2, self.server3])

        return True

    def run(self):
        cmd_base = "mysqlrplsync.py"
        master_con = self.build_connection_string(self.server1).strip(' ')
        slave1_con = self.build_connection_string(self.server2).strip(' ')
        slave2_con = self.build_connection_string(self.server3).strip(' ')
        slave3_con = self.build_connection_string(self.server4).strip(' ')
        slaves_con = ",".join([slave1_con, slave2_con, slave3_con])

        # Show help.
        test_num = 1
        comment = ("Test case {0} - show help."
                   "").format(test_num)
        cmd = "{0} --help".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        if self.debug:
            print("\nCreate test databases and tables on master.")
        rpl_sync.create_test_db(self.server1)
        # Add another database (empty) to be replicated on all slaves and
        # checked when using the --exclude option.
        self.server1.exec_query('CREATE DATABASE empty_db')

        if self.debug:
            print("\nInsert data into test database on master.")
        rpl_sync.load_test_data(self.server1)

        if self.debug:
            print("\nWait for slaves to catch up with master.")
        self.wait_for_slaves()

        # Skip servers with GTID disabled.
        test_num += 1
        comment = ("Test case {0} - skip slave with GTID OFF."
                   "").format(test_num)
        cmd = "{0} --master={1} --slaves={2}".format(cmd_base, master_con,
                                                     slaves_con)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        slaves_con = ",".join([slave1_con, slave2_con])

        if self.debug:
            print("\nStop one of the slaves.")
        self.server2.exec_query('STOP SLAVE')

        # Skip sync for stopped slaves.
        test_num += 1
        comment = ("Test case {0} - skip sync for stopped slaves."
                   "").format(test_num)
        cmd = "{0} --master={1} --slaves={2}".format(cmd_base, master_con,
                                                     slaves_con)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        if self.debug:
            print("\nCreate a new database on stopped slave and on master.")
        self.server2.exec_query('CREATE DATABASE `only_on_slave_db`')
        self.server1.exec_query('SET SQL_LOG_BIN=0')
        self.server1.exec_query('CREATE DATABASE `only_on_master_db`')
        self.server1.exec_query('SET SQL_LOG_BIN=1')

         # Identify missing databases.
        test_num += 1
        comment = ("Test case {0} - identify missing database."
                   "").format(test_num)
        cmd = "{0} --master={1} --slaves={2}".format(cmd_base, master_con,
                                                     slaves_con)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        if self.debug:
            print("\nChange table definition on slave.")
        self.server2.exec_query('ALTER TABLE `test_rplsync_db`.`t0` '
                                'MODIFY rnd_txt0 VARCHAR(50)')

        # Different table definition.
        test_num += 1
        comment = ("Test case {0} - identify table with different definition."
                   "").format(test_num)
        cmd = "{0} --master={1} --slaves={2}".format(cmd_base, master_con,
                                                     slaves_con)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        if self.debug:
            print("\nRemove tables on master and slave.")
        last_tbl = '`t{0}`'.format(rpl_sync.TEST_DB_NUM_TABLES-1)
        self.server1.exec_query('SET SQL_LOG_BIN=0')
        self.server1.exec_query('DROP TABLE `test_rplsync_db`.'
                                '{0}'.format(last_tbl))
        self.server1.exec_query('SET SQL_LOG_BIN=1')
        self.server2.exec_query('DROP TABLE `test_rplsync_db`.`t0`')

        # Identify missing tables.
        test_num += 1
        comment = ("Test case {0} - identify missing tables."
                   "").format(test_num)
        cmd = "{0} --master={1} --slaves={2}".format(cmd_base, master_con,
                                                     slaves_con)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        if self.debug:
            print("\nChanging data on slaves.")
        self.server2.exec_query("UPDATE `test_rplsync_db`.`t1` "
                                "SET rnd_txt0='changed value' "
                                "WHERE id=1".format(last_tbl))
        self.server3.exec_query("INSERT INTO `test_rplsync_db`.`t0` "
                                "(rnd_txt0) VALUES ('new value')")

        # Identify data difference.
        test_num += 1
        comment = ("Test case {0} - identify data differences on tables."
                   "").format(test_num)
        cmd = "{0} --master={1} --slaves={2}".format(cmd_base, master_con,
                                                     slaves_con)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Check a specific database.
        test_num += 1
        comment = ("Test case {0} - check a specific database."
                   "").format(test_num)
        cmd = ("{0} --master={1} --slaves={2} "
               "test_rplsync_db").format(cmd_base, master_con, slaves_con)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Exclude check of a specific database.
        test_num += 1
        comment = ("Test case {0} - exclude a specific database."
                   "").format(test_num)
        cmd = ("{0} --master={1} --slaves={2} "
               "--exclude=test_rplsync_db").format(cmd_base, master_con,
                                                   slaves_con)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Check a specific table.
        test_num += 1
        comment = ("Test case {0} - check a specific table."
                   "").format(test_num)
        cmd = ("{0} --master={1} --slaves={2} "
               "test_rplsync_db.t0").format(cmd_base, master_con, slaves_con)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Exclude check of a specific table.
        test_num += 1
        comment = ("Test case {0} - exclude a specific table."
                   "").format(test_num)
        cmd = ("{0} --master={1} --slaves={2} "
               "--exclude=test_rplsync_db.t0").format(cmd_base, master_con,
                                                      slaves_con)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Include/exclude data to check (using backtick quotes).
        test_num += 1
        comment = ("Test case {0} - include/exclude data (using backticks)."
                   "").format(test_num)
        if os.name == 'posix':
            cmd_arg = ("'`test_rplsync_db`' --exclude='`test_rplsync_db`.`t0`,"
                       "`test_rplsync_db`.`t1`'")
        else:
            cmd_arg = ('"`test_rplsync_db`" --exclude="`test_rplsync_db`.`t0`,'
                       '`test_rplsync_db`.`t1`"')
        cmd = ("{0} --master={1} --slaves={2} "
               "{3}").format(cmd_base, master_con, slaves_con, cmd_arg)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Check a specific database that does not exist.
        test_num += 1
        comment = ("Test case {0} - check a non existing database."
                   "").format(test_num)
        cmd = ("{0} --master={1} --slaves={2} "
               "no_exist_db").format(cmd_base, master_con, slaves_con)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask out non-deterministic data
        self.do_masks()

        return True

    def do_masks(self):
        self.replace_substring(str(self.server1.port), "PORT1")
        self.replace_substring(str(self.server2.port), "PORT2")
        self.replace_substring(str(self.server3.port), "PORT3")
        self.replace_substring(str(self.server4.port), "PORT4")

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqlrplsync"
                                           " version", 6)

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
        self.force_lines_order(
            ("#   [DIFF] Database 'only_on_master_db' NOT on server "
             "'localhost@PORT2'.\n",
             "#   [DIFF] Database 'only_on_master_db' NOT on server "
             "'localhost@PORT3'.\n")
        )
        self.force_lines_order(
            ("#   [DIFF] Table NOT on base server but found on "
             "'localhost@PORT2': t3\n",
             "#   [DIFF] Table NOT on base server but found on "
             "'localhost@PORT3': t3\n")
        )
        self.force_lines_order(
            ("#   [DIFF] `test_rplsync_db`.`t1` checksum for server "
             "'localhost@PORT2'.\n",
             "#   [OK] `test_rplsync_db`.`t1` checksum for server "
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
            ['rep_master_gtid', 'rep_slave1_gtid', 'rep_slave2_gtid',
             'rep_slave3_no_gtid']
        )
        return True
