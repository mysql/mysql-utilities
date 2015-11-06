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
import_parameters test.
"""

import import_parameters


class test(import_parameters.test):
    """check parameters for import utility
    This test executes a basic check of parameters for mysqldbimport.
    It uses the import_basic test as a parent for setup and teardown methods.
    """

    server_lst = None
    old_sql_mode_lst = None

    def setup(self):
        setup_ok = super(test, self).setup()
        self.server_lst = [self.server0, self.server1, self.server2]
        self.old_sql_mode_lst = []
        # if setup went ok, set STRICT SQL_MODE
        if setup_ok:
            for server in self.server_lst:
                self.old_sql_mode_lst.append(server.select_variable('sql_mode',
                                                                    'global'))
                server.exec_query("SET GLOBAL SQL_MODE=STRICT_ALL_TABLES")
        else:
            return False
        return len(self.server_lst) == len(self.old_sql_mode_lst)

    def run(self):
        run_ok = super(test, self).run()
        # if it ran ok, check if sql_mode is the same at the end
        if run_ok:
            for server in self.server_lst:
                sql_mode = server.select_variable('sql_mode', 'global')
                if not sql_mode.upper() == "STRICT_ALL_TABLES":
                    return False
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # restore sql_mode
        for server, sql_mode in (zip(self.server_lst, self.old_sql_mode_lst)):
            server.exec_query("SET GLOBAL SQL_MODE='{0}'".format(sql_mode))
        return super(test, self).cleanup()
