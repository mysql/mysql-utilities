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
clone_server_errors test.
"""

import os
import shutil

import mutlib

from mysql.utilities.exception import MUTLibError


class test(mutlib.System_test):
    """clone server errors
    This test exercises the error conditions for mysqlserverclone.
    """

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        # No setup needed
        return True

    def run(self):
        self.res_fname = "result.txt"
        srv0_con_str = self.build_connection_string(self.servers.get_server(0))
        cmd_str = "mysqlserverclone.py --server={0} ".format(srv0_con_str)

        test_num = 1
        port1 = int(self.servers.get_next_port())
        newport = "--new-port={0} ".format(port1)
        comment = ("Test case {0} - error: no --new-data "
                   "option".format(test_num))
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        comment = "Test case {0} - error: clone remote server".format(test_num)
        res = self.run_test_case(2, "mysqlserverclone.py "
                                    "--server=root:root@notme:90125 "
                                    "--new-data=/nada --delete-data "
                                    "--new-id=7 {0} ".format(newport), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        comment = "Test case {0} - error: no login".format(test_num)
        res = self.run_test_case(1, "mysqlserverclone.py "
                                    "--server=root:root@localhost:90125 "
                                    "--new-data=/nada --delete-data "
                                    "--new-id=7 {0}".format(newport), comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        comment = "Test case {0} - error: cannot connect".format(test_num)
        res = self.run_test_case(1, "mysqlserverclone.py --server=nope@"
                                    "localhost:38310 --new-data=/nada "
                                    "--new-id=7 --delete-data "
                                    "--root-password=nope {0}".format(newport),
                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        cmd_str = "{0} --new-id={1} {2} {3} {4}".format(
            cmd_str, self.servers.get_next_id(), newport,
            "--root-password=root ", "--new-data=/not/there/yes")
        comment = "Test case {0} - cannot create directory".format(test_num)
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Make the directory and put a file in it
        new_dir = os.path.join(os.getcwd(), "test123")
        shutil.rmtree(new_dir, True)
        os.mkdir(new_dir)
        f_out = open(os.path.join(new_dir, "temp123"), "w")
        f_out.write("test")
        f_out.close()
        cmd_str = ("mysqlserverclone.py --server=root:nope@nothere "
                   "--new-data={0} --new-id=7 --root-password=nope "
                   "{1}".format(new_dir, newport))
        comment = "Test case {0} - error: --new-data exists".format(test_num)
        res = self.run_test_case(2, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        shutil.rmtree(new_dir, True)

        cmd_str = ("mysqlserverclone.py --server=root:nope@localhost "
                   "--new-data={0} --new-id=7 --root-password=nope "
                   "{1}".format(new_dir, newport))
        comment = ("Test case {0} - --new-data does not exist (but cannot "
                   "connect)".format(test_num))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        cmd_str = ("mysqlserverclone.py --server={0} --new-port={1} "
                   "--new-data={2} --root=root"
                   "".format(srv0_con_str, self.servers.get_server(0).port,
                             new_dir))

        comment = ("Test case {0} - attempt to use existing "
                   "port".format(test_num))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_str = ("mysqlserverclone.py --server={0} --new-port={1} "
                   "--new-data=lo{2}ng --root=root"
                   "".format(srv0_con_str, port1, "o" * 200))

        comment = ("Test case {0} - use invalid big path in --new-data"
                   "".format(test_num))
        res = self.run_test_case(1, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        # Mask known platform-dependent lines
        self.mask_result("Error 2003:", "2003", "####")
        self.mask_result("Error 1045", "1045", "####:")

        self.replace_any_result(
            ["ERROR: Can't connect to MySQL server on ",
             "Error ####: Can't connect to MySQL server",
             "Error ####:(28000):", "Error Can't connect to MySQL server on",
             "ERROR: Access denied for user",
             "Error Access denied for user"],
            "Error ####: Can't connect to MySQL server on 'nothere:####'\n")

        self.replace_result("# Cloning the MySQL server running on ",
                            "# Cloning the MySQL server running on "
                            "XXXXX-XXXXX.\n")

        self.replace_result("#  -uroot", "#  -uroot [...]\n")

        self.replace_result("ERROR: Unable to create directory",
                            "ERROR: Unable to create directory "
                            "'/not/there/yes'\n")

        self.replace_substring_portion("ERROR: Port ", "in use",
                                       "ERROR: Port ##### in use")

        self.replace_substring_portion("ERROR: The --new-data path '",
                                       " is too long",
                                       "ERROR: The --new-data path 'XXXX' "
                                       "is too long")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return True
