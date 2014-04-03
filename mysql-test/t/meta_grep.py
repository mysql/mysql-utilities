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
meta_grep test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError, UtilError


class test(mutlib.System_test):
    """Process grep
    This test executes the process grep tool on a single server.
    """

    server1 = None
    need_servers = False

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        self.server1 = None
        self.need_servers = False
        if not self.check_num_servers(2):
            self.need_servers = True
        return self.check_num_servers(1)

    def setup(self):
        num_server = self.servers.num_servers()
        if self.need_servers:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError as err:
                raise MUTLibError(
                    "Cannot spawn needed servers: {0}".format(err.errmsg))
        else:
            num_server -= 1  # Get last server in list
        self.server1 = self.servers.get_server(num_server)
        data_file = os.path.normpath("./std_data/basic_data.sql")
        self.drop_all()
        try:
            self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file {0}: "
                              "{1}".format(data_file, err.errmsg))
        return True

    def run(self):
        self.res_fname = "result.txt"

        from_conn = self.build_connection_string(self.server1)

        cmd_base = ("mysqlmetagrep.py --server={0} "
                    "--database=util_test".format(from_conn))

        test_num = 1
        comment = "Test case {0} - find objects simple search".format(test_num)
        cmd = "{0} --pattern=t_".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = "Test case {0} - find objects name search".format(test_num)
        cmd = "{0} -b --pattern=%t2%".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = "Test case {0} - find objects regexp search".format(test_num)
        cmd = "{0} -Gb --pattern=t2".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - find objects regexp search with "
                   "type".format(test_num))
        cmd = "{0} -Gb --pattern=t2 --search=table".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        _FORMATS = ("CSV", "TAB", "VERTICAL", "GRID")
        for frmt in _FORMATS:
            test_num += 1
            comment = ("Test case {0} - find objects format="
                       "{1}".format(test_num, frmt))
            cmd = "{0} --format={1} -Gb --pattern=t2".format(cmd_base, frmt)
            res = self.run_test_case(0, cmd, comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))
            self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - find LIKE pattern in object body "
                   "(including VIEWS).".format(test_num))
        cmd = "{0} --body --pattern=%t1%".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        test_num += 1
        comment = ("Test case {0} - find REGEXP pattern in object body "
                   "(including VIEW).".format(test_num))
        cmd = "{0} -bG --pattern=t1".format(cmd_base)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")

        # CSV masks
        self.mask_column_result("root:*@localhost", ",", 1, "root[...]")

        # TAB masks
        self.mask_column_result("root:*@localhost", "\t", 1, "root[...]")

        # Vertical masks
        self.replace_result("  Connection: ", " Connection: XXXXX\n")

        # Grid masks
        # Here, we truncate all horizontal bars for deterministic results
        self.replace_result("+---", "+---+\n")
        self.mask_column_result("| root", "|", 2, " root[...]  ")
        self.replace_result("| Connection",
                            "| Connection | Object Type  | Object Name  "
                            "| Database   |\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def drop_all(self):
        """Drops all databases and users created.
        """
        res = self.drop_db(self.server1, "util_test")

        drop_user = ["DROP USER 'joe'@'user'", "DROP USER 'joe_wildcard'@'%'"]
        for drop in drop_user:
            try:
                self.server1.exec_query(drop)
            except UtilError:
                pass
        return res

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()
