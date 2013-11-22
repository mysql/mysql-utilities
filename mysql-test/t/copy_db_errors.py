#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
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
import copy_db
from mysql.utilities.exception import MUTLibError, UtilError


class test(copy_db.test):
    """check errors for copy db
    This test ensures the known error conditions are tested. It uses the
    copy_db test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return copy_db.test.check_prerequisites(self)

    def setup(self):
        res = copy_db.test.setup(self)
        if not res:
            return res
            # Create users for privilege testing
        self.drop_users()
        self.server1.exec_query("CREATE USER 'joe'@'localhost'")
        self.server1.exec_query("CREATE USER 'sam'@'localhost'")
        self.server1.exec_query(
            "GRANT SELECT, EVENT ON util_test.* TO " + "'joe'@'localhost'")
        self.server1.exec_query(
            "GRANT SELECT ON mysql.* TO " + "'joe'@'localhost'")
        self.server1.exec_query(
            "GRANT SHOW VIEW ON util_test.* TO " + "'joe'@'localhost'")

        self.server2.exec_query("CREATE USER 'joe'@'localhost'")
        self.server2.exec_query("CREATE USER 'sam'@'localhost'")
        self.server2.exec_query("GRANT ALL ON util_db_clone.* TO "
                                "'joe'@'localhost' WITH GRANT OPTION")
        self.server2.exec_query("GRANT SUPER, CREATE USER ON *.* TO "
                                "'joe'@'localhost'")
        return True

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1))
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server2))

        test_num = 1
        cmd_str = "mysqldbcopy.py --skip-gtid {0} ".format(from_conn)
        cmd_opts = "util_test:util_db_clone "
        comment = ("Test case {0} - error: no destination "
                   "specified".format(test_num))
        res = self.run_test_case(2, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = "mysqldbcopy.py --skip-gtid {0} {1} ".format(from_conn,
                                                               to_conn)
        cmd_opts = " "
        comment = ("Test case {0} - error: no database "
                   "specified".format(test_num))
        res = self.run_test_case(2, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = " wax\t::sad "
        comment = ("Test case {0} - error: cannot parse database "
                   "list".format(test_num))
        res = self.run_test_case(2, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = "NOT_THERE_AT_ALL:util_db_clone"
        comment = ("Test case {0} - error: old database doesn't "
                   "exist".format(test_num))
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = ("mysqldbcopy.py --skip-gtid {0} "
                   "--source=nope:nada@localhost:3306 ".format(to_conn))
        cmd_opts = "util_test:util_db_clone "
        comment = ("Test case {0} - error: cannot connect to "
                   "source".format(test_num))
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = ("mysqldbcopy.py --skip-gtid {0} "
                   "--destination=nope:nada@localhost:3306 ".format(from_conn))
        cmd_opts = "util_test:util_db_clone "
        comment = ("Test case {0} - error: cannot connect to "
                   "destination".format(test_num))
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        from_conn = "--source=joe@localhost:{0} ".format(self.server1.port)
        # Watch out for Windows: it doesn't use sockets!
        if os.name == "posix" and self.server2.socket is not None:
            to_conn = "--destination=joe@localhost:{0}:{1}".format(
                self.server2.port, self.server2.socket)
        else:
            to_conn = "--destination=joe@localhost:{0}".format(
                self.server2.port)
        cmd_str = "mysqldbcopy.py --skip-gtid {0} {1} ".format(from_conn,
                                                               to_conn)
        test_num += 1
        cmd_opts = "util_test:util_db_clone "
        comment = ("Test case {0} - users with minimal "
                   "privileges".format(test_num))
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        from_conn = "--source=sam@localhost:{0} ".format(self.server1.port)
        if os.name == "posix" and self.server2.socket is not None:
            to_conn = "--destination=joe@localhost:{0}:{1}".format(
                self.server2.port, self.server2.socket)
        else:
            to_conn = "--destination=joe@localhost:{0}".format(
                self.server2.port)
        cmd_str = "mysqldbcopy.py --skip-gtid {0} {1} ".format(from_conn,
                                                               to_conn)

        test_num += 1
        cmd_opts = "util_test:util_db_clone --force"
        comment = ("Test case {0} - source user not enough privileges "
                   "needed".format(test_num))
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        # Give Sam some privileges on source and retest until copy works
        self.server1.exec_query("GRANT SELECT ON util_test.* TO "
                                "'sam'@'localhost'")
        comment = ("Test case {0} - source user has some privileges "
                   "needed".format(test_num))
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        self.server1.exec_query("GRANT SELECT ON mysql.* TO 'sam'@'localhost'")
        comment = ("Test case {0} - source user has some privileges "
                   "needed".format(test_num))
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        self.server1.exec_query("GRANT SHOW VIEW, EVENT "
                                "ON util_test.* TO 'sam'@'localhost'")
        comment = ("Test case {0} - source user has privileges "
                   "needed".format(test_num))
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        # Watchout for Windows: it doesn't use sockets!
        if os.name == "posix":
            to_conn = "--destination=sam@localhost:{0}:{1}".format(
                self.server2.port, self.server2.socket)
        else:
            to_conn = "--destination=sam@localhost:{0}".format(
                self.server2.port)
        cmd_str = "mysqldbcopy.py --skip-gtid {0} {1} ".format(from_conn,
                                                               to_conn)
        cmd_opts = "util_test:util_db_clone --force "
        comment = ("Test case {0} - dest user not enough privileges "
                   "needed".format(test_num))
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        # Give Sam some privileges on source and retest until copy works
        self.server2.exec_query("GRANT ALL ON util_db_clone.* TO "
                                "'sam'@'localhost' WITH GRANT OPTION")
        comment = ("Test case {0} - dest user has some privileges "
                   "needed".format(test_num))
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        self.server2.exec_query("GRANT CREATE USER ON *.* TO "
                                "'sam'@'localhost'")
        comment = ("Test case {0} - dest user has some privileges "
                   "needed".format(test_num))
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        self.server2.exec_query("GRANT SUPER ON *.* TO 'sam'@'localhost'")
        comment = ("Test case {0} - dest user has privileges "
                   "needed".format(test_num))
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = ("mysqldbcopy.py --skip-gtid --source=rocks_rocks_rocks {0} "
                   "util_test:util_db_clone --force ".format(to_conn))
        comment = "Test case {0} - cannot parse --source".format(test_num)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = ("mysqldbcopy.py --skip-gtid {0} util_test:util_db_clone "
                   "--destination=rocks_rocks_rocks "
                   "--force ".format(from_conn))
        comment = "Test case {0} - cannot parse --destination".format(test_num)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = ("mysqldbcopy.py --skip-gtid --source=rocks_rocks_rocks "
                   "util_test:util_db_clone --force ")
        comment = "Test case {0} - no destination specified".format(test_num)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = "mysqldbcopy.py --skip-gtid {0} {1} ".format(to_conn,
                                                               from_conn)
        comment = "Test case {0} - no database specified".format(test_num)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = ("mysqldbcopy.py --skip-gtid {0} {1} util_test:util_db_clone"
                   " --force --new-storage-engine=NOTTHERE".format(to_conn,
                                                                   from_conn))
        comment = "Test case {0} - new storage engine missing".format(test_num)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = ("mysqldbcopy.py --skip-gtid {0} {1} util_test:util_db_clone"
                   " --force --default-storage-engine="
                   "NOPENOTHERE".format(to_conn, from_conn))
        comment = ("Test case {0} - default storage engine "
                   "missing".format(test_num))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = ("mysqldbcopy.py --skip-gtid {0} {1} util_test:util_db_clone"
                   " --force --all".format(to_conn, from_conn))
        comment = "Test case {0} - database listed and --all".format(test_num)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Check --rpl option errors        
        test_num += 1
        cmd_str = ("mysqldbcopy.py --skip-gtid {0} {1} "
                   "util_test ".format(to_conn, from_conn))
        comment = "Test case {0} - error: {1} but no --rpl".format(
            test_num, "--rpl-user=root")
        res = self.run_test_case(2, cmd_str + "--rpl-user=root", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        cmd_str = ("mysqldbcopy.py {0} {1} --all "
                   "--character-set=unsupported_charset"
                   "".format(from_conn, to_conn))
        comment = "Test case {0} - Invalid --character-set".format(test_num)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask socket for destination server
        self.replace_result("# Destination: root@localhost:",
                            "# Destination: root@localhost:[] ... connected\n")
        self.replace_result("# Destination: joe@localhost:",
                            "# Destination: joe@localhost:[] ... connected\n")
        self.replace_result("# Destination: sam@localhost:",
                            "# Destination: sam@localhost:[] ... connected\n")

        # Mask known source and destination host name.
        self.replace_substring("on localhost", "on XXXX-XXXX")
        self.replace_substring("on [::1]", "on XXXX-XXXX")

        # Replace error code.
        self.replace_result("Error 1045", "Error XXXX: Access denied\n")
        self.replace_result("Error 2003", "Error XXXX: Access denied\n")

        # Ignore GTID messages (skipping GTIDs in this test)
        self.remove_result("# WARNING: The server supports GTIDs")

        # Replace connection errors
        self.replace_result("mysqldbcopy: error: Source connection "
                            "values invalid",
                            "mysqldbcopy: error: Source connection "
                            "values invalid\n")
        self.replace_result("mysqldbcopy: error: Destination connection "
                            "values invalid",
                            "mysqldbcopy: error: Destination connection "
                            "values invalid\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_users(self):
        try:
            self.server1.exec_query("DROP USER 'joe'@'localhost'")
        except UtilError:
            pass
        try:
            self.server1.exec_query("DROP USER 'sam'@'localhost'")
        except UtilError:
            pass
        try:
            self.server2.exec_query("DROP USER 'joe'@'localhost'")
        except UtilError:
            pass
        try:
            self.server2.exec_query("DROP USER 'sam'@'localhost'")
        except UtilError:
            pass

    def cleanup(self):
        self.drop_users()
        res = copy_db.test.cleanup(self)
        return res
