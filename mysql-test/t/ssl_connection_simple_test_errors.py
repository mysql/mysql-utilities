#
# Copyright (c) 2014, 2015, Oracle and/or its affiliates. All rights reserved.
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

from mysql.utilities.exception import MUTLibError

from mutlib.ssl_certs import ssl_c_ca_b

import ssl_connection_simple_test


class test(ssl_connection_simple_test.test):
    """checks ssl connection support for utilities that uses add server option
    from option module.

    Shares the the same pre_requisites and drop_all methods as the
    parent class.
    """

    server2 = None

    def setup(self):
        super(test, self).setup()
        try:
            self.servers.spawn_server('no_ssl_server', mysqld="--ssl=0")
        except MUTLibError as err:
            raise MUTLibError("Cannot spawn needed servers: {0}"
                              "".format(err.errmsg))

        index = self.servers.find_server_by_name('no_ssl_server')
        self.server2 = self.servers.get_server(index)

        return True

    def run_round_of_tests(self, tests, test_num, conn_opts, comment):
        """Runs a round of tests.
        """
        exp_result = 2
        self.results.append("{0}\n".format("#" * 78))
        self.results.append("--> {0}\n".format(comment))
        self.results.append("{0}\n".format("#" * 78))
        for test in tests:
            test_num += 1
            self.run_test(test, test_num, conn_opts, exp_result)
            self.results.append("\n")
        return test_num

    def run(self):
        self.res_fname = "result.txt"

        conn_str = self.build_connection_string(self.server1, ssl=False)
        conn_val = self.get_connection_values(self.server1)
        ssl_ca = "--ssl-ca={0}".format(conn_val[6])
        ssl_cert = "--ssl-cert={0}".format(conn_val[7])
        ssl_key = "--ssl-key={0}".format(conn_val[8])
        ssl = "--ssl={0}"
        conn_no_ssl = self.build_connection_string(self.server2)
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

        # ========  mysqlmetagrep  ========= #
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
            "cmd_opts": ""
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

        # ========  mysqlbinlogrotate  ========= #
        tests.append({
            "utility": "mysqlbinlogrotate",
            "cmd_str": "mysqlbinlogrotate.py --server={0}",
            "comment": "Test case {0} - basic mysqlbinlogrotate with ssl",
            "cmd_opts": ""
        })

        # ========  mysqlbinlogpurge  ========= #
        tests.append({
            "utility": "mysqlbinlogpurge",
            "cmd_str": "mysqlbinlogpurge.py --server={0}",
            "comment": "Test case {0} - basic mysqlbinlogpurge with ssl",
            "cmd_opts": ""
        })

        test_num = 0

        # conn_str without ssl options
        conn_opts = "{0}".format(conn_str)
        test_num = self.run_round_of_tests(tests, test_num, conn_opts,
                                           "No ssl options")

        # conn_str with --ssl-ca and --ssl-key options only
        conn_opts = "{0} {1} {2}".format(conn_str, ssl_ca, ssl_key)
        test_num = self.run_round_of_tests(tests, test_num, conn_opts,
                                           "--ssl-ca and --ssl"
                                           "-key options only")

        # conn_str with --ssl-key option only
        conn_opts = "{0} {1}".format(conn_str, ssl_key)
        test_num = self.run_round_of_tests(tests, test_num, conn_opts,
                                           "--ssl-key option only")

        # conn_str with --ssl-key and --ssl-cert options only
        conn_opts = "{0} {1} {2}".format(conn_str, ssl_key, ssl_cert)
        test_num = self.run_round_of_tests(tests, test_num, conn_opts,
                                           "--ssl-key and "
                                           "--ssl-cert options only")

        # conn_str with invalid --ssl-ca option
        invalid_ssl_ca = "--ssl-ca=./"
        conn_opts = "{0} {1}".format(conn_str, invalid_ssl_ca)
        test_num = self.run_round_of_tests(tests, test_num, conn_opts,
                                           "invalid --ssl-ca "
                                           "option")

        # conn_str with invalid --ssl-ca option
        invalid_ssl_ca = "--ssl-ca=./std_data"
        conn_opts = "{0} {1}".format(conn_str, invalid_ssl_ca)
        test_num = self.run_round_of_tests(tests, test_num, conn_opts,
                                           "invalid --ssl-ca "
                                           "option")

        # conn_str with unexisting certificate file in --ssl-ca option
        invalid_ssl_ca = "--ssl-ca=./std_data/unexisting.pem"
        conn_opts = "{0} {1}".format(conn_str, invalid_ssl_ca)
        test_num = self.run_round_of_tests(tests, test_num, conn_opts,
                                           "unexisting certificate"
                                           "file in --ssl-ca option")

        # conn_str with unexisting certificate file in --ssl-cert option
        invalid_ssl_ca = "--ssl-cert=./std_data/unexisting.pem"
        conn_opts = "{0} {1}".format(conn_str, invalid_ssl_ca)
        test_num = self.run_round_of_tests(tests, test_num, conn_opts,
                                           "unexisting certificate"
                                           "file in --ssl-cert option")

        # conn_str with unexisting certificate file in --ssl-cert option
        invalid_ssl_ca = "--ssl-key=./std_data/unexisting.pem"
        conn_opts = "{0} {1}".format(conn_str, invalid_ssl_ca)
        test_num = self.run_round_of_tests(tests, test_num, conn_opts,
                                           "unexisting certificate"
                                           "file in --ssl-key option")

        # conn_str with --ssl=0 with user that requires SSL
        ssl_required = ssl.format("0")
        conn_opts = "{0} {1}".format(conn_str, ssl_required)
        test_num = self.run_round_of_tests(tests, test_num, conn_opts,
                                           "only --ssl=0 option for ssl "
                                           "required user")

        # conn_str with --ssl=1 with server without ssl certs and user that no
        # requires SSL
        ssl_required = ssl.format("1")
        conn_opts = "{0} {1}".format(conn_no_ssl, ssl_required)
        test_num = self.run_round_of_tests(tests, test_num, conn_opts,
                                           "only --ssl=1 option and server "
                                           "without ssl certs")

        # conn_str with --ssl=1 with different ca-cert
        ssl_required = ssl.format("1")
        conn_opts = "{0} --ssl-ca={1} {2}".format(conn_str, ssl_c_ca_b,
                                                  ssl_required)
        test_num = self.run_round_of_tests(tests, test_num, conn_opts,
                                           "--ssl=1 option and different ssl "
                                           "ca-cert")

        self.do_replacements()

        return True

    def do_replacements(self):
        """Mask out this information to make result file deterministic.
        """
        self.replace_substring("localhost", "XXXX-XXXX")
        self.replace_substring("127.0.0.1", "XXXX-XXXX")
        self.replace_substring(repr(self.server1.port), "XXXX")
        self.replace_result("# Starting the spawned server on port",
                            "# Starting the spawned server on port...\n")
        self.replace_substring("1045 (28000): ", "")
        self.replace_result("+---", "+---+\n")
        self.mask_column_result("| root", "|", 2, " root[...]  ")
        self.replace_result("| root[...]",
                            "| root[...]\n")
        self.remove_result_and_lines_after("              config_file:", 16)
        self.remove_result_and_lines_after("| db_name             |", 12)
        self.remove_result("# Database totals:")
        self.remove_result_and_lines_after("Total database disk u", 2)
        self.replace_substring("mysqldiskusage: error: Lost connection",
                               "ERROR: Lost connection")
        self.replace_substring("ERROR: 2055: Lost connection",
                               "ERROR: Lost connection")
        self.replace_substring("mysqlfrm: error: Lost connection",
                               "ERROR: Lost connection")
        self.replace_substring_portion("ERROR: Lost connection",
                                       "certificate verify failed",
                                       "certificate verify failed")
        self.replace_result("ERROR: Lost connection to MySQL server at",
                            "ERROR: Lost connection to MySQL server at"
                            " 'XXXX-XXXX:XXXX'\n")
        self.replace_result("certificate verify failed",
                            "certificate verify failed\n")
        # Mask password field on grant statements since it stopped appearing on
        # versions >= 5.7.6
        self.replace_substring_portion(" IDENTIFIED BY PASSWORD '", "'", "")
        # Remove warning that appears only on 5.7 and which is not important
        # for the sake of this test.
        self.remove_result_and_lines_around(
            "WARNING: Unable to get size information from 'stderr' "
            "for 'error log'.", lines_before=3, lines_after=1)

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        self.kill_server_list(['no_ssl_server'])
        return ssl_connection_simple_test.test.cleanup(self)
