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

class test(mutlib.System_test):
    """Disk usage
    This test executes the disk space utility on a single server.
    It uses the diskusage test for setup and teardown methods.
    """

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
            except MUTLibError, e:
                raise MUTLibError("Cannot get diskusage_all server " +
                                   "server_id: %s" % e.errmsg)
            self.s1_serverid = int(res[0][1])
        else:
            self.gen_log = os.path.join(os.getcwd(), "general.log")
            self.slow_log = os.path.join(os.getcwd(), "slow.log")
            self.error_log = os.path.join(os.getcwd(), "error_log.err")
            self.s1_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(self.server0, self.s1_serverid,
                                                "diskusage_all",
                                                ' --mysqld="--log-bin=mysql-'
                                                'bin --general-log '
                                                '--slow-query-log '
                                                '--slow-query-log-file=%s '
                                                '--general-log-file=%s '
                                                ' --log-error=%s"' %
                                                (self.gen_log, self.slow_log,
                                                 self.error_log))
            if not res:
                raise MUTLibError("Cannot spawn diskusage_all server.")
            self.server1 = res[0]
            self.servers.add_new_server(self.server1, True)

        self.drop_all()
        data_file = os.path.normpath("./std_data/basic_data.sql")
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
        except MUTLibError, e:
            raise MUTLibError("Failed to read commands from file %s: " % \
                               data_file + e.errmsg)
        return True


    def mask(self):
        # Do masking
        self.mask_column_result("| util_test  ", "|", 3, " XXXXXXX  ")

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

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server=%s" % self.build_connection_string(self.server1)

        cmd_base = "mysqldiskusage.py %s util_test --format=CSV" % from_conn
        test_num = 1
        comment = "Test Case %d : Testing disk space (simple)" % test_num
        res = self.run_test_case(0, cmd_base, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: %s: failed" % comment)

        cmd_base = "mysqldiskusage.py %s util_test --empty test" % from_conn
        test_num = 2
        comment = "Test Case %d : Testing disk space (with empty)" % test_num
        res = self.run_test_case(0, cmd_base, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: %s: failed" % comment)

        self.mask()

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        try:
            res = server.exec_query("SHOW DATABASES LIKE 'util_%%'")
        except:
            return True # Ok to exit here as there weren't any dbs to drop
        try:
            res = server.exec_query("DROP DATABASE %s" % db)
        except:
            return False
        return True

    def drop_all(self):
        try:
            self.drop_db(self.server1, "util_test")
        except:
            return False
        return True

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except:
                pass
        self.servers.add_cleanup_file(self.gen_log)
        self.servers.add_cleanup_file(self.slow_log)
        self.servers.add_cleanup_file(self.error_log)
        return self.drop_all()
