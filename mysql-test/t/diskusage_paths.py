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
import diskusage_basic
from mysql.utilities.exception import MUTLibError, UtilError

_MYSQLD = ('--log-bin="{0}" --general-log --slow-query-log '
           '--slow-query-log-file="{1}" --general-log-file="{2}" '
           ' --log-error="{3}"')


class test(diskusage_basic.test):
    """Disk usage
    This test executes the disk space utility on a single server.
    It requires a 5.6.2 or later server for setting binary log and
    relay log paths. It uses diskusage_basic for cleanup.
    """

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 2):
            raise MUTLibError("Test requires server version 5.6.2 or later")
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

        index = self.servers.find_server_by_name("diskusage_paths")
        if index >= 0:
            self.server1 = self.servers.get_server(index)
            res = self.server1.show_server_variable("server_id")
            self.s1_serverid = int(res[0][1])
        else:
            self.binlog = os.path.join(os.getcwd(), "mysql-bin")
            self.gen_log = os.path.join(os.getcwd(), "general.log")
            self.slow_log = os.path.join(os.getcwd(), "slow.log")
            self.error_log = os.path.join(os.getcwd(), "error_log.err")
            self.s1_serverid = self.servers.get_next_id()
            mysqld_options = _MYSQLD.format(self.binlog, self.gen_log,
                                            self.slow_log, self.error_log)
            res = self.servers.spawn_new_server(self.server0, self.s1_serverid,
                                                "diskusage_paths",
                                                mysqld_options)
            if not res:
                raise MUTLibError("Cannot spawn diskusage_all server.")
            self.server1 = res[0]
            self.servers.add_new_server(self.server1, True)

        self.drop_all()
        data_file = os.path.normpath("./std_data/basic_data.sql")
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file "
                              "{0}: {1}".format(data_file, err.errmsg))
        return True

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))

        cmd_base = ("mysqldiskusage.py {0} util_test "
                    "--format=CSV -a".format(from_conn))
        test_num = 1
        comment = ("Test Case {0} : Testing disk space "
                   "(with paths)".format(test_num))
        res = self.run_test_case(0, cmd_base, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: {0}: failed".format(comment))

        diskusage_basic.test.mask(self)

        self.replace_result("db_name,total", "db_name,total\n")
        self.replace_result("log_name,size", "log_name,size\n")
        self.replace_result("error_log.err,", "error_log.err,XXXXX\n")
        self.replace_result("log_file,size", "log_file,size\n")
        self.replace_result("innodb_file,size", "innodb_file,size\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        folder = os.getcwd()
        for item in os.listdir(folder):
            name, ext = os.path.splitext(item)
            if name.upper() == "MYSQL-BIN":
                os.unlink(item)

        kill_list = ['diskusage_paths']
        res = diskusage_basic.test.cleanup(self)
        return res and self.kill_server_list(kill_list)
