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
diff_sql_databases test.
"""

import test_sql_template

from mysql.utilities.exception import MUTLibError


# (comment, def1, def2, expected result)
_DATABASE_TESTS = [
    ("Database definition charset", "ALTER DATABASE diff_db charset=latin2;",
     "ALTER DATABASE diff_db charset=latin1;", 0),
    ("Database definition collation",
     "ALTER DATABASE diff_db collate=latin1_swedish_ci;",
     "ALTER DATABASE diff_db collate=latin2_general_ci;", 0),
    ("Database definition charset and collation",
     "ALTER DATABASE diff_db charset=latin1 collate=latin1_swedish_ci;",
     "ALTER DATABASE diff_db charset=latin2 collate=latin2_general_ci;", 0),
]

_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --skip-slave-start '
                       '--log-slave-updates --gtid-mode=on '
                       '--enforce-gtid-consistency --report-host=localhost'
                       '--report-port={0} --bind-address=:: '
                       '--master-info-repository=table '
                       '--sql-mode=ANSI_QUOTES"')


class test(test_sql_template.test):
    """test mysqldiff --difftype=sql generation for databases

    This test uses the test_sql_template for testing databases.
    """

    utility = None
    server1 = None

    def check_prerequisites(self):
        self.server0 = self.servers.get_server(0)
        if not self.server0.check_version_compat(5, 6, 5):
            raise MUTLibError("Test requires server version 5.6.5 and later.")
        return test_sql_template.test.check_prerequisites(self)

    def setup(self):
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server1 = self.servers.spawn_server("diff_sql_srv1_ansi_quotes",
                                                 mysqld, True)
        mysqld = _DEFAULT_MYSQL_OPTS.format(self.servers.view_next_port())
        self.server2 = self.servers.spawn_server("diff_sql_srv2_ansi_quotes",
                                                 mysqld, True)

        test_object = {'db1': 'diff_db', 'db2': 'diff_db', 'object_name': '',
                       'startup_cmds': [], 'shutdown_cmds': [], }
        for database in _DATABASE_TESTS:
            new_test_obj = test_object.copy()
            new_test_obj['comment'] = database[0]
            new_test_obj['server1_object'] = database[1]
            new_test_obj['server2_object'] = database[2]
            new_test_obj['expected_result'] = database[3]
            self.test_objects.append(new_test_obj)

        self.utility = 'mysqldiff.py'

        return test_sql_template.test.setup(self, spawn_servers=False)

    def run(self):
        return test_sql_template.test.run(self)

    def get_result(self):
        return test_sql_template.test.get_result(self)

    def record(self):
        return True  # Not a comparative test

    def cleanup(self):
        if not self.server1:
            return True   # Nothing to do
        # Kill the servers that are only for this test.
        kill_list = ["diff_sql_srv1_ansi_quotes",
                     "diff_sql_srv2_ansi_quotes"]
        return (test_sql_template.test.cleanup(self) and
                self.kill_server_list(kill_list))
