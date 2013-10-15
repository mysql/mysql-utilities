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

from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import UtilDBError
from mysql.utilities.exception import UtilError


class test(mutlib.System_test):
    """simple db copy
    This test executes copy database test cases among two servers.
    """

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        # Need at least one server.
        self.server1 = None
        self.server2 = None
        self.need_server = False
        if not self.check_num_servers(2):
            self.need_server = True
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        if self.need_server:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers: {0}"
                                  "".format(err.errmsg))
        self.server2 = self.servers.get_server(1)
        self.drop_all()
        data_file = os.path.normpath("./std_data/basic_data.sql")
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: {1}"
                              "".format(data_file, err.errmsg))

        # Create backtick database (with weird names)
        data_file_backticks = os.path.normpath("./std_data/backtick_data.sql")
        try:
            res = self.server1.read_and_exec_SQL(data_file_backticks, 
                                                 self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: {1}"
                              "".format(data_file_backticks, err.errmsg))

        # Create database with test VIEWS.
        data_file_views = os.path.normpath("./std_data/db_copy_views.sql")
        try:
            self.server1.read_and_exec_SQL(data_file_views, self.debug)
        except UtilError as err:
            raise MUTLibError(
                "Failed to read commands from file "
                "{0}: {1}".format(data_file_views, err.errmsg)
            )

        return True

    
    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server2)

        test_num = 1
        comment = ("Test case {0} - copy a sample database X:Y"
                   "").format(test_num)
        cmd = "mysqldbcopy.py --skip-gtid {0} {1} ".format(from_conn, to_conn)
        res = self.exec_util(cmd + " util_test:util_db_clone", self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - copy a sample database X".format(test_num)
        res = self.exec_util(cmd + " util_test", self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - copy using different engine"
                   "").format(test_num)
        cmd += " util_test:util_db_clone --force --new-storage-engine=MEMORY"
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - copy a sample database X:Y with weird "
                   "names (backticks)").format(test_num)
        # Set input parameter with appropriate quotes for the OS
        if os.name == 'posix':
            cmd_arg = "'`db``:db`:`db``:db_clone`'"
        else:
            cmd_arg = '"`db``:db`:`db``:db_clone`"'
        cmd = "mysqldbcopy.py {0} {1} {2}".format(from_conn, to_conn, cmd_arg)
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - copy a sample database X with weird "
                   "names (backticks)").format(test_num)
        # Set input parameter with appropriate quotes for the OS
        if os.name == 'posix':
            cmd_arg = "'`db``:db`'"
        else:
            cmd_arg = '"`db``:db`"'
        cmd = "mysqldbcopy.py {0} {1} {2}".format(from_conn, to_conn, cmd_arg)
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - copy a sample database with views"
                   "").format(test_num)
        cmd = "mysqldbcopy.py {0} {1} {2}".format(
            from_conn, to_conn, "views_test:views_test_clone"
        )
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        # These two DB and tables does not contains any row, and are used  
        # to test DB copy of default character set and collation.
        # was not move to ./std_data/basic_data.sql to avoid warning
        # "A partial copy from a server that has GTIDs.." messages
        # when setup is invoke from subclasses and other tests and
        # to avoid the creation of an additional file.
        queries = [("CREATE DATABASE util_test_default_collation "
                    "DEFAULT COLLATE utf8_general_ci"),
                   ("CREATE TABLE util_test_default_collation.t1 "
                    "(a char(30)) ENGINE=MEMORY"),
                   ("CREATE DATABASE util_test_default_charset "
                    "DEFAULT CHARACTER SET utf8"),
                   ("CREATE TABLE util_test_default_charset.t1 "
                    "(a char(30)) ENGINE=MEMORY")]
        for query in queries:
            self.server1.exec_query(query)

        test_num += 1
        dest_c = ("--destination={0}"
                  "").format(self.build_connection_string(self.server1))
        comment = "Test case {0} - copydb default collation".format(test_num)
        dbs = ("util_test_default_collation:"
               "util_test_default_collation_copy")
        cmd = ("mysqldbcopy.py --skip-gtid {0} {1} {2}"
               "").format(from_conn, dest_c, dbs)
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - copydb default charset".format(test_num)
        dbs = ("util_test_default_charset:"
               "util_test_default_charset_copy")
        cmd = ("mysqldbcopy.py --skip-gtid {0} {1} {2}"
               "").format(from_conn, dest_c, dbs)
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("{0}: failed".format(comment))

        return True
  
    def get_result(self):
        msg = []
        copied_db_on_server2 = ["util_db_clone", "util_test", "util_db_clone",
                                'db`:db_clone', 'db`:db', "views_test_clone"]
        copied_db_on_server1 = ["util_test_default_collation_copy",
                                "util_test_default_charset_copy"]

        query = "SHOW DATABASES LIKE '{0}'"
        for db in copied_db_on_server2:
            try:
                res = self.server2.exec_query(query.format(db))
                try:
                    if res[0][0] != db:
                        msg.append("Database {0} not found in {1}.\n"
                                   "".format(db, self.server2.role))
                except:
                    msg.append("Database {0} not found in {1}.\n"
                               "".format(db, self.server2.role))
            except UtilDBError as err:
                raise MUTLibError(err.errmsg)
        for db in copied_db_on_server1:
            try:
                res = self.server1.exec_query(query.format(db))
                try:
                    if res[0][0] != db:
                        msg.append("Database {0} not found in {1}.\n"
                                   "".format(db, self.server1.role))
                except:
                    msg.append("Database {0} not found in {1}.\n"
                               "".format(db, self.server1.role))
            except UtilDBError as err:
                raise MUTLibError(err.errmsg)

        qry_db = ("SELECT {0} FROM INFORMATION_SCHEMA.SCHEMATA "
                  "WHERE SCHEMA_NAME = '{1}'")
        qry_tb = ("SELECT CCSA.{0} "
                  "FROM information_schema.`TABLES` T, "
                  "information_schema.`COLLATION_CHARACTER_SET_APPLICABILITY`"
                  " CCSA WHERE CCSA.collation_name = T.table_collation "
                  " AND T.table_schema = '{1}' AND T.table_name = 't1'")
        check_db_info_on_server1 = [
            ("util_test_default_collation_copy",
             "DEFAULT_COLLATION_NAME",
             "utf8_general_ci", "COLLATION_NAME"),
            ("util_test_default_charset_copy",
             "DEFAULT_CHARACTER_SET_NAME",
             "utf8", "CHARACTER_SET_NAME")]
        for db in check_db_info_on_server1:
            try:
                res = self.server1.exec_query(qry_db.format(db[1], db[0]))
                try:
                    if res[0][0] != db[2]:
                        msg.append("For database {0} attribute {1} copy "
                                   "failed, got {2} expected {3}.\n"
                                   "".format(db[0], db[1], res[0][0], db[2]))
                except:
                    msg.append("For database {0} no value found for attribute "
                               "{1}.\n".format(db[0], db[1]))

                res = self.server1.exec_query(qry_tb.format(db[3], db[0]))
                try:
                    if res[0][0] != db[2]:
                        msg.append("For table {0} attribute {1} copy "
                                   "failed, got {2} expected {3}.\n"
                                   "".format(db[0], db[3], res[0][0], db[2]))
                except:
                    msg.append("For table {0} no value found for attribute "
                               "{1}.\n".format(db[0], db[3]))
            except UtilDBError as err:
                raise MUTLibError(err.errmsg)
        if msg:
            return (False, ("Result failure.\n", "\n".join(msg)))
        else:
            return (True, "")
    
    def record(self):
        # Not a comparative test, returning True
        return True

    def drop_all(self):
        # this DBs may not be created on subclasses.
        db_drops_on_server1 = ["util_test", 'db`:db', 'views_test',
                               "util_test_default_charset",
                               "util_test_default_collation",
                               "util_test_default_charset_copy",
                               "util_test_default_collation_copy"]
        for db in db_drops_on_server1:
            self.drop_db(self.server1, db)

        db_drops_on_server2 = ["util_test", 'db`:db', "util_db_clone",
                               'db`:db_clone', "views_test_clone"]
        for db in db_drops_on_server2:
            self.drop_db(self.server2, db)
        
        drop_user = ["DROP USER 'joe'@'user'", "DROP USER 'joe_wildcard'@'%'"]
        for drop in drop_user:
            try:
                self.server1.exec_query(drop)
                self.server2.exec_query(drop)
            except UtilError:
                pass
        return True
            
    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()


