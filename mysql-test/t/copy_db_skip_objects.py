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
    """check skip objects for copy/clone db
    This test executes a series of copy database operations on two 
    servers using a variety of skip oject parameters. It uses the
    copy_db test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return copy_db.test.check_prerequisites(self)

    def setup(self):
        return copy_db.test.setup(self)
        
    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"
       
        from_conn = "--source={0}".format(
            self.build_connection_string(self.server1)
        )
        to_conn = "--destination={0}".format(
            self.build_connection_string(self.server2)
        )

        cmd_str = ("mysqldbcopy.py --skip-gtid {0} {1} "
                   "util_test:util_db_clone".format(from_conn, to_conn))
        
        # In this test, we execute a series of commands saving the results
        # from each run to perform a comparative check.
        
        cmd_opts = "{0} --force --skip=grants".format(cmd_str)
        test_num = 1
        comment = "Test case {0} - no grants".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append(self.check_objects(self.server2, "util_db_clone"))

        test_num += 1
        cmd_opts = "{0},events".format(cmd_opts)
        comment = "Test case {0} - no events".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append(self.check_objects(self.server2, "util_db_clone"))

        test_num += 1
        cmd_opts = "{0},triggers".format(cmd_opts)
        comment = "Test case {0} - no triggers".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append(self.check_objects(self.server2, "util_db_clone"))

        test_num += 1
        cmd_opts = "{0},views".format(cmd_opts)
        comment = "Test case {0} - no views".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append(self.check_objects(self.server2, "util_db_clone"))

        test_num += 1
        cmd_opts = "{0},procedures".format(cmd_opts)
        comment = "Test case {0} - no procedures".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append(self.check_objects(self.server2, "util_db_clone"))

        test_num += 1
        cmd_opts = "{0},functions".format(cmd_opts)
        comment = "Test case {0} - no functions".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append(self.check_objects(self.server2, "util_db_clone"))

        test_num += 1
        cmd_opts = "{0},tables".format(cmd_opts)
        comment = "Test case {0} - no tables".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append(self.check_objects(self.server2, "util_db_clone"))
        
        # Create the database to test --skip=create-db
        query = "DROP DATABASE util_db_clone"
        try:
            res = self.server2.exec_query(query)
        except UtilError as err:
            raise MUTLibError(err.errmsg)

        query = "CREATE DATABASE util_db_clone"
        try:
            res = self.server2.exec_query(query)
        except UtilError as err:
            raise MUTLibError(err.errmsg)

        # Reset to check only the skip create
        test_num += 1
        cmd_opts = "{0} --skip=create_db".format(cmd_str)
        comment = "Test case {0} - skip create db".format(test_num)
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append(self.check_objects(self.server2, "util_db_clone"))

        query = "DROP DATABASE util_db_clone"
        try:
            res = self.server2.exec_query(query)
        except UtilError as err:
            raise MUTLibError(err.errmsg)
        
        test_num += 1
        # Show possible errors from skip misuse
        cmd_opts = "{0} --skip=tables".format(cmd_str)
        comment = ("Test case {0} - skip tables only"
                   " - will fail".format(test_num))
        res = self.run_test_case(1, cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Mask socket for destination server
        self.replace_result("# Destination: root@localhost:",
                            "# Destination: root@localhost:[] ... connected\n")
        self.replace_result("ERROR: Cannot operate on VIEW object. Error: "
                            "Query failed. 1146",
                            "ERROR: Cannot operate on VIEW object. Error: "
                            "Query failed. 1146: [...]\n")

        # Mask known source and destination host name.
        self.replace_result("# Source on ",
                            "# Source on XXXX-XXXX: ... connected.\n")
        self.replace_result("# Destination on ",
                            "# Destination on XXXX-XXXX: ... connected.\n")

        # Ignore GTID messages (skipping GTIDs in this test)
        self.remove_result("# WARNING: The server supports GTIDs")

        return True
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return copy_db.test.cleanup(self)
