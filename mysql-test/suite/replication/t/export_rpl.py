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
export_rpl test.
"""

import os

import mutlib
import replicate

from mysql.utilities.exception import MUTLibError, UtilError


_RPL_MODES = ["master", "slave", "both"]
_LOCKTYPES = ['no-locks', 'lock-all', 'snapshot']


class test(replicate.test):
    """check --rpl parameter for export utility
    This test executes a series of export database operations on a single
    server using a variety of --rpl and --locking options. It uses the
    replicate test as a parent for setup and teardown methods.
    """

    server3 = None
    s3_serverid = None

    def check_prerequisites(self):
        # Check MySQL server version - Must be 5.1.0 or higher
        if not self.servers.get_server(0).check_version_compat(5, 1, 0):
            raise MUTLibError("Test requires server version 5.1.0 or higher")
        self.check_gtid_unsafe()
        return replicate.test.check_prerequisites(self)

    def setup(self):
        self.res_fname = "result.txt"
        self.server3 = None

        result = replicate.test.setup(self)

        index = self.servers.find_server_by_name("rep_relay_slave")
        if index >= 0:
            self.server3 = self.servers.get_server(index)
            try:
                res = self.server3.show_server_variable("server_id")
            except MUTLibError as err:
                raise MUTLibError("Cannot get relay slave "
                                  "server_id: {0}".format(err.errmsg))
            self.s3_serverid = int(res[0][1])
        else:
            self.s3_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(
                self.server0, self.s3_serverid, "rep_relay_slave",
                ' --mysqld="--log-bin=mysql-bin "')
            if not res:
                raise MUTLibError("Cannot spawn replication slave server.")
            self.server3 = res[0]
            self.servers.add_new_server(self.server3, True)

        master_str = "--master={0}".format(
            self.build_connection_string(self.server1))
        slave_str = " --slave={0}".format(
            self.build_connection_string(self.server2))
        conn_str = master_str + slave_str
        self.server1.exec_query("STOP SLAVE")
        self.server1.exec_query("RESET SLAVE")
        self.server2.exec_query("STOP SLAVE")
        self.server2.exec_query("RESET SLAVE")
        self.server3.exec_query("STOP SLAVE")
        self.server3.exec_query("RESET SLAVE")

        self.drop_all()
        data_file = os.path.normpath("./std_data/basic_data.sql")
        try:
            self.server1.exec_query("DROP DATABASE IF EXISTS util_test")
            self.server1.read_and_exec_SQL(data_file, self.debug)
            self.server2.exec_query("DROP DATABASE IF EXISTS util_test")
            self.server2.read_and_exec_SQL(data_file, self.debug)
            self.server3.exec_query("DROP DATABASE IF EXISTS util_test")
            self.server3.read_and_exec_SQL(data_file, self.debug)
        except MUTLibError as err:
            raise MUTLibError("Failed to read commands from file {0}: "
                              "{1}".format(data_file, err.errmsg))

        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl {0}".format(conn_str)
        try:
            self.exec_util(cmd, self.res_fname)
        except MUTLibError:
            raise

        master_str = " --master={0}".format(
            self.build_connection_string(self.server2))
        slave_str = " --slave={0}".format(
            self.build_connection_string(self.server3))
        conn_str = master_str + slave_str
        self.server3.exec_query("STOP SLAVE")
        self.server3.exec_query("RESET SLAVE")

        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl {0}".format(conn_str)
        try:
            self.exec_util(cmd, self.res_fname)
        except MUTLibError:
            raise

        return result

    def run(self):
        master_conn = "--server={0}".format(
            self.build_connection_string(self.server1))
        relay_conn = "--server={0}".format(
            self.build_connection_string(self.server2))
        slave_conn = "--server={0}".format(
            self.build_connection_string(self.server3))

        cmd_str = ("mysqldbexport.py util_test --export=both "
                   "--skip=events,grants,procedures,functions,views "
                   "--rpl-user=rpl:rpl ")

        test_num = 1
        for rpl_mode in _RPL_MODES:
            for locktype in _LOCKTYPES:
                comment = ("Test case {0} - rpl = {1} and lock_type = "
                           "{2}".format(test_num, rpl_mode, locktype))
                if rpl_mode == "master":
                    cmd_opts = master_conn
                elif rpl_mode == "slave":
                    cmd_opts = slave_conn
                else:
                    cmd_opts = relay_conn
                cmd_opts = "{0} --rpl={1} --locking={2}".format(
                    cmd_opts, rpl_mode, locktype)
                res = mutlib.System_test.run_test_case(self, 0,
                                                       cmd_str + cmd_opts,
                                                       comment)
                if not res:
                    raise MUTLibError("{0}: failed".format(comment))
                test_num += 1

        self.replace_result("CHANGE MASTER", "CHANGE MASTER <goes here>\n")
        self.replace_result("# CHANGE MASTER", "# CHANGE MASTER <goes here>\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return replicate.test.cleanup(self)

    def drop_all(self):
        """Drops all databases and users created.
        """
        self.drop_db(self.server1, "util_test")
        self.drop_db(self.server1, "master_db1")
        self.drop_db(self.server2, "util_test")
        self.drop_db(self.server2, "master_db1")
        self.drop_db(self.server3, "util_test")
        self.drop_db(self.server3, "master_db1")
        try:
            self.server1.exec_query("DROP USER 'joe'@'user'")
        except UtilError:
            pass
        try:
            self.server2.exec_query("DROP USER 'joe'@'user'")
        except UtilError:
            pass
        try:
            self.server3.exec_query("DROP USER 'joe'@'user'")
        except UtilError:
            pass
        return True
