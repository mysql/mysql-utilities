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

import mutlib

from mysql.utilities.exception import MUTLibError, UtilError

_ENGINE_QUERY = """
    SELECT ENGINE FROM INFORMATION_SCHEMA.TABLES
    WHERE table_schema = 'util_test' and table_name = '{0}'
"""

_TABLES = ('t1', 't2', 't3', 't4', 't5', 't6', 't7', 't8', 't9', 't10')


class test(mutlib.System_test):
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
        num_servers = self.servers.num_servers()
        if self.need_servers:
            try:
                self.servers.spawn_new_servers(num_servers)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers: "
                                  "{0}".format(err.errmsg))

        self.server0 = self.servers.get_server(0)

        index = self.servers.find_server_by_name("import_basic")
        if index >= 0:
            self.server1 = self.servers.get_server(index)
            try:
                res = self.server1.show_server_variable("server_id")
            except MUTLibError as err:
                raise MUTLibError("Cannot get import_basic server server_id: "
                                  "{0}".format(err.errmsg))
            self.s1_serverid = int(res[0][1])
        else:
            self.s1_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(self.server0, self.s1_serverid,
                                                "import_basic",
                                                '"--sql_mode="')
            if not res:
                raise MUTLibError("Cannot spawn import_basic server.")
            self.server1 = res[0]
            self.servers.add_new_server(self.server1, True)
        try:
            self.server1.exec_query("SET GLOBAL default_storage_engine=MEMORY")
        except UtilError:
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
                res = self.server1.exec_query(_ENGINE_QUERY.format(table_name))
                if not res:
                    self.results.append("util_test.{1}: ENGINE NOT FOUND!\n")
                else:
                    self.results.append(
                        "util_test.{0}: ENGINE={1}\n".format(table_name,
                                                             res[0][0]))

        self.res_fname = "result.txt"

        to_conn = "--server={0}".format(
            self.build_connection_string(self.server1))

        import_file = os.path.normpath("./std_data/bad_engine.csv")
        test_num = 1

        cmd_str = ("mysqldbimport.py {0} {1} --import=both "
                   "--format=CSV ".format(to_conn, import_file))
        comment = "Test case {0} - Normal run".format(test_num)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        _get_engines()

        cmd_str = ("mysqldbimport.py {0} {1} --import=definitions "
                   "--new-storage-engine=MEMORY --drop-first "
                   "--format=CSV".format(to_conn, import_file))
        comment = "Test case {0} - convert to memory storage engine".format(
            test_num)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        _get_engines()

        cmd_str = ("mysqldbimport.py {0} {1} --import=definitions "
                   "--new-storage-engine=NOTTHERE --drop-first "
                   "--format=CSV".format(to_conn, import_file))
        comment = "Test case {0} - new storage engine missing".format(test_num)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        _get_engines()

        cmd_str = ("mysqldbimport.py {0} {1} --import=definitions "
                   "--default-storage-engine=NOPENOTHERE --drop-first "
                   "--format=CSV".format(to_conn, import_file))
        comment = "Test case {0} - default storage engine missing".format(
            test_num)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        _get_engines()

        cmd_str = ("mysqldbimport.py {0} {1} --import=definitions "
                   "--new-storage-engine=NOTTHERE --drop-first --format=CSV "
                   "--default-storage-engine=INNODB ".format(to_conn,
                                                             import_file))
        comment = ("Test case {0} - new storage engine missing, "
                   "default Ok".format(test_num))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        _get_engines()

        cmd_str = ("mysqldbimport.py {0} {1} --import=definitions "
                   "--default-storage-engine=NOPENOTHERE --drop-first "
                   "--format=CSV "
                   "--new-storage-engine=MYISAM".format(to_conn, import_file))

        comment = ("Test case {0} - default storage engine missing, "
                   "new Ok".format(test_num))
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        _get_engines()

        self.replace_result("# Importing", "# Importing ... bad_engines.csv\n")

        # Mask known source and destination host name.
        self.replace_substring("on localhost", "on XXXX-XXXX")
        self.replace_substring("on [::1]", "on XXXX-XXXX")

        return True

    def drop_all(self):
        # OK if drop_db fails - they are spawned servers.
        self.drop_db(self.server1, "util_test")
        self.drop_db(self.server1, 'db`:db')
        self.drop_db(self.server1, "import_test")

        drop_user = ["DROP USER 'joe'@'user'", "DROP USER 'joe_wildcard'@'%'"]
        for drop in drop_user:
            try:
                self.server1.exec_query(drop)
            except UtilError:
                pass
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Remove result file.
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except OSError:
                pass  # Ignore error because file may not exist.
            # Drop all imported database data.
        return self.drop_all()
