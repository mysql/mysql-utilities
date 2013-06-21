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
from mysql.utilities.exception import MUTLibError


class test(diskusage_basic.test):
    """Disk usage parameters
    This test executes the disk space utility
    on a single server using a variety of parameters.
    It uses the diskusage_basic test for setup and teardown methods.
    """

    def check_prerequisites(self):
        if self.servers.get_server(0).check_version_compat(5, 6, 2):
            raise MUTLibError("Test requires server version prior to 5.6.2")
        return diskusage_basic.test.check_prerequisites(self)

    def setup(self):
        return diskusage_basic.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1)
        )

        cmd_base = ("mysqldiskusage.py {0} util_test "
                    "--format=csv").format(from_conn)
        test_num = 1
        comment = "Test Case {0} : Showing help ".format(test_num)
        cmd = "{0} --help".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: {0}: failed".format(comment))
        self.results.append("\n")
        test_num += 1

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqldiskusage.py "
                                           "version", 6)

        # no headers - only works when format != GRID
        comment = "Test Case {0} : No headers ".format(test_num)
        cmd = "{0} --no-headers".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: {0}: failed".format(comment))
        self.results.append("\n")
        test_num += 1

        # binlog
        comment = "Test Case {0} : Show binlog usage ".format(test_num)
        cmd = "{0} --binlog".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: {0}: failed".format(comment))
        self.results.append("\n")
        test_num += 1

        # logs
        comment = "Test Case {0} : Show log usage ".format(test_num)
        cmd = "{0} --logs".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: {0}: failed".format(comment))
        self.results.append("\n")
        test_num += 1

        try:
            res = self.server1.show_server_variable('datadir')
            if not res:
                raise MUTLibError("DISKUSAGE: Cannot get datadir.")
            datadir = res[0][1]
            os.mkdir(os.path.join(datadir, 'mt_db'))
        except:
            raise MUTLibError("DISKUSAGE: {0}: failed".format(comment))

        # InnoDB
        comment = "Test Case {0} : Show InnoDB usage ".format(test_num)
        cmd = "{0} --innodb".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: {0}: failed".format(comment))
        self.results.append("\n")
        test_num += 1

        # empty dbs
        comment = "Test Case {0} : Include empty database ".format(test_num)
        cmd = "{0} --empty mt_db".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: {0}: failed".format(comment))
        self.results.append("\n")
        test_num += 1

        # all
        comment = "Test Case {0} : Show all usage ".format(test_num)
        cmd_base = "mysqldiskusage.py {0} --format=csv".format(from_conn)
        cmd = "{0} --all".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: {0}: failed".format(comment))
        self.results.append("\n")
        test_num += 1

        # verbose with all
        comment = "Test Case {0} : Show all plus verbose ".format(test_num)
        cmd = "{0} -lambi -vv".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: {0}: failed".format(comment))
        self.results.append("\n")
        test_num += 1

        # quiet with all
        comment = "Test Case {0} : Show all plus quiet ".format(test_num)
        cmd = "{0} -lambi --quiet".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: {0}: failed".format(comment))
        self.results.append("\n")

        # Create a database using strange characters.
        self.server1.exec_query("CREATE DATABASE `strange.``name`")
        self.server1.exec_query("CREATE TABLE `strange.``name`.`we.i``rd` "
                                "(a char(30))")
        self.server1.exec_query('INSERT INTO `strange.``name`.`we.i``rd` '
                                'VALUES ("sample text")')

        test_num += 1
        comment = ("Test Case {0} : Database name with strange "
                   "characters.").format(test_num)
        cmd = '{0}'.format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: {0}: failed".format(comment))
        self.results.append("\n")

        # Show log usage using a user with strictly required mySQL privileges.

        # Grant only SUPER privilege to user (no previous privilege).
        self.server1.exec_query("GRANT SUPER ON *.* TO 'repl'@'{0}' IDENTIFIED "
                                "BY 'repl'".format(self.server1.host))

        test_num += 1
        comment = ("Test Case {0} : Use a user only with SUPER "
                   "privilege.").format(test_num)
        cmd_base = cmd_base.replace('root', 'repl')
        cmd = '{0} -a'.format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: {0}: failed".format(comment))
        self.results.append("\n")

        # Grant only REPLICATION CLIENT privilege to user (revoking previous
        # privilege).
        self.server1.exec_query("REVOKE SUPER ON *.* FROM "
                                "'repl'@'{0}'".format(self.server1.host))
        self.server1.exec_query("GRANT REPLICATION CLIENT ON *.* TO "
                                "'repl'@'{0}' IDENTIFIED BY "
                                "'repl'".format(self.server1.host))

        test_num += 1
        comment = ("Test Case {0} : Use a user only with REPLICATION CLIENT "
                   "privilege.").format(test_num)
        cmd_base = cmd_base.replace('root', 'repl')
        cmd = '{0} -a'.format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("DISKUSAGE: {0}: failed".format(comment))
        self.results.append("\n")

        diskusage_basic.test.mask(self)

        self.mask_column_result("strange.`name,", ",", 2, "XXXXXXX")
        self.mask_column_result("mysql,", ",", 2, "XXXXXXX")
        self.mask_column_result("util_test", ",", 2, "XXXXXXX")
        self.mask_column_result("mysql,X", ",", 3, "XXXXXXX")
        self.mask_column_result("util_test,X", ",", 3, "XXXXXXX")
        self.mask_column_result("mysql,X", ",", 4, "XXXXXXX")
        self.mask_column_result("util_test,X", ",", 4, "XXXXXXX")
        self.mask_column_result("mysql,X", ",", 5, "XXXXXXX")
        self.mask_column_result("util_test,X", ",", 5, "XXXXXXX")

        self.replace_result("error_log.err", "error_log.err,XXXX\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return diskusage_basic.test.cleanup(self)
