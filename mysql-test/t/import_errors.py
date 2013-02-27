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
import import_basic
from mysql.utilities.exception import MUTLibError

class test(import_basic.test):
    """Import Data
    This test executes the import utility on a single server.
    It tests the error conditions for importing data.
    It uses the import_basic test for setup and teardown methods.
    """

    def check_prerequisites(self):
        return import_basic.test.check_prerequisites(self)

    def setup(self):
        return import_basic.test.setup(self)
    
    def run(self):
        self.res_fname = "result.txt"
        
        from_conn = "--server=%s" % self.build_connection_string(self.server1)
        to_conn = "--server=%s" % self.build_connection_string(self.server2)

        _FORMATS = ("CSV", "TAB", "GRID", "VERTICAL")
        test_num = 1
        for frmt in _FORMATS:
            comment = ("Test Case %d : Testing import with "
                       "%s format and NAMES display" % (test_num, frmt))
            # We test DEFINITIONS and DATA only in other tests
            self.run_import_test(1, from_conn, to_conn, 'util_test',
                                 frmt, "BOTH", comment, " --display=NAMES")
            self.drop_db(self.server2, "util_test")
            test_num += 1

        export_cmd = "mysqldbexport.py %s util_test --export=BOTH" % from_conn
        export_cmd += " --format=SQL --skip-gtid "
        export_cmd += " > %s" % self.export_import_file
        
        # First run the export to a file.
        res = self.run_test_case(0, export_cmd, "Running export...")
        if not res:
            raise MUTLibError("EXPORT: %s: failed" % comment)

        import_cmd = "mysqldbimport.py %s " % to_conn

        comment = "Test case %d - no file specified " % test_num
        cmd_str = import_cmd + " --import=BOTH --format=SQL"
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        import_cmd += "%s --import=BOTH --format=SQL" % self.export_import_file

        comment = "Test case %d - bad --skip values" % test_num
        cmd_str = import_cmd + " --skip=events,wiki-waki,woo-woo "
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1
                    
        comment = "Test case %d - exporting data and skipping data" % \
                  test_num
        cmd_str = import_cmd + " --skip=data --import=data"
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1
          
        cmd_str = "mysqldbimport.py --server=rocks_rocks_rocks "
        cmd_str += " %s " % self.export_import_file
        comment = "Test case %d - cannot parse --server" % test_num
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        cmd_str = "mysqldbimport.py %s " % self.export_import_file
        cmd_str += "--server=nope:nada@localhost:%s" % self.server0.port
        comment = "Test case %d - error: cannot connect to server" % test_num
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        res = self.server2.exec_query("CREATE USER 'joe'@'localhost'")

        # Watchout for Windows: it doesn't use sockets!
        if os.name == "posix":
            joe_conn = "--server=joe@localhost:%s" % self.server2.port
            if self.server2.socket is not None:
                joe_conn += ":%s" % self.server2.socket
        else:
            joe_conn = "--server=joe@localhost:%s " % self.server2.port

        cmd_str = "mysqldbimport.py %s %s " % (joe_conn, self.export_import_file)
        comment = "Test case %d - error: not enough privileges" % test_num
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        cmd_str = "mysqldbimport.py %s %s --import=definitions" % \
                  (joe_conn, self.export_import_file)
        comment = "Test case %d - error: not enough privileges" % test_num
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        bad_sql_file = os.path.normpath("./std_data/bad_sql.sql")

        cmd_str = "mysqldbimport.py %s %s --import=definitions" % \
                  (to_conn, bad_sql_file)
        comment = "Test case %d - error: bad SQL statements" % test_num
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        self.drop_db(self.server2, "util_test")

        # Skipping create and doing the drop should be illegal.
        cmd_str = import_cmd + " %s --skip=create_db " % \
                  self.export_import_file + \
                  "--format=sql --import=data --drop-first " 
        comment = "Test case %d - error: --skip=create_db & --drop-first" % \
                  test_num
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        self.drop_db(self.server2, "util_test")

        import_cmd = "mysqldbimport.py %s " % to_conn
        cmd_str = import_cmd + " %s --skip-blobs " % self.export_import_file + \
                  "--format=sql --import=definitions " 
        comment = "Test case %d - warning: --skip-blobs" % test_num
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        cmd_str = import_cmd + " %s --skip=data " % self.export_import_file + \
                  "--format=sql --import=data " 
        comment = "Test case %d - error: --skip=data & --import=data" % test_num
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        bad_csv_file = os.path.normpath("./std_data/bad_object.csv")

        cmd_str = import_cmd + " %s " % bad_csv_file + \
                  "--format=csv --import=both " 
        comment = "Test case %d - error: bad object definition" % test_num
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        test_num += 1

        # Test database with backticks
        _FORMATS_BACKTICKS = ("CSV", "TAB")
        for frmt in _FORMATS_BACKTICKS:
            comment = ("Test Case %d : Testing import with %s format and "
                       "NAMES display (using backticks)" % (test_num, frmt))
            self.run_import_test(1, from_conn, to_conn, '`db``:db`',
                                 frmt, "BOTH", comment, " --display=NAMES")
            self.drop_db(self.server2, '`db``:db`')
            test_num += 1

        if os.name != "posix":
            self.replace_result("# Importing definitions and data from "
                                "std_data\\bad_object.csv",
                                "# Importing definitions and data from "
                                "std_data/bad_object.csv.\n")
            self.replace_result("# Importing definitions from "
                                "std_data\\bad_sql.sql",
                                "# Importing definitions from "
                                "std_data/bad_sql.sql.\n")

        self.replace_substring(" (28000)", "")
        self.replace_result("ERROR: Query failed.", "ERROR: Query failed.\n")

        self.replace_substring("1045 (28000)", "1045")

        self.replace_result("mysqldbimport.py: error: Server connection "
                            "values invalid",
                            "mysqldbimport.py: error: Server connection "
                            "values invalid\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        try:
            self.server2.exec_query("DROP USER 'joe'@'localhost'")
        except:
            pass 
        return import_basic.test.drop_all(self)




