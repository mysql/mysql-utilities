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

import ssl_connection_simple_test


class test(ssl_connection_simple_test.test):
    """checks ssl connection support for utilities that uses add server option
    from option module.

    Shares the the same pre_requisites, setup and drop_all methods as the
    parent class.
    """
    # pylint: disable=W0221
    def run_test(self, test, test_case, conn_str, exp_result):
        """Runs each individual test.
        """
        test_cmd = "{0} {1}".format(test['cmd_str'].format(conn_str),
                                    test['cmd_opts'])
        test_comment = test['comment'].format(test_case)
        res = self.run_test_case(exp_result, test_cmd, test_comment)
        return res

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

        test_num = 0

        # conn_str without ssl options
        conn_opts = "{0}".format(conn_str)
        test_num = self.run_round_of_tests(tests, test_num, conn_opts,
                                           "No ssl options")

        # Servers prior to 5.7 will allow connection if ssl_ca is present
        # for that reason this case is not run on this test.
        # MySQl 5.7 may require a variant of this test.

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

        self.do_replacements()

        return True

    def do_replacements(self):
        """Mask out this information to make result file deterministic.
        """
        self.replace_substring("localhost", "XXXX-XXXX")
        self.replace_substring("127.0.0.1", "XXXX-XXXX")
        self.replace_substring("1045 (28000): ", "")

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return ssl_connection_simple_test.test.cleanup(self)
