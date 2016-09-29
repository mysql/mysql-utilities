#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights reserved.
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
diskusage_basic test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError, UtilError


class test(mutlib.System_test):
    """Disk usage
    This test executes the disk space utility on a single server.
    It uses the diskusage test for setup and teardown methods.
    """

    server0 = None
    server1 = None
    server2 = None
    gen_log = None
    slow_log = None
    error_log = None
    export_import_file = None
    s1_serverid = None

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        if self.servers.get_server(0).check_version_compat(5, 6, 2):
            raise MUTLibError("Test requires server version prior to 5.6.2")
        # Need at least one server.
        self.server1 = None
        self.server2 = None
        self.gen_log = None
        self.slow_log = None
        self.error_log = None
        return self.check_num_servers(1)

    def setup(self):
        self.server0 = self.servers.get_server(0)
        self.export_import_file = "test_run.txt"

        index = self.servers.find_server_by_name("diskusage_all")
        if index >= 0:
            self.server1 = self.servers.get_server(index)
            try:
                res = self.server1.show_server_variable("server_id")
            except MUTLibError as err:
                raise MUTLibError("Cannot get diskusage_all server "
                                  "server_id: {0}".format(err.errmsg))
            self.s1_serverid = int(res[0][1])
        else:
            self.gen_log = os.path.join(os.getcwd(), "general.log")
            self.slow_log = os.path.join(os.getcwd(), "slow.log")
            self.error_log = os.path.join(os.getcwd(), "error_log.err")
            self.s1_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(
                self.server0, self.s1_serverid, "diskusage_all",
                ' --mysqld=--log-bin=mysql-bin --general-log --slow-query-log '
                '--slow-query-log-file="{0}" --general-log-file="{1}" '
                ' --log-error="{2}"'.format(self.slow_log, self.gen_log,
                                            self.error_log))
            if not res:
                raise MUTLibError("Cannot spawn diskusage_all server.")
            self.server1 = res[0]
            self.servers.add_new_server(self.server1, True)

        self.drop_all()
        data_file = os.path.normpath("./std_data/basic_data.sql")
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: "
                              "{1}".format(data_file, err.errmsg))

        # Create a new user 'repl:repl' (without privileges).
        try:
            self.server1.exec_query("CREATE USER 'repl'@'{0}' IDENTIFIED BY "
                                    "'repl'".format(self.server1.host))
        except UtilError as err:
            raise MUTLibError("Failed to create user 'repl'@'{0}' (with "
                              "password 'repl'): {1}".format(self.server1.host,
                                                             err.errmsg))

        return True

    def mask(self):
        """Masks result.
        """
        self.mask_column_result("| util_test  ", "|", 3, " XXXXXX  ")

        self.mask_column_result("ib", ",", 2, "XXXXXXXX")
        self.mask_column_result("general.log", ",", 2, "XXXX")
        self.mask_column_result("slow.log", ",", 2, "XXXX")
        self.mask_column_result("mysql-bin", ",", 2, "XXXX")
        self.mask_column_result("util_test", ",", 2, "XXXXXXX")

        self.mask_column_result("util_test", "\t", 2, "XXXXXXX")

        self.replace_result("   total:", "    total: XXXXXXX\n")

        self.replace_result("Total database disk",
                            "Total database disk usage = XXXXXXX\n")

        self.replace_result("Current binary log file",
                            "Current binary log file = XXXX\n")

        self.replace_result("Current relay log file",
                            "Current relay log file = XXXX\n")

        self.replace_result("Total size of logs",
                            "Total size of logs = XXXX\n")

        self.replace_result("Total size of binary",
                            "Total size of binary logs = XXXX\n")

        self.replace_result("Total size of relay",
                            "Total size of relay logs = XXXX\n")

        self.replace_result("Total size of InnoDB",
                            "Total size of InnoDB files = XXXXXXXX\n")
        self.replace_result("InnoDB freespace",
                            "InnoDB freespace = XXXXXXXX\n")

        self.remove_result("performance_schema")

        self.replace_result("Tablespace ibdata1:10M:autoextend",
                            "Tablespace ibdata1:10M:autoextend...\n")

        # Mask size of binary log files
        self.replace_result("clone-bin.000001,", "clone-bin.000001,XXXX\n")
        self.replace_result("clone-bin.index,", "clone-bin.index,XXXX\n")

        # Mask the grid output
        self.replace_result("+----", "+----\n")
        self.replace_result("| db_name ", "| db_name ... total\n")

    def run(self):
        self.mask_global = False  # Turn off global masks
        self.res_fname = "result.txt"

        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))

        cmd_base = ("mysqldiskusage.py {0} util_test "
                    "--format=CSV".format(from_conn))
        test_num = 1
        comment = ("Test Case {0} : Testing disk space "
                   "(simple)".format(test_num))
        res = self.run_test_case(0, cmd_base, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: {0}: failed".format(comment))

        cmd_base = ("mysqldiskusage.py {0} util_test --empty "
                    "test".format(from_conn))
        test_num += 1
        comment = ("Test Case {0} : Testing disk space "
                   "(with empty)".format(test_num))
        res = self.run_test_case(0, cmd_base, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: {0}: failed".format(comment))

        self.mask()

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_all(self):
        """Drops all databases and users created.
        """
        # Drop user.
        try:
            self.server1.exec_query(
                "DROP USER 'repl'@'{0}'".format(self.server1.host)
            )
        except UtilError:
            pass  # Ignore DROP USER failure in case user does not exist.
        drop_user = ["DROP USER 'joe'@'user'", "DROP USER 'joe_wildcard'@'%'"]
        for drop in drop_user:
            try:
                self.server1.exec_query(drop)
            except UtilError:
                pass
        # Drop database.
        return self.drop_db(self.server1, "util_test")

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except OSError:
                pass
        self.servers.add_cleanup_file(self.gen_log)
        self.servers.add_cleanup_file(self.slow_log)
        self.servers.add_cleanup_file(self.error_log)
        return self.drop_all()
