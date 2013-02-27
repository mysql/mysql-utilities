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

from mysql.utilities.common.table import quote_with_backticks

from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import UtilDBError
from mysql.utilities.exception import UtilError


class test(mutlib.System_test):
    """simple db clone
    This test executes a simple clone of a database on a single server.
    """

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        data_file = os.path.normpath("./std_data/basic_data.sql")
        self.drop_all()
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file %s: %s"
                              % (data_file, err.errmsg))

        # Create backtick database (with weird names)
        data_file_backticks = os.path.normpath("./std_data/backtick_data.sql")
        try:
            res = self.server1.read_and_exec_SQL(data_file_backticks,
                                                 self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file %s: %s"
                              % (data_file_backticks, err.errmsg))

        return True
    
    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"
        
        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server1)
       
        # Test case 1 - clone a sample database
        cmd = "mysqldbcopy.py --skip-gtid %s %s  util_test:util_db_clone " % \
              (from_conn, to_conn) 
        try:
            res = self.exec_util(cmd, self.res_fname)
            self.results.append(res)
            return res == 0
        except MUTLibError, e:
            raise MUTLibError(e.errmsg)

        # Test case 2 - clone a sample database with weird names (backticks)
        # Set input parameter with appropriate quotes for the OS
        if os.name == 'posix':
            cmd_arg = "'`db``:db`:`db``:db_clone`'"
        else:
            cmd_arg = '"`db``:db`:`db``:db_clone`"'
        cmd = ("mysqldbcopy.py --skip-gtid %s %s %s' "
               % (from_conn, to_conn, cmd_arg))
        try:
            res = self.exec_util(cmd, self.res_fname)
            self.results.append(res)
            return res == 0
        except MUTLibError, e:
            raise MUTLibError(e.errmsg)

    def get_result(self):
        if self.server1 and self.results[0] == 0:
            query = "SHOW DATABASES LIKE 'util_db_clone'"
            try:
                res = self.server1.exec_query(query)
                if res and res[0][0] == 'util_db_clone':
                    return (True, None)
            except UtilDBError as err:
                raise MUTLibError(err.errmsg)
            query = "SHOW DATABASES LIKE 'db`:db_clone'"
            try:
                res = self.server1.exec_query(query)
                if res and res[0][0] == 'db`:db_clone':
                    return (True, None)
            except UtilDBError as err:
                raise MUTLibError(err.errmsg)
        return (False, ("Result failure.\n", "Database clone not found.\n"))
    
    def record(self):
        # Not a comparative test, returning True
        return True
    
    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        try:
            res = server.exec_query("SHOW DATABASES LIKE '%s'" % db)
        except:
            return True # Ok to exit here as there weren't any dbs to drop
        try:
            q_db = quote_with_backticks(db)
            res = server.exec_query("DROP DATABASE %s" % q_db)
        except:
            return False
        return True
    
    def drop_all(self):
        res = True
        try:
            self.drop_db(self.server1, "util_test")
        except:
            res = res and False
        try:
            self.drop_db(self.server1, 'db`:db')
        except:
            res = res and False
        try:
            self.drop_db(self.server1, "util_db_clone")
        except:
            res = res and False
        try:
            self.drop_db(self.server1, "db`:db_clone")
        except:
            res = res and False
        try:
            self.server1.exec_query("DROP USER 'joe'@'user'")
        except:
            pass
        return res

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()




