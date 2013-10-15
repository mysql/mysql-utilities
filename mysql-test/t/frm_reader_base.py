#
# Copyright (c) 2013, Oracle and/or its affiliates. All rights reserved.
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
import difflib
import os
import mutlib

from mysql.utilities.exception import MUTLibError


class test(mutlib.System_test):
    """.frm file reader
    This test executes test cases to test the .frm reader.
    """

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 11):
            raise MUTLibError("Test requires server version 5.6.11 and later.")
        self.server0 = None
        self.server1 = None
        return self.check_num_servers(1)

    def setup(self):
        self.server0 = self.servers.get_server(0)
        self.frm_output = "frm_output.txt"
        self.s1_serverid = None

        index = self.servers.find_server_by_name("frm_test")
        if index >= 0:
            self.server1 = self.servers.get_server(index)
            try:
                res = self.server1.show_server_variable("server_id")
            except MUTLibError as err:
                raise MUTLibError("Cannot get frm test server " +
                                   "server_id: %s" % err.errmsg)
            self.s1_serverid = int(res[0][1])
        else:
            self.s1_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(self.server0, self.s1_serverid,
                                               "frm_test", ' --mysqld='
                                                '"--log-bin=mysql-bin "')
            if not res:
                raise MUTLibError("Cannot spawn frm_test server.")
            self.server1 = res[0]
            self.servers.add_new_server(self.server1, True)

        self.drop_all()

        self.server1.exec_query("CREATE DATABASE frm_test")
        basedir = self.server1.show_server_variable("basedir")[0][1]

        # Load a known CREATE TABLE|VIEW statement from file
        data_file = os.path.normpath("./std_data/frm_test.sql")
        sql_statements = []
        try:
            file = open(data_file, 'r')
            queries = " ".join([a.strip("\n") for a in file.readlines()])
            sql_statements = queries.split(";")
            for table_sql in sql_statements:
                res = self.server1.exec_query(table_sql)
            file.close()
        except MUTLibError as err:
            raise MUTLibError("Failed to read commands from file %s: " % \
                               data_file + err.errmsg)

        return True

    def check_frm_read(self, tablename, frm_file, comment, exp_result=0):

        if self.debug:
            print comment
            print "Running test for %s" % tablename

        self.results.append(comment)
        try:
            res = self.exec_util(self.cmd + frm_file, self.res_fname)
            self.results.append(res)
        except MUTLibError as err:
            raise MUTLibError(err.errmsg)
        if not res == exp_result:
            raise MUTLibError("%s: failed" % comment)

        if self.debug:
            for row in open(self.res_fname, 'r').readlines():
                print row

        # Get the create statement
        create_table = self.server1.exec_query("SHOW CREATE TABLE frm_test.%s" % \
                                               tablename)[0][1]
        # Add the database
        create_table = create_table.replace("`%s`" % tablename,
                                            "`frm_test`.`%s`" % tablename, 1)
        # Add the ending ;
        create_table = create_table.strip()
        create_stmt = [a.strip() for a in create_table.split('\n')]

        # Do a diff on the output versus
        diff_str = []
        file1 = open(self.frm_output)
        lines = []
        # But first, fix the output file.
        for line in file1.readlines():
            # Skip comments or blank lines
            if line[0] == '#' or len(line.strip()) == 0:
                continue
            lines.append(line.strip())

        # Generate unified is SQL is specified for use in reporting errors
        for line in difflib.unified_diff(create_stmt, lines):
            diff_str.append(line.strip('\n').rstrip(' '))
        if diff_str:
            for row in diff_str:
                print row
        file1.close()

        os.unlink(self.frm_output)

        return len(diff_str) == 0

    def run(self):
        self.res_fname = "result.txt"

        if self.debug:
            print
        test_num = 1
        res = self.server1.exec_query("SHOW TABLES FROM frm_test")
        tables = [a[0] for a in res]
        tables.sort() # make predictable order

        port = self.servers.get_next_port()
        self.cmd = "mysqlfrm.py --server=%s --port=%s " % \
                   (self.build_connection_string(self.server1), port)

        # Perform tests of specific .frm files
        for tablename in tables:
        # Read the .frm File from the server
            datadir = self.server1.show_server_variable("datadir")[0][1]
            frm_file = os.path.normpath("%s/frm_test/%s.frm > %s" % \
                                        (datadir, tablename, self.frm_output))
            comment = "Test case %s: - Check complex types " % test_num + \
                      "and default values for table: %s" % tablename
            self.check_frm_read(tablename, frm_file, comment)
            test_num += 1

        return True

    def get_result(self):
        msg = None
        stop = len(self.results)
        i = 0
        while i < stop:
            comment = self.results[i]
            result = self.results[i+1]
            if result:
                return (False, "%s\nFAILED: differences found!")
            i += 2

        return (True, '')

    def record(self):
        # Not a comparative test, returning True
        return True

    def drop_all(self):
        return self.drop_db(self.server1, "frm_test")

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()
