#
# Copyright (c) 2014, Oracle and/or its affiliates. All rights reserved.
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
check ssl connection support test.
"""

import mutlib

from mysql.utilities.exception import MUTLibError, UtilError
from mysql.utilities.common.server import Server
from mysql.utilities.common.user import grant_proxy_ssl_privileges
from mutlib.ssl_certs import (ssl_pass, ssl_user, ssl_server_opts,
                              ssl_c_ca, ssl_c_cert, ssl_c_key)


class test(mutlib.System_test):
    """checks ssl connection support for utilities that uses add server option
    from option module or the add_ssl_options method.
    """

    server1 = None

    def check_prerequisites(self):
        # This test requires server version > 5.5.7, due to the lack of
        # 'GRANT PROXY ON ...' on previews versions.
        if not self.servers.get_server(0).check_version_compat(5, 5, 8):
            raise MUTLibError("Test requires server version >= 5.5.8")
        return self.check_num_servers(1)

    def setup(self):
        try:
            mysqld = "--log-bin=mysql-bin {0}".format(ssl_server_opts())
            self.servers.spawn_server('ssl_server',
                                      mysqld, kill=False)
        except MUTLibError as err:
            raise MUTLibError("Cannot spawn needed servers: {0}"
                              "".format(err.errmsg))

        index = self.servers.find_server_by_name('ssl_server')
        self.server1 = self.servers.get_server(index)

        for server in [self.server1]:
            try:
                grant_proxy_ssl_privileges(server, ssl_user, ssl_pass)
            except UtilError as err:
                raise MUTLibError("{0} on:{1}".format(err.errmsg,
                                                      server.role))

        conn_info = {
            'user': ssl_user,
            'passwd': ssl_pass,
            'host': self.server1.host,
            'port': self.server1.port,
            'ssl_ca': ssl_c_ca,
            'ssl_cert': ssl_c_cert,
            'ssl_key': ssl_c_key,
        }

        self.server1 = Server.fromServer(self.server1, conn_info)
        self.server1.connect()

        res = self.server1.exec_query("SHOW STATUS LIKE 'Ssl_cipher'")
        if not res[0][1]:
            raise MUTLibError("Cannot spawn a SSL server.")
        data_files = ["std_data/index_test.sql", "./std_data/basic_users.sql"]

        self.drop_all()
        for data_file in data_files:
            try:
                self.server1.read_and_exec_SQL(data_file, self.debug)
            except UtilError as err:
                raise MUTLibError("Failed to read commands from file {0}: "
                                  "{1}".format(data_file, err.errmsg))

        return True

    def run_test(self, test, test_case, conn_str):
        """Runs each individual test.
        """
        test_cmd = "{0} {1}".format(test['cmd_str'].format(conn_str),
                                    test['cmd_opts'])
        test_comment = test['comment'].format(test_case)
        res = self.run_test_case(0, test_cmd, test_comment)
        return res

    def run(self):
        self.res_fname = "result.txt"

        conn_str = self.build_connection_string(self.server1, ssl=True)

        tests = []

        # ======== mysqlindexcheck ========= #
        tests.append({
            "utility": "mysqlindexcheck",
            "cmd_str": "mysqlindexcheck.py --server={0}",
            "comment": ("Test case {0} - indexcheck with ssl connection all "
                        "tables for a single database"),
            "cmd_opts": "util_test_a"
        })

        # ======== mysqlserverinfo ========= #
        tests.append({
            "utility": "mysqlserverinfo",
            "cmd_str": "mysqlserverinfo.py --server={0}",
            "comment": "Test case {0} - basic serverinfo with ssl",
            "cmd_opts": " --format=vertical "
        })

        # ======== mysqluserclone ========= #
        tests.append({
            "utility": "mysqluserclone",
            "cmd_str": "mysqluserclone.py --source={0}",
            "comment": "Test case {0} - userclone dump grants with ssl",
            "cmd_opts": " -d -v {0}".format(" joe_pass@user")
        })

        # ========  mysqldbexport  ========= #
        tests.append({
            "utility": "mysqldbexport",
            "cmd_str": "mysqldbexport.py --server={0}",
            "comment": "Test case {0} - basic dbexport with ssl",
            "cmd_opts": " -edefinitions {0}".format("util_test_a")
        })

        # ========  mysqldbimport  ========= #
        tests.append({
            "utility": "mysqldbimport",
            "cmd_str": "mysqldbimport.py --server={0}",
            "comment": "Test case {0} - basic dbimport with ssl",
            "cmd_opts": " -d {0}".format("./std_data/import_data.sql")
        })

        # ========  mysqlmetagrep  =========#
        tests.append({
            "utility": "mysqlmetagrep",
            "cmd_str": "mysqlmetagrep.py --server={0}",
            "comment": "Test case {0} - basic metagrep with ssl",
            "cmd_opts": " -e%{0}".format("mysql")
        })

        # ========  mysqlprocgrep  ========= #
        tests.append({
            "utility": "mysqlprocgrep",
            "cmd_str": "mysqlprocgrep.py --server={0}",
            "comment": "Test case {0} - basic procgrep with ssl",
            "cmd_opts": " --match-user={0}".format(self.server1.user)
        })

        # ========  mysqldiskusage  ========= #
        tests.append({
            "utility": "mysqldiskusage",
            "cmd_str": "mysqldiskusage.py --server={0}",
            "comment": "Test case {0} - basic diskusage with ssl",
            "cmd_opts": " -q"
        })

        # ========  mysqlfrm  ========= #
        tests.append({
            "utility": "mysqlfrm",
            "cmd_str": "mysqlfrm.py --server={0}",
            "comment": "Test case {0} - basic mysqlfrm with ssl",
            "cmd_opts": " ./ --port={0}".format(self.servers.get_free_port())
        })

        # ========  mysqldbcopy  ========= #
        tests.append({
            "utility": "mysqldbcopy",
            "cmd_str": "mysqldbcopy.py --source={0} --destination={0}",
            "comment": "Test case {0} - basic mysqldbcopy with ssl",
            "cmd_opts": " util_test_a:util_test_z"
        })

        # ========  mysqldiff  ========= #
        tests.append({
            "utility": "mysqldiff",
            "cmd_str": "mysqldiff.py --server1={0} --server2={0}",
            "comment": "Test case {0} - basic mysqldiff with ssl",
            "cmd_opts": " util_test_a.t1:util_test_z.t1 --skip-table-options"
        })

        # mysqlbinlogrotate
        tests.append({
            "utility": "mysqlbinlogrotate",
            "cmd_str": "mysqlbinlogrotate.py --server={0}",
            "comment": "Test case {0} - basic mysqlbinlogrotate with ssl",
            "cmd_opts": ""
        })

        # mysqlbinlogpurge
        tests.append({
            "utility": "mysqlbinlogpurge",
            "cmd_str": "mysqlbinlogpurge.py --server={0}",
            "comment": "Test case {0} - basic mysqlbinlogpurge with ssl",
            "cmd_opts": ""
        })

        test_num = 0
        results_list = []
        for test in tests:
            test_num += 1
            res = self.run_test(test, test_num, conn_str)
            if not res:
                raise MUTLibError(
                    "{0}: failed".format(test['comment'].format(test_num)))
            else:
                results_list.append(
                    "{0}: {1}\n"
                    "".format(test["comment"].format(test_num), "passed")
                )

        self.results = results_list

        # Mask known source host name.
        self.replace_result("# Source on ",
                            "# Source on XXXX-XXXX: ... connected.\n")

        return True

    def drop_all(self):
        """Drops all databases and users.
        """
        # Drop databases
        databases = ["util_test_a", "util_test_b", "util_test_c",
                     "util_test_d", "util_test_e", "util_test_f",
                     "util_test_g", "util_test"]
        for db in databases:
            try:
                self.server1.exec_query("DROP DATABASE IF EXISTS "
                                        "{0}".format(db))
            except UtilError:
                pass

        # Drop users
        users = ["joe_nopass@'user'", "amy_nopass@'user'", "remote@'%'", ]
        for user in users:
            try:
                self.server1.exec_query("DROP USER {0}".format(user))
            except UtilError:
                pass
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        self.drop_all()
        return self.kill_server_list(['ssl_server'])
