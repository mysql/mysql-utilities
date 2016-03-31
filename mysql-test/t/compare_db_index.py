#
# Copyright (c) 2016, Oracle and/or its affiliates. All rights reserved.
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
compare_db_index test.
"""

import os

import compare_db

from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import UtilError
from mysql.utilities.common.database import UtilDBError


_ALTER_COL_DEF = "ALTER TABLE {db}.{tb} MODIFY {col} {new_def}"


class test(compare_db.test):
    """Large db diff
    This test executes a consistency check of two databases on
    separate servers and uses the db_compare_index_definition.sql.

    Tests BUG#21572065 and BUG#21803368. Where comparing two tables with
    diferent definitions of the used indexes (i.e defining in table1 'id' of
    type SMALLINT while on table2 is TINYINT) can produce wrong data to be
    stored in the comparation table, this because mysqldbcompare was using
    only the table definition from the first table to construct the comparation
    tables for the two tables, which can change the indexes values due to the
    lost of precision (or truncated bits) corvering the data to a diferent
    type.
    """

    server1 = None
    server2 = None
    db_test_name = None
    setup_temp_file = None

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        # Need at least one server.
        self.need_server = False
        if not self.check_num_servers(2):
            self.need_server = True
        if self.servers.get_server(0).check_version_compat(5, 7, 0):
            raise MUTLibError("Test requires server version prior to 5.7.0")
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        if self.need_server:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers: {0}".format(
                    err.errmsg))
        self.server2 = self.servers.get_server(1)

        # set the db test name
        self.db_test_name = "index_def"
        self.drop_all()

        data_file = os.path.normpath("./std_data/db_compare_index_defs.sql")

        try:
            for server in [self.server1, self.server2]:
                server.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file"
                              " {0}: {1} to server {2}"
                              "".format(data_file, err.errmsg, server.port))

        return True

    def run(self):
        self.res_fname = "result.txt"
        s_conn = self.build_connection_string(self.server1)
        s1_conn = "--server1={0}".format(s_conn)
        s_conn = self.build_connection_string(self.server2)
        s2_conn = "--server2={0}".format(s_conn)

        cmd_str = ("mysqldbcompare.py {s1} {s2} {params}"
                   "".format(s1=s1_conn, s2=s2_conn, params="{params}"))

        test_case = 1
        comment = ("Test case {0} - check database with No differences"
                   "".format(test_case))

        parameters = ("{0}:{1} -t --changes-for=server1 --difftype=unified "
                      "--format=grid --skip-table-options "
                      "--disable-binary-logging"
                      "".format(self.db_test_name, self.db_test_name))
        res = self.run_test_case(0, cmd_str.format(params=parameters), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_case += 1
        # Alter the table definition on server 2
        # This produces to some rows not being found in the compare tables
        # in the server if the origal definition was not used, due to the
        # values of the indexes are comprimissed by the lost of precision in
        # the column definition.
        db = "index_def"
        tb = "deduction"
        col = "company"
        new_def = "tinyint unsigned"
        try:
            self.server2.exec_query(_ALTER_COL_DEF.format(db=db, tb=tb,
                                                          col=col,
                                                          new_def=new_def))
        except UtilDBError as err:
            raise MUTLibError("Failed to execute query: {0}"
                              "".format(err.errmsg))

        comment = ("Test case {0} - check databases with index precision lost"
                   " and No other differences".format(test_case))
        res = self.run_test_case(1, cmd_str.format(params=parameters), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_case += 1
        # Alter some values (not primary keys) on server 2
        try:
            # Rows modified
            self.server2.exec_query("UPDATE {0}.{1} SET percent=0.85 "
                                    "WHERE company > 50 and company < 100"
                                    "".format(self.db_test_name, tb))

        except UtilError as err:
            raise MUTLibError("Failed to execute query: {0}"
                              "".format(err.errmsg))

        comment = ("Test case {0} - check databases with index precision lost "
                   "and known differences in No pk values".format(test_case))
        res = self.run_test_case(1, cmd_str.format(params=parameters), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_case += 1
        # Insert new values on server 1, incompatible with the previewsly
        # modified column defenition
        try:
            count_rows_qry = ("SELECT COUNT(*) FROM {0}.{1}"
                              "".format(self.db_test_name, tb))
            count_before = self.server2.exec_query(count_rows_qry)

            # Rows modified
            self.server1.exec_query("INSERT INTO {0}.{1} VALUES"
                                    "(512,1,'deducccion 0%',0),"
                                    "(1024,2,'deduction 25%',0.75)"
                                    "".format(self.db_test_name, tb))

            count_after = self.server2.exec_query(count_rows_qry)

            if self.debug:
                print("{0}.{1} rows had been increased from {2} to {3}"
                      "".format(self.db_test_name, table, count_before[0][0],
                                count_after[0][0]))

        except UtilError as err:
            raise MUTLibError("Failed to execute query: {0}"
                              "".format(err.errmsg))

        comment = ("Test case {0} - check databases with index precision lost "
                   "and new inserts".format(test_case))
        res = self.run_test_case(1, cmd_str.format(params=parameters), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.do_replacements()

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def do_replacements(self):
        compare_db.test.do_replacements(self)
        prefixes = ['***', '---', '+++']
        names = ['deduction']
        for prefix in prefixes:
            for name in names:
                self.replace_result("{0} {2}.{1}".format(prefix, name,
                                                         self.db_test_name),
                                    "{0} {2}.{1}\n".format(prefix, name,
                                                           self.db_test_name))

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_all(self):
        """Drops all databases created.
        """
        for server in [self.server1, self.server2]:
            if server is not None:
                self.drop_db(server, self.db_test_name)
        return True

    def cleanup(self):
        self.drop_all()
        try:
            if self.res_fname:
                os.unlink(self.res_fname)
        except OSError:
            pass
        return self.kill_server(self.server2.role)
