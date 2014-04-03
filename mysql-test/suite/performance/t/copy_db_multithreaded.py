#
# Copyright (c) 2010, 2014, Oracle and/or its affiliates. All rights reserved.
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
copy_db_multithreaded test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError


class test(mutlib.System_test):
    """simple db copy
    This test executes copy database test cases among two servers using
    multiple threads.
    """

    server1 = None
    server2 = None
    need_server = None

    # pylint: disable=W0221
    def is_long(self):
        # This test is a long running test
        return True

    def check_prerequisites(self):
        # Need non-Windows platform
        if os.name == "nt":
            raise MUTLibError("Test requires a non-Windows platform.")
        # Need at least one server.
        self.server1 = self.servers.get_server(0)
        self.server2 = None
        self.need_server = False
        if not self.check_num_servers(2):
            self.need_server = True
        res = self.check_num_servers(1)
        rows = []
        try:
            rows = self.server1.exec_query("SHOW DATABASES LIKE 'employees'")
        except:
            pass
        if len(rows) == 0:
            raise MUTLibError("Need employees database loaded on "
                              "{0}".format(self.server1.role))
        return res

    def setup(self):
        if self.need_server:
            self.servers.spawn_new_servers(2)
        self.server2 = self.servers.get_server(1)
        self.drop_all()
        return True

    def run(self):
        self.res_fname = "result.txt"

        from_conn = ("--source={0}"
                     "".format(self.build_connection_string(self.server1)))
        to_conn = ("--destination={0}"
                   "".format(self.build_connection_string(self.server2)))

        comment = "Test case 1 - copy a sample database"
        cmd = ("mysqldbcopy.py {0} {1} {2}"
               "".format(from_conn, to_conn,
                         "employees:emp_mt --force --threads=3"))
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_all(self):
        """Drops all databases created.
        """
        return self.drop_db(self.server2, "emp_mt")

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()
