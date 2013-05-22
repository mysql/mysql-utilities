#
# Copyright (c) 2013, Oracle and/or its affiliates. All rights reserved.
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

import socket
import mutlib
from mysql.utilities.exception import MUTLibError

_IPv6_LOOPBACK = "::1"

_DEFAULT_MYSQL_OPTS = ('"--log-bin=mysql-bin  --report-host=%s '
                       '--report-port=%s --bind-address=:: "')
_PASS = "Pass\n"
_FAIL = "Failed\n\n"
_BAD_RESULT_MSG = ("Got wrong result for test case {0}. \n"
                   " Expected: {1}, got: {2}.")
_test_case_name = "test_case_name"
_aliases = "aliases"
_host_name = "host_name"
_result = "result"
_desc = "description"

_alias_reuseness = 'alias_reuseness'
_mock_no_local_host = 'mock_no_local_host'
# this address is used just to obtained his IP
_oracle_com = 'oracle.com'
_oracle_ip = socket.getaddrinfo(_oracle_com, None)[0][4][0]
# this address must return the same host_name using his IP
_python_org = "python.org"
_python_ip = socket.getaddrinfo(_python_org, None)[0][4][0]

_special_test_cases = [{_desc: "This test reuse of aliases",
                        _test_case_name: _alias_reuseness,
                       _aliases: [_alias_reuseness],
                       _host_name: _alias_reuseness,
                       _result: True},

                      {_desc: "this test addition of  lookup to aliases",
                       _test_case_name: _mock_no_local_host,
                       _aliases: [],
                       _host_name: _mock_no_local_host,
                       _result: True},

                      {_desc: "This test Negative host added to aliases",
                       _test_case_name: _alias_reuseness,
                       _aliases: [],
                       _host_name: _mock_no_local_host,
                       _result: False},

                      {_desc: ("This test non local server host name,"
                               " lookup of his aliases"),
                       _test_case_name: _oracle_com,
                       _aliases: [],
                       _host_name: _python_org,
                       _result: False},

                      {_desc: ("This test non local server, lookup"
                               " of aliases for the given hostname"),
                      _test_case_name: _oracle_com,
                       _aliases: [_mock_no_local_host],
                       _host_name: _mock_no_local_host,
                       _result: False},

                      {_desc: ("This test non local server,"
                               "lookup of aliases for the given ip"),
                       _test_case_name: _python_ip,
                       _aliases: [_mock_no_local_host],
                       _host_name: _mock_no_local_host,
                       _result: False},

                      {_desc: ("This test lookup of aliases for non "
                               "local server by IP."),
                       _test_case_name: _oracle_ip,
                       _aliases: [],
                       _host_name: _oracle_com,
                       _result: True},

                      {_desc: ("This test lookups of aliases for non "
                               "local server by hostname."),
                       _test_case_name: _python_org,
                       _aliases: [],
                       _host_name: _python_ip,
                       _result: True},

                      {_desc: ("It test the reuse of aliases for the "
                               "given non local server by hostname."),
                       _test_case_name: _python_org,
                       _aliases: [_python_ip],
                       _host_name: _python_ip,
                       _result: True}]


class test(mutlib.System_test):
    """test Server.is_alias() method.
    This test, test the result from Server.is_alias()
    Note: this test requires server version 5.5.30 and Internet connection.
    """

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 5, 30):
            raise MUTLibError("Test requires server version 5.5.30")
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"

        # Spawn servers
        # Change clone Server_List host value
        self.old_cloning_host = self.servers.cloning_host
        self.servers.cloning_host = _IPv6_LOOPBACK

        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS % (_IPv6_LOOPBACK,
                                        self.servers.view_next_port())
        self.server1_name = "server_1"
        res = self.servers.spawn_new_server(self.server0, "1001",
                                            self.server1_name, mysqld)
        if not res:
            raise MUTLibError("Cannot spawn server '{0}'."
                              "".format(name))
        self.server1 = res[0]

        self.host_name = socket.gethostname()

        # Duplicated values added to test reuse of calculated values.
        # All elements of List of good test cases are expected to return True.
        self.good_test_cases = ["127.0.0.1", "[::1]", "localhost",
                                self.host_name, "::1", "0:0:0:0:0:0:0:1",
                                "0::0:1", "[0::1]", "0::0:0:1"]
        # All elements of List of bad test cases are expected to return False.
        self.bad_test_cases = ["0.0.0.2", "[::2]", "host_local", "::2",
                               "0:0:0:0:0:0:0:2", "oracle.com", "python.org"]

        return True

    def run_is_alias_test(self, server, test_num, test_case,
                                    exp_res=True):
        NOT = ""
        if not exp_res:
            NOT = "not "
        comment = ("test case {0} - test alias: {1} is {2}alias for "
                   "server {3}".format(test_num, test_case, NOT, server.host))
        if self.debug:
                print(comment)
        self.results.append("{0}\n".format(comment))
        res = server.is_alias(test_case)
        if not res == exp_res:
            msg = _BAD_RESULT_MSG.format(test_num, repr(exp_res), repr(res))
            if self.debug:
                print("{0} {1}".format(_FAIL, msg))
            raise MUTLibError("{0}: {1} {2}".format(comment, _FAIL, msg))
        else:
            if self.debug:
                print(_PASS)
            self.results.append(_PASS)
        self.results.append("\n")
        server.aliases = []

    def run_is_alias_test_cases(self, server, test_num):
        for test_case in self.good_test_cases:
            test_num += 1
            self.run_is_alias_test(server, test_num, test_case)
        for test_case in self.bad_test_cases:
            test_num += 1
            self.run_is_alias_test(server, test_num, test_case, False)
        return test_num

    def run(self):
        test_num = 0
        if self.debug:
                print("\n")
        test_num = self.run_is_alias_test_cases(self.server0, test_num)
        test_num = self.run_is_alias_test_cases(self.server1, test_num)

        for dict in _special_test_cases:
            test_num += 1
            self.server1.aliases = dict[_aliases]
            self.server1.host = dict[_host_name]
            self.run_is_alias_test(self.server1, test_num, dict[_test_case_name],
                               dict[_result])

        # cleanup name_host
        self.server1.host = "localhost"
        # Mask Known results values.
        self.replace_substring(self.host_name, "<computer_name>")
        self.replace_substring(_oracle_ip, "ORACLE_IP")
        self.replace_substring(_python_ip, "PYTHON.ORG_IP")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Restoring clone Server_List host value
        self.servers.cloning_host = self.old_cloning_host
        # Kill the servers that are only for this test.
        self.servers.stop_server(self.server1)
        return True
