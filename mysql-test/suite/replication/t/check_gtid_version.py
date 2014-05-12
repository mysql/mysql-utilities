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
check_gtid_version test.
"""

import os

import mutlib

from mysql.utilities.exception import UtilError, MUTLibError


_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin --skip-slave-start '
                       '--log-slave-updates --gtid-mode=on '
                       '--disable-gtid-unsafe-statements '
                       '--sync-master-info=1 --master-info-repository=table"')


class test(mutlib.System_test):
    """check gtid version
    This test exercises the code to check gtid version compatibility.
    It requires a pre-5.6.9 GTID enabled server.
    """

    server0 = None
    server1 = None
    s1_serverid = None

    def check_prerequisites(self):
        # Check MySQL server version - Must be between 5.5.6 and 5.6.8
        low = self.servers.get_server(0).check_version_compat(5, 6, 5)
        high = self.servers.get_server(0).check_version_compat(5, 6, 9)
        if not low or high:
            raise MUTLibError("Test requires server version between "
                              "5.6.5 and 5.6.8 inclusive.")
        return self.check_num_servers(1)

    def setup(self):
        self.server0 = self.servers.get_server(0)
        self.server1 = None

        index = self.servers.find_server_by_name("with_gtids_old")
        if index:
            self.server1 = self.servers.get_server(index)
            try:
                res = self.server1.show_server_variable("server_id")
            except UtilError as err:
                raise MUTLibError("Cannot get gtid enabled server 1 "
                                  "server_id: {0}".format(err.errmsg))
            self.s1_serverid = int(res[0][1])
        else:
            self.s1_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(self.server0, self.s1_serverid,
                                                "with_gtids_old",
                                                _DEFAULT_MYSQL_OPTS)
            if not res:
                raise MUTLibError("Cannot spawn gtid enabled server.")
            self.server1 = res[0]
            self.servers.add_new_server(self.server1, True)
        self.drop_all()
        self.server1.exec_query("CREATE DATABASE gtid_version")
        self.server1.exec_query("CREATE TABLE gtid_version.t1 (a int)")
        self.server1.exec_query("INSERT INTO gtid_version.t1 VALUES (1)")

        return True

    def run(self):
        self.res_fname = "result.txt"

        export_cmd_str = ("mysqldbexport.py gtid_version --export=both "
                          "--skip=events,grants,procedures,functions,views "
                          "--format=SQL ")

        conn1 = "--server=" + self.build_connection_string(self.server1)

        test_num = 1
        comment = "Test case {0} attempt failed gtid version check".format(
            test_num)
        cmd_str = export_cmd_str + conn1
        res = mutlib.System_test.run_test_case(self, 1, cmd_str, comment)
        if not res:
            for row in self.results:
                print row,
            raise MUTLibError("{0}: failed".format(comment))

        self.mask_result("ERROR: The server",
                         "{0}".format(self.server1.port), "XXXXX")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        try:
            if self.res_fname:
                os.unlink(self.res_fname)
        except OSError:
            pass
        return self.drop_all()

    def drop_all(self):
        """Drops all databases created.
        """
        try:
            self.server1.exec_query("DROP DATABASE `gtid_version`")
        except UtilError:
            pass
        return True
