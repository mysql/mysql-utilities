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
import compare_db
from mysql.utilities.exception import MUTLibError

class test(compare_db.test):
    """check errors for dbcompare
    This test executes a series of error conditions for the check database
    utility. It uses the compare_db test as a parent for setup and teardown
    methods.
    """

    def check_prerequisites(self):
        return compare_db.test.check_prerequisites(self)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        if self.need_server:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError, e:
                raise MUTLibError("Cannot spawn needed servers: " + e.errmsg)
        self.server2 = self.servers.get_server(1)
        self.drop_all()
        return True

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        s1_conn = "--server1=" + self.build_connection_string(self.server1)
        s2_conn = "--server2=" + self.build_connection_string(self.server2)

        test_num = 1
        cmd_str = "mysqldbcompare.py -t -vvv inventory:inventory "
        cmd_opts = "--server1=joeunk:@:dooer " + s2_conn
        comment = "Test case {0} - Invalid --server1 ".format(test_num)
        res = self.run_test_case(2, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = "--server2=joeunk:@:dooer " + s1_conn
        comment = "Test case {0} - Invalid --server2 ".format(test_num)
        res = self.run_test_case(2, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = "mysqldbcompare.py %s %s" % (s1_conn, s2_conn)
        cmd_opts = " inventory.inventory"
        comment = ("Test case {0} - missing backticks{1} "
                   "").format(test_num, cmd_opts)
        res = self.run_test_case(2, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        # Set input parameter with appropriate quotes for the OS
        if os.name == 'posix':
            cmd_opts = "'`inventory.inventory`'"
        else:
            cmd_opts = '"`inventory.inventory`"'
        cmd_str = "mysqldbcompare.py %s %s %s" % (s1_conn, s2_conn, cmd_opts)
        comment = ("Test case {0} - non existing database "
                   "'`inventory.inventory`'").format(test_num)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = "mysqldbcompare.py %s %s" % (s1_conn, s2_conn)
        cmd_opts = " :inventory"
        comment = ("Test case {0} - invalid format{1} "
                   "").format(test_num, cmd_opts)
        res = self.run_test_case(2, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = ("mysqldbcompare.py {0} {1} {2} "
                   "".format(s1_conn, s2_conn, "inventory:inventory -t"))
        cmd_opts = "--span-key-size=A"
        comment = ("Test case {0} - invalid value for {1} "
                   "").format(test_num, cmd_opts)
        res = self.run_test_case(2, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = ("mysqldbcompare.py {0} {1} {2} "
                   "".format(s1_conn, s2_conn, "inventory:inventory -t"))
        cmd_opts = "--span-key-size=-4"
        comment = ("Test case {0} - size too low for {1} "
                   "".format(test_num, cmd_opts))
        cmd = "{0}{1}".format(cmd_str, cmd_opts)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = "mysqldbcompare.py"
        comment = "Test case {0} - no options".format(test_num)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Add two tables without primary keys
        self.server1.exec_query("CREATE DATABASE inventory")
        self.server1.exec_query("CREATE TABLE inventory.box (a int) "
                                "ENGINE=INNODB")
        self.server1.exec_query("INSERT INTO inventory.box VALUES (1)")
        self.server2.exec_query("CREATE DATABASE inventory")
        self.server2.exec_query("CREATE TABLE inventory.box (a int) "
                                "ENGINE=INNODB")
        self.server2.exec_query("INSERT INTO inventory.box VALUES (2)")
        test_num += 1
        cmd_str = ("mysqldbcompare.py {0} {1} {2} "
                   "".format(s1_conn, s2_conn, "inventory:inventory -t"))
        comment = ("Test case {0} - No pri key".format(test_num, cmd_opts))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))


        self.replace_result("mysqldbcompare.py: error: Server1 connection "
                            "values invalid",
                            "mysqldbcompare.py: error: Server1 connection "
                            "values invalid\n")
        self.replace_result("mysqldbcompare.py: error: Server2 connection "
                            "values invalid",
                            "mysqldbcompare.py: error: Server2 connection "
                            "values invalid\n")

        self.replace_substring("on [::1]", "on localhost")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        try:
            self.server1.exec_query("DROP DATABASE inventory")
        except:
            pass
        try:
            self.server2.exec_query("DROP DATABASE inventory")
        except:
            pass
        return compare_db.test.cleanup(self)
