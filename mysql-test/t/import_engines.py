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

_ENGINE_QUERY = """
    SELECT ENGINE FROM INFORMATION_SCHEMA.TABLES
    WHERE table_schema = 'util_test' and table_name = '%s'
"""

_TABLES = ('t1', 't2', 't3', 't4', 't5', 't6', 't7', 't8', 't9', 't10')

class test(import_basic.test):
    """check storage engine options for import utility
    This test executes a test for engine parameters for mysqldbimport.
    It uses the import_basic test as a parent for teardown methods.
    """

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        self.server0 = self.servers.get_server(0)
        sql_mode = self.server0.show_server_variable("SQL_MODE")[0]
        if "NO_ENGINE_SUBSTITUTION" in sql_mode[1]:
            raise MUTLibError("Test requires servers that do not have "
                              "sql_mode = 'NO_ENGINE_SUBSTITUTION'.")
        # Need at least one server.
        self.server1 = None
        self.need_servers = False
        if not self.check_num_servers(2):
            self.need_servers = True
        return self.check_num_servers(1)

    def setup(self):
        self.export_import_file = "test_run.txt"
        num_servers = self.servers.num_servers()
        if self.need_servers:
            try:
                self.servers.spawn_new_servers(num_servers)
            except MUTLibError, e:
                raise MUTLibError("Cannot spawn needed servers: %s" % \
                                   e.errmsg)
        else:
            num_servers -= 1 # Get last server in list
        self.server0 = self.servers.get_server(0)

        index = self.servers.find_server_by_name("import_basic")
        if index >= 0:
            self.server1 = self.servers.get_server(index)
            try:
                res = self.server1.show_server_variable("server_id")
            except MUTLibError, e:
                raise MUTLibError("Cannot get import_basic server " +
                                   "server_id: %s" % e.errmsg)
            self.s1_serverid = int(res[0][1])
        else:
            self.s1_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(self.server0, self.s1_serverid,
                                               "import_basic")
            if not res:
                raise MUTLibError("Cannot spawn import_basic server.")
            self.server1 = res[0]
            self.servers.add_new_server(self.server1, True)
        try:
            self.server1.exec_query("SET GLOBAL default_storage_engine=MEMORY")
        except:
            self.server1.exec_query("SET GLOBAL storage_engine=MEMORY")
            
        return True

    def run(self):
        
        # Get the engines for the tables and save them for compare
        #
        # Note: This may show different result file if run on a server whose
        # default storage engine is set differently than version 5.1.
        #
        def _get_engines():
            for table_name in _TABLES:
                res = self.server1.exec_query(_ENGINE_QUERY % table_name)
                if res == []:
                    self.results.append("util_test.%s: ENGINE NOT FOUND!\n")
                else:
                    self.results.append("util_test.%s: ENGINE=%s\n" %
                                        (table_name, res[0][0]))

        self.res_fname = "result.txt"
        import_basic.test.drop_all(self)
        
        to_conn = "--server=" + self.build_connection_string(self.server1)
        
        import_file = os.path.normpath("./std_data/bad_engine.csv")
        case_num = 1
        
        cmd_str = "mysqldbimport.py %s %s --import=both --format=CSV " % \
                  (to_conn, import_file)
        comment = "Test case %d - Normal run" % case_num
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        case_num += 1
        
        _get_engines()
        
        cmd_str = "mysqldbimport.py %s %s --import=definitions " % \
                  (to_conn, import_file)
        cmd_str += "--new-storage-engine=MEMORY --drop-first --format=CSV"
        comment = "Test case %d - convert to memory storage engine" % case_num
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        case_num += 1

        _get_engines()

        cmd_str = "mysqldbimport.py %s %s --import=definitions " % \
                  (to_conn, import_file)
        cmd_str += "--new-storage-engine=NOTTHERE --drop-first --format=CSV"
        comment = "Test case %d - new storage engine missing" % case_num
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        case_num += 1

        _get_engines()

        cmd_str = "mysqldbimport.py %s %s --import=definitions " % \
                  (to_conn, import_file)
        cmd_str += "--default-storage-engine=NOPENOTHERE --drop-first" + \
                   " --format=CSV"
        comment = "Test case %d - default storage engine missing" % case_num
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        case_num += 1

        _get_engines()

        cmd_str = "mysqldbimport.py %s %s --import=definitions  " % \
                  (to_conn, import_file)
        cmd_str += "--new-storage-engine=NOTTHERE --drop-first --format=CSV "
        cmd_str += "--default-storage-engine=INNODB "
        comment = "Test case %d - new storage engine missing, default Ok" % \
                  case_num
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        case_num += 1

        _get_engines()

        cmd_str = "mysqldbimport.py %s %s --import=definitions " % \
                  (to_conn, import_file)
        cmd_str += "--default-storage-engine=NOPENOTHERE --drop-first" + \
                   " --format=CSV "
        cmd_str += "--new-storage-engine=MYISAM"
        comment = "Test case %d - default storage engine missing, new Ok" % \
                  case_num
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        case_num += 1

        _get_engines()

        self.replace_result("# Importing", "# Importing ... bad_engines.csv\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return import_basic.test.cleanup(self)
