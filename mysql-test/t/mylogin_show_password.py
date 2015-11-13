#
# Copyright (c) 2015, Oracle and/or its affiliates. All rights reserved.
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
mylogin show password option test.
"""
import os
import shutil

import mutlib

from mysql.utilities.exception import MUTLibError
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.my_print_defaults import (my_login_config_path,
                                                      MyDefaultsReader,
                                                      MYLOGIN_FILE)

_VALUES_DIFFER_MSG = '  Values for {0} differ: expected "{1}" but found "{2}".'
_VALUES_EQUAL_MSG = '  Values for {0}: "{1}" and "{2}" are equivalent.'


class test(mutlib.System_test):
    """Test the login-path authentication mechanism.
    This module tests the capability to retrieve the password using
    my_print_defaults to access the .mylogin.cnf file on MySQL Server 5.6.25
    and 5.7.8 and newer versions, due the change of my_print_defaults'
    functionality (introduced on BUG#19953365, BUG#20903330) which mask
    passwords by default and added the '--show' password option to display
    passwords in cleartext.
    """

    mylogin_src = None
    mylogin_bkp = None

    def check_prerequisites(self):
        # Check if the required tools are accessible
        self.check_mylogin_requisites()

        # Check MySQL server version - Must be 5.6.25 or higher
        if not \
           (self.servers.get_server(0).check_version_compat(5, 7, 8) or
            (self.servers.get_server(0).check_version_compat(5, 6, 25) and
             not self.servers.get_server(0).check_version_compat(5, 7, 0))):
            raise MUTLibError("Test requires server version higher than 5.6.25"
                              " but lower than 5.7.0 or higher than 5.7.7")

        # .mylogin.cnf must be at his default location
        self.mylogin_src = os.path.normpath(
            os.path.join(my_login_config_path(), MYLOGIN_FILE)
        )
        if not os.path.exists(self.mylogin_src):
            raise MUTLibError("Test requires file .mylogin.cnf at his default"
                              " location: {0}".format(self.mylogin_src))

        # Check the required number of servers
        return self.check_num_servers(0)

    def setup(self):
        # Backup and replace .mylogin.cnf file
        self.mylogin_bkp = "{0}.bkp".format(self.mylogin_src)
        shutil.move(self.mylogin_src, self.mylogin_bkp)

        # Replace with test.mylogin.cnf
        mylogin_test_src = os.path.normpath("./std_data/test.mylogin.cnf")
        shutil.copy(mylogin_test_src, self.mylogin_src)

        # Copy permissions
        shutil.copymode(self.mylogin_bkp, self.mylogin_src)

        return True

    def run(self):
        # Test "--show" password in plain text option is available on this
        # version of my_print_defaults.
        test_num = 1
        test_case = 'Test "--show" password in plain text option is available'
        comment = "Test case {0}  {1}".format(test_num, test_case)
        my_defaults_reader = MyDefaultsReader()
        if not my_defaults_reader.check_show_required():
            raise MUTLibError("{0}: failed".format(comment))
        else:
            if self.debug:
                print("{0}: pass".format(comment))
            self.results.append("{0}: pass\n".format(comment))

        # Test retrieve of expected values for passwords variables stored in
        # test.mylogin.cnf
        con_tests = {
            "test1": "user_1:pass_1@localhost:10001",
            "test2": "user_2:A_passw0rd@localhost:20002",
            "test3": "user_3:M4g1cw0rd@localhost:30003",
            "test4": "user_4:-*123 !%^@remotehost:40004",
        }

        for group in sorted(con_tests.keys()):
            test_num += 1
            test_case = 'Test Retrieve group: "{0}"'.format(group)
            comment = "Test case {0}  {1}".format(test_num, test_case)
            self.results.append("{0}\n".format(comment))
            if self.debug:
                print(comment)

            # Retrieve stored values in group from .mylogin.cnf
            ret_dt = my_defaults_reader.get_group_data(group)
            # If not values, group was not found
            if ret_dt is None:
                if self.debug:
                    print('Can not retrieve values for group: "{}"'
                          ''.format(group))
                raise MUTLibError("{0}: failed".format(comment))

            con_dic = parse_connection(con_tests[group],
                                       options={"charset": "utf8"})

            con_dic.pop("charset")

            self.results.append("Retrieved data:\n")
            if self.debug:
                print("Retrieved data:")

            for data in sorted(ret_dt.iteritems()):
                # Only password is saved as passwd key
                if 'passw' in data[0]:
                    if con_dic['passwd'] != data[1]:
                        if self.debug:
                            print(_VALUES_DIFFER_MSG.format("password",
                                                            con_dic['passwd'],
                                                            data[1]))
                        raise MUTLibError("{0}: failed".format(comment))
                    else:
                        msg = _VALUES_EQUAL_MSG.format("password",
                                                       con_dic['passwd'],
                                                       data[1])
                        if self.debug:
                            print(msg)
                        self.results.append("{0}\n".format(msg))

                elif str(con_dic[data[0]]) != data[1]:
                    if self.debug:
                        print(_VALUES_DIFFER_MSG.format(data[0],
                                                        con_dic[data[0]],
                                                        data[1]))
                    raise MUTLibError("{0}: failed".format(comment))

                else:
                    msg = _VALUES_EQUAL_MSG.format(data[0], con_dic[data[0]],
                                                   data[1])
                    if self.debug:
                        print(msg)
                    self.results.append("{0}\n".format(msg))

            # None check failed, mark as pass
            self.results.append("Test result: pass\n")
            if self.debug:
                print("Result: pass")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # restore .mylogin.cnf from backup
        if os.path.exists(self.mylogin_bkp) and \
           os.path.exists(self.mylogin_src):
            os.unlink(self.mylogin_src)
            shutil.move(self.mylogin_bkp, self.mylogin_src)

        return True
