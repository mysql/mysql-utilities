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
rpl_admin_logfile test.
"""

import os
import stat

import mutlib
import rpl_admin

from mysql.utilities.exception import MUTLibError
from mysql.utilities.common.server import get_connection_dictionary
from mysql.utilities.common.messages import (MSG_UTILITIES_VERSION,
                                             MSG_MYSQL_VERSION)
from mysql.utilities import VERSION_STRING


_LOGNAME = "temp_log.txt"
_UTILITIES_VERSION_PHRASE = MSG_UTILITIES_VERSION.format(
    utility="mysqlrpladmin", version=VERSION_STRING)


class test(rpl_admin.test):
    """test replication administration commands
    This tests checks handling of accessibility of the log file (BUG#14208415)
    """

    def check_prerequisites(self):
        if self.servers.get_server(0).check_version_compat(5, 6, 5):
            raise MUTLibError("Test requires server version prior to 5.6.5")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"
        return rpl_admin.test.setup(self)

    def find_stop_phrase(self, logfile, comment, stop_phrase):
        """Find stop phrase in the log file.

        logfile[in]       Log filename.
        comment[in]       Test comment.
        stop_phrase[in]   Phrase to be found.

        Raises a MUTLibError if the phrase is not found.
        """
        # Check result code from stop_process then read the log to find the
        # key phrase.
        found_row = False
        with open(logfile, "r") as file_:
            rows = file_.readlines()
            if self.debug:
                print("# Looking in log for: {0}".format(stop_phrase))
            for row in rows:
                if stop_phrase in row:
                    found_row = True
                    if self.debug:
                        print("# Found in row = '{0}'."
                              "".format(row[:-1]))
                    break

        if not found_row:
            if self.debug:
                print("# ERROR: Cannot find entry in log:")
                for row in rows:
                    print(row)
            raise MUTLibError("{0}: failed - cannot find entry in log."
                              "".format(comment))

    def run(self):
        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave_conn = self.build_connection_string(self.server2).strip(' ')

        # For this test, it's OK when master and slave are the same
        master_str = "--master={0}".format(master_conn)
        slave_str = "--slave={0}".format(slave_conn)

        # command used in test cases: replace 3 element with location of
        # log file.
        cmd = [
            "mysqlrpladmin.py",
            master_str,
            slave_str,
            "--log={0}".format(_LOGNAME),
            "health",
        ]

        # Test Case 1
        test_num = 1
        comment = "Test Case {0} - Log file is newly created".format(test_num)
        res = mutlib.System_test.run_test_case(
            self, 0, ' '.join(cmd), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Test Case 2
        test_num += 1
        comment = "Test Case {0} - Log file is reopened".format(test_num)
        res = mutlib.System_test.run_test_case(
            self, 0, ' '.join(cmd), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Test Case 3
        test_num += 1
        comment = ("Test Case {0} - Log file can not be "
                   "written to".format(test_num))
        os.chmod(_LOGNAME, stat.S_IREAD)  # Make log read-only
        res = mutlib.System_test.run_test_case(
            self, 2, ' '.join(cmd), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Find MySQL and Utilities versions in the log
        self.find_stop_phrase(_LOGNAME, comment, MSG_UTILITIES_VERSION.format(
            utility="mysqlrpladmin", version=VERSION_STRING))

        # Find master MySQL server version in the log
        master_host_port = (
            "{host}:{port}".format(**get_connection_dictionary(master_conn)))
        self.find_stop_phrase(_LOGNAME, comment, MSG_MYSQL_VERSION.format(
            server=master_host_port, version=self.server1.get_version()))

        # Find slave MySQL server version in the log
        slave_host_port = (
            "{host}:{port}".format(**get_connection_dictionary(slave_conn)))
        self.find_stop_phrase(_LOGNAME, comment, MSG_MYSQL_VERSION.format(
            server=slave_host_port, version=self.server2.get_version()))

        # Mask out non-deterministic data
        rpl_admin.test.do_masks(self)
        self.remove_result("NOTE: Log file 'temp_log.txt' does not exist. "
                           "Will be created.")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        try:
            os.chmod(_LOGNAME, stat.S_IWRITE)
            os.unlink(_LOGNAME)
        except OSError:
            if self.debug:
                print "# failed removing temporary log file {0}".format(
                    _LOGNAME)
        return rpl_admin.test.cleanup(self)
