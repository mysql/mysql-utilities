#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights reserved.
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
replicate_log_file test.
"""

import replicate

from mysql.utilities.exception import MUTLibError, UtilError


# Setup expected results.
_EXPECTED_RESULTS = [
    # ( Test_num, result)
    (1, [('001a',), ('001b',), ('001c',), ('002a',), ('002b',)]),
    (2, [('001c',), ('002a',), ('002b',)]),
    (3, [('002a',), ('002b',)]),
]


class test(replicate.test):
    """check parameters for the replicate utility
    This test executes the replicate utility to exercise the master log file
    and master log position options. It uses the replicate test as a parent
    for testing methods.
    """

    # There are four scenarios that need to be tested. This test shall include
    # test cases for (2)-(4) since (1) is covered in the existing replicate*
    # tests.
    #
    #   1) Start replication from current location of master log file
    #
    #   2) Start replication from the beginning (no log file info passed to CM)
    #
    #   3) Start replication from a specific log file and position.
    #
    #   4) Start replication from a specific log file.
    #

    master_log_info = None

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        return replicate.test.check_prerequisites(self)

    @staticmethod
    def stop_slave(comment, slave):
        """Stop and flush the slave to disconnect are reset.

        comment[in]      Comment.
        slave[in]        Slave instance.
        """
        try:
            slave.exec_query("STOP SLAVE")
            slave.exec_query("RESET SLAVE")
        except UtilError:
            raise MUTLibError("{0}: Cannot stop and reset slave.".format(
                comment))

    def setup(self):
        self.master_log_info = []

        # Setup master and slave
        self.server0 = self.servers.get_server(0)
        self.server1 = None
        self.server2 = None
        self.s1_serverid = None
        self.s2_serverid = None

        index = self.servers.find_server_by_name("rep_slave_log")
        if index >= 0:
            self.server1 = self.servers.get_server(index)
            try:
                res = self.server1.show_server_variable("server_id")
            except MUTLibError as err:
                raise MUTLibError("Cannot get replication slave "
                                  "server_id: {0}".format(err.errmsg))
            self.s1_serverid = int(res[0][1])
        else:
            self.s1_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(self.server0, self.s1_serverid,
                                                "rep_slave_log")
            if not res:
                raise MUTLibError("Cannot spawn replication slave server.")
            self.server1 = res[0]
            self.servers.add_new_server(self.server1, True)

        index = self.servers.find_server_by_name("rep_master")
        if index >= 0:
            self.server2 = self.servers.get_server(index)
            try:
                res = self.server2.show_server_variable("server_id")
            except MUTLibError as err:
                raise MUTLibError("Cannot get replication master "
                                  "server_id: {0}".format(err.errmsg))
            self.s2_serverid = int(res[0][1])
        else:
            self.s2_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(
                self.server0, self.s2_serverid, "rep_master",
                ' --mysqld="--log-bin=mysql-bin "')
            if not res:
                raise MUTLibError("Cannot spawn replication slave server.")
            self.server2 = res[0]
            self.servers.add_new_server(self.server2, True)

        self.drop_all()

        # Create a database
        try:
            self.server2.exec_query("RESET MASTER")
            self.server2.exec_query("CREATE DATABASE log_test")
            self.server2.exec_query("CREATE TABLE log_test.t1 (a char(30)) "
                                    "ENGINE=MEMORY")
        except MUTLibError:
            raise MUTLibError("Failed to create the test database.")

        # Populate with rows and save master log and position
        if not self.insert_row_rotate(("001a", "001b", "001c")):
            return False
        if not self.insert_row_rotate(("002a", "002b")):
            return False

        return True

    def insert_row_rotate(self, rows):
        """Insert a row, rotate the logs, and save master position, repeat.

        rows[in]    Rows to be inserted.
        """
        try:
            for row in rows:
                self.server2.exec_query('INSERT INTO log_test.t1 '
                                        'VALUES ("{0}")'.format(row))
                res = self.server2.exec_query("SHOW MASTER STATUS")
                if res and not res == []:
                    self.master_log_info.append((res[0][0], res[0][1]))
            self.server2.exec_query("FLUSH LOGS")
        except UtilError:
            return False
        return True

    def get_table_rows(self, comment):
        """Get list of rows from the slave.

        comment[in]     Comment.
        """
        try:
            res = self.server1.exec_query("SELECT * FROM log_test.t1")
            self.results.append(res)
        except UtilError as err:
            raise MUTLibError("{0}: Query failed. {1}".format(comment,
                                                              err.errmsg))

    def wait_for_slave(self, attempts):
        """Wait for slave to read the master log file.

        attempts[in]     Number of attempts.
        """
        i = 0
        while i < attempts:
            try:
                res = self.server1.exec_query("SHOW SLAVE STATUS")
                if res:
                    if res[0] == 'Waiting for master to send event':
                        return
            except UtilError:
                return
            i += 1
        return

    def run_and_record_test(self, comment, options):
        """Execute the test and record the results.

        comment[in]     Comment.
        options[in]     Options for running rpl test.
        """
        res = replicate.test.run_rpl_test(self, self.server1, self.server2,
                                          self.s1_serverid, comment, options,
                                          False, 0, False)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.wait_for_slave(10)

        # Record the results
        self.get_table_rows(comment)

        # Stop slave
        self.stop_slave(comment, self.server1)

        return True

    def run(self):
        self.res_fname = "result.txt"

        test_num = 1
        self.run_and_record_test("Test case {0} - start from "
                                 "beginning".format(test_num),
                                 "--start-from-beginning --quiet")

        self.server1.exec_query("DELETE FROM log_test.t1")

        test_num += 1
        self.run_and_record_test("Test case {0} - start from specific log, "
                                 "pos".format(test_num),
                                 "--master-log-file={0} --master-log-pos={1} "
                                 "--quiet".format(*self.master_log_info[1]))

        self.server1.exec_query("DELETE FROM log_test.t1")

        test_num += 1
        self.run_and_record_test("Test case {0} - start at start of specific "
                                 "log".format(test_num),
                                 "--master-log-file={0} "
                                 "--quiet".format(self.master_log_info[3][0]))

        if self.debug:
            i = 0
            print "\n", len(self.results), self.results
            print "\nTest Results: (test_case_num, result)"
            for result in _EXPECTED_RESULTS:
                print "Expected:", result
                if i + 2 > len(self.results):
                    print "Not enough actual results for this test case."
                else:
                    i += 1
                    post_rpl = self.results[i]
                    i += 1
                    print("Actual:   ({0}, {1})".format(result[0], post_rpl))

        return True

    def get_result(self):
        # Check results
        i = 0
        for result in _EXPECTED_RESULTS:
            if i + 2 > len(self.results):
                raise MUTLibError("Not enough results to compare test cases.")
            test_case = self.results[i]
            i += 1
            post_rpl = self.results[i]
            i += 1

            result_msg = "Result: {0} ? {1}".format(result[1], post_rpl)

            if not result[1] == post_rpl:
                return (False, "{0}: Result mismatch."
                               "\n{1}".format(test_case, result_msg))
            if self.debug:
                print "{0}:\n{1}".format(test_case, result_msg)
        return True, None

    def record(self):
        # Not a comparative test, returning True
        return True

    def drop_all(self):
        """Drops all databases created.
        """
        res1 = self.drop_db(self.server1, "log_test")
        res2 = self.drop_db(self.server2, "log_test")
        return res1 and res2

    def cleanup(self):
        # Kill servers that are only used in this test
        kill_list = ['rep_slave_log']
        return (replicate.test.cleanup(self) and
                self.kill_server_list(kill_list))
