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
rpl_sync_filters test.
"""

import os

import rpl_sync

from mysql.utilities.exception import MUTLibError


MYSQL_OPTS_RPL_FILTERS = ('"--log-bin=mysql-bin --skip-slave-start '
                          '--log-slave-updates --gtid-mode=on '
                          '--enforce-gtid-consistency '
                          '--report-host=localhost --report-port={port} '
                          '--sync-master-info=1 '
                          '--master-info-repository=TABLE '
                          '{rpl_filter_opt}"')

OPT_BINLOG_DO_DB = '--binlog-do-db=test_rplsync_db1'
OPT_BINLOG_IGNORE_DB = '--binlog-ignore-db=test_rplsync_db2'

OPT_REPLICATE_DO_DB = '--replicate-do-db=test_rplsync_db1'
OPT_REPLICATE_IGNORE_DB = '--replicate-ignore-db=test_rplsync_db2'
OPT_REPLICATE_DO_TABLE = '--replicate-do-table=test_rplsync_db1.t1'
OPT_REPLICATE_IGNORE_TABLE = '--replicate-ignore-table=test_rplsync_db1.t2'
OPT_REPLICATE_WILD_DO_TABLE = '--replicate-wild-do-table=test%db_.%'
OPT_REPLICATE_WILD_IGNORE_TABLE = (
    '--replicate-wild-ignore-table=test\\\\_rplsync\\\\_db1.%3'
)


class test(rpl_sync.test):
    """Test the detection of the use of replication filters with mysqlrplsync
    and if database/table consistency checks are correctly skipped.

    More info about replication rules:
    http://dev.mysql.com/doc/refman/5.6/en/replication-rules.html

    NOTE: Test extend the base rpl_sync test and it has the same prerequisites.
    """

    server5 = None
    server6 = None
    server7 = None

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers with supported replication filter options.
        self.server0 = self.servers.get_server(0)
        mysqld = MYSQL_OPTS_RPL_FILTERS.format(
            port=self.servers.view_next_port(),
            rpl_filter_opt=OPT_BINLOG_DO_DB
        )
        self.server1 = self.spawn_server("rpl_master1_gtid", mysqld, True)

        mysqld = MYSQL_OPTS_RPL_FILTERS.format(
            port=self.servers.view_next_port(),
            rpl_filter_opt=OPT_BINLOG_IGNORE_DB
        )
        self.server2 = self.spawn_server("rpl_master2_gtid", mysqld, True)

        # Note: option replicate-wild-do-table cannot be used here because it
        # has known issues.
        mysqld = MYSQL_OPTS_RPL_FILTERS.format(
            port=self.servers.view_next_port(),
            rpl_filter_opt=OPT_REPLICATE_DO_TABLE
        )
        self.server3 = self.spawn_server("rep_slave1_gtid", mysqld, True)

        rpl_filter = "{0} {1}".format(
            OPT_REPLICATE_IGNORE_TABLE,
            OPT_REPLICATE_WILD_IGNORE_TABLE
        )
        mysqld = MYSQL_OPTS_RPL_FILTERS.format(
            port=self.servers.view_next_port(),
            rpl_filter_opt=rpl_filter
        )
        self.server4 = self.spawn_server("rep_slave2_gtid", mysqld, True)

        # Spawn servers with not supported replication filter options.
        mysqld = MYSQL_OPTS_RPL_FILTERS.format(
            port=self.servers.view_next_port(),
            rpl_filter_opt=OPT_REPLICATE_DO_DB
        )
        self.server5 = self.spawn_server("rep_slave3_gtid", mysqld, True)

        mysqld = MYSQL_OPTS_RPL_FILTERS.format(
            port=self.servers.view_next_port(),
            rpl_filter_opt=OPT_REPLICATE_IGNORE_DB
        )
        self.server6 = self.spawn_server("rep_slave4_gtid", mysqld, True)

        mysqld = MYSQL_OPTS_RPL_FILTERS.format(
            port=self.servers.view_next_port(),
            rpl_filter_opt=OPT_REPLICATE_WILD_DO_TABLE
        )
        self.server7 = self.spawn_server("rep_slave5_gtid", mysqld, True)

        # Reset spawned servers (clear binary log and GTID_EXECUTED set)
        # with supported filter options (first topology).
        self.reset_master([self.server1, self.server3, self.server4])

        # Set (first) replication topology.
        self.reset_topology([self.server3, self.server4])

        return True

    def run(self):
        cmd_base = "mysqlrplsync.py"
        master1_con = self.build_connection_string(self.server1).strip(' ')
        master2_con = self.build_connection_string(self.server2).strip(' ')
        slave1_con = self.build_connection_string(self.server3).strip(' ')
        slave2_con = self.build_connection_string(self.server4).strip(' ')
        slaves_con = ",".join([slave1_con, slave2_con])
        slave3_con = self.build_connection_string(self.server5).strip(' ')
        slave4_con = self.build_connection_string(self.server6).strip(' ')
        slave5_con = self.build_connection_string(self.server7).strip(' ')

        if self.debug:
            print("\nCreate test databases and tables on master.")
        rpl_sync.create_test_db(self.server1, db_num=4)

        if self.debug:
            print("\nWait for slaves to catch up with master.")
        self.wait_for_slaves([self.server3, self.server4])

        # Skip check of databases with replication filters (case 1).
        # master: --binlog-do-db=test_rplsync_db1
        # slave1: --replicate-do-table=test_rplsync_db1.t1
        # slave2: --replicate-ignore-table=test_rplsync_db1.t2
        #         --replicate-wild-ignore-table=test\_rplsync\_db1.%3
        test_num = 1
        comment = ("Test case {0} - check replication filters skip (case 1)."
                   "").format(test_num)
        cmd = "{0} --master={1} --slaves={2} -v".format(cmd_base, master1_con,
                                                        slaves_con)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - check replication filters skip (case 1) - "
                   "only with slaves.").format(test_num)
        cmd = "{0} --slaves={1} -v".format(cmd_base, slaves_con)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        if self.debug:
            print("\nDrop test databases on master.")
        rpl_sync.drop_test_db(self.server1, db_num=4)

        if self.debug:
            print("\nWait for slaves to catch up with master.")
        self.wait_for_slaves([self.server3, self.server4])

        if self.debug:
            print("\nReset topology with a new master.")
        self.reset_master([self.server2, self.server3, self.server4])
        self.reset_topology([self.server3, self.server4], master=self.server2)

        if self.debug:
            print("\nCreate test databases and tables on master.")
        rpl_sync.create_test_db(self.server2, db_num=4)

        if self.debug:
            print("\nWait for slaves to catch up with master.")
        self.wait_for_slaves([self.server3, self.server4], master=self.server2)

        # Skip check of databases with replication filters (case 2).
        # master: --binlog-ignore-db=test_rplsync_db2
        # slave1: --replicate-do-table=test_rplsync_db1.t1
        # slave2: --replicate-ignore-table=test_rplsync_db1.t2
        #         --replicate-wild-ignore-table=test\_rplsync\_db1.%3
        test_num += 1
        comment = ("Test case {0} - check replication filters skip (case 2)."
                   "").format(test_num)
        cmd = "{0} --master={1} --slaves={2} -v".format(cmd_base, master2_con,
                                                        slaves_con)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - check replication filters skip (case 2) - "
                   "only with slaves.").format(test_num)
        cmd = "{0} --slaves={1} -v".format(cmd_base, slaves_con)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        if self.debug:
            print("\nReset topology with new slaves.")
        self.reset_master([self.server2, self.server5, self.server6,
                           self.server7])
        self.reset_topology([self.server5, self.server6, self.server7],
                            master=self.server2)

        # Options replicate-do-db, replicate-ignore-db, and
        # replicate-wild-do-db are not supported due to known issues on the
        # server, leading to inconsistent GTID_EXECUTED sets.
        test_num += 1
        comment = ("Test case {0} - error using replicate-do-db."
                   "").format(test_num)
        cmd = "{0} --master={1} --slaves={2}".format(cmd_base, master2_con,
                                                     slave3_con)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error using replicate-ignore-db."
                   "").format(test_num)
        cmd = "{0} --master={1} --slaves={2}".format(cmd_base, master2_con,
                                                     slave4_con)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - error using replicate-wild-do-db."
                   "").format(test_num)
        cmd = "{0} --master={1} --slaves={2}".format(cmd_base, master2_con,
                                                     slave5_con)
        res = self.run_test_case(1, cmd, comment)
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
        self.replace_substring(str(self.server5.port), "PORT5")
        self.replace_substring(str(self.server6.port), "PORT6")
        self.replace_substring(str(self.server7.port), "PORT7")

        # Force order of filters results (non-deterministic dictionary order).
        # pylint: disable=W1401
        self.force_lines_order(
            ("# Slave 'localhost@PORT3':\n",
             "#   - replicate_do_table: test_rplsync_db1.t1\n",
             "# Slave 'localhost@PORT4':\n",
             "#   - replicate_ignore_table: test_rplsync_db1.t2\n",
             "#   - replicate_wild_ignore_table: test\_rplsync\_db1.%3\n")
        )

        # Force order of checksum results (due to multiprocessing).
        # pylint: disable=W1401
        self.force_lines_order(
            ("#   [OK] `test_rplsync_db1`.`t1` checksum for server "
             "'localhost@PORT3'.\n",
             "#   [OK] `test_rplsync_db1`.`t1` checksum for server "
             "'localhost@PORT4'.\n")
        )

        # Force order of skip table results (non-deterministic set/dict order).
        self.force_lines_order(
            ("# [SKIP] Table 't2' check for 'localhost@PORT3' - filtered by "
             "replication rule.\n",
             "# [SKIP] Table 't2' check for 'localhost@PORT4' - filtered by "
             "replication rule.\n")
        )
        self.force_lines_order(
            ("# [SKIP] Table 't3' check for 'localhost@PORT3' - filtered by "
             "replication rule.\n",
             "# [SKIP] Table 't3' check for 'localhost@PORT4' - filtered by "
             "replication rule.\n")
        )
        self.force_lines_order(
            ("# [SKIP] Database 'test_rplsync_db0' check - filtered by "
             "replication rule.\n",
             "# [SKIP] Database 'test_rplsync_db2' check - filtered by "
             "replication rule.\n",
             "# [SKIP] Database 'test_rplsync_db3' check - filtered by "
             "replication rule.\n")
        )
        self.force_lines_order(
            ("# [SKIP] Table 't0' - filtered by replication rule on base "
             "server.\n",
             "# [SKIP] Table 't1' - filtered by replication rule on base "
             "server.\n",
             "# [SKIP] Table 't2' - filtered by replication rule on base "
             "server.\n",
             "# [SKIP] Table 't3' - filtered by replication rule on base "
             "server.\n")
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
            ['rep_master1_gtid', 'rep_master2_gtid', 'rep_slave1_gtid',
             'rep_slave2_gtid', 'rep_slave3_gtid', 'rep_slave4_gtid',
             'rep_slave5_gtid']
        )
        return True
