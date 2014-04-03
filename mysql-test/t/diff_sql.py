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
diff_sql test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError, UtilError


class test(mutlib.System_test):
    """simple db diff
    This test executes a simple diff of two databases on separate servers.
    """

    server1 = None
    server2 = None
    need_server = False

    def check_prerequisites(self):
        if self.servers.get_server(0).check_version_compat(5, 6, 5):
            raise MUTLibError("Test requires server version prior to 5.6.5")
            # Need at least one server.
        self.server1 = None
        self.server2 = None
        self.need_server = False
        if not self.check_num_servers(2):
            self.need_server = True
        return self.check_num_servers(1)

    def _load_data(self, server, data_file):
        """Reads and executes SQL from data file.

        server[in]       Server instance.
        data_file[in]    File name containing SQL statements.
        """
        try:
            server.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: "
                              "{1}".format(data_file, err.errmsg))

    def setup(self):
        self.server1 = self.servers.get_server(0)
        if self.need_server:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers: {0}".format(
                    err.errmsg))
        self.server2 = self.servers.get_server(1)
        self.drop_all()
        self._load_data(self.server1,
                        os.path.normpath("./std_data/basic_data.sql"))
        self._load_data(self.server2,
                        os.path.normpath("./std_data/transform_data.sql"))

        return True

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        s1_conn = "--server1={0}".format(
            self.build_connection_string(self.server1))
        s2_conn = "--server2={0}".format(
            self.build_connection_string(self.server2))

        cmd_str = "mysqldiff.py {0} {1} util_test:util_test".format(s1_conn,
                                                                    s2_conn)
        cmd_str = "{0} --force --difftype=sql ".format(cmd_str)

        test_num = 1
        comment = ("Test case {0} - create transform for objects for "
                   "--changes-for=server1".format(test_num))
        cmd_opts = " --changes-for=server1 "
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - create transform for objects for "
                   "--changes-for=server2".format(test_num))
        cmd_opts = " --changes-for=server2 "
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - create transform for objects for "
                   "--changes-for=server1 with reverse".format(test_num))
        cmd_opts = " --changes-for=server1 --show-reverse "
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - create transform for objects for "
                   "--changes-for=server2 with reverse".format(test_num))
        cmd_opts = " --changes-for=server2 --show-reverse "
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Do transform for tables with different names
        cmd_str = "mysqldiff.py {0} {1} util_test.t1:util_test.t6".format(
            s1_conn, s2_conn)
        cmd_str = "{0} --force --difftype=sql ".format(cmd_str)

        self.server2.exec_query("CREATE TABLE util_test.t6 ENGINE=MyISAM AS "
                                "SELECT * FROM util_test.t1")

        test_num += 1
        comment = ("Test case {0} - create transform for renamed "
                   "table ".format(test_num))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Check to see if rename worked

        cmd_str = "mysqldiff.py {0} {1} util_test.t6:util_test.t6".format(
            s1_conn, s2_conn)
        cmd_str = "{0} --force --difftype=sql ".format(cmd_str)

        self.server1.exec_query("ALTER TABLE util_test.t1 "
                                "RENAME TO util_test.t6, ENGINE=MyISAM")

        test_num += 1
        comment = ("Test case {0} - test transform for renamed "
                   "table ".format(test_num))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # The following are necessary due to changes in character spaces
        # introduced with Python 2.7.X in the difflib.

        self.replace_result("+++ util_test.t1", "+++ util_test.t1\n")
        self.replace_result("+++ util_test.t2", "+++ util_test.t2\n")
        self.replace_result("--- util_test.t1", "--- util_test.t1\n")
        self.replace_result("+++ util_test.t2", "+++ util_test.t2\n")
        self.replace_result("--- util_test.t2", "--- util_test.t2\n")
        self.replace_result("+++ util_test.t3", "+++ util_test.t3\n")
        self.replace_result("--- util_test.t3", "--- util_test.t3\n")
        self.replace_result("+++ util_test.t6", "+++ util_test.t6\n")
        self.replace_result("--- util_test.t6", "--- util_test.t6\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_all(self):
        """Drops all databases and users created.
        """
        self.drop_db(self.server1, "util_test")
        self.drop_db(self.server2, "util_test")
        drop_user = ["DROP USER 'joe'@'user'", "DROP USER 'joe_wildcard'@'%'"]
        for drop in drop_user:
            try:
                self.server1.exec_query(drop)
                self.server2.exec_query(drop)
            except UtilError:
                pass
        return True

    def cleanup(self):
        try:
            os.unlink(self.res_fname)
        except OSError:
            pass
        return self.drop_all()
