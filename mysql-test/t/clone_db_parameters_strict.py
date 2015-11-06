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
clone_db_parameters_strict test.
"""

import clone_db_parameters


class test(clone_db_parameters.test):
    """check parameters for clone db using strict mode
    This test executes a series of clone database operations on a single
    server using a variety of parameters. It uses the clone_db_strict test
    as a parent for setup and teardown methods.
    """
    old_sql_mode = None

    def setup(self):
        setup_ok = super(test, self).setup()
        # if setup went ok, set STRICT SQL_MODE
        if setup_ok:
            self.old_sql_mode = self.server1.select_variable('sql_mode',
                                                             'global')
            self.server1.exec_query("SET GLOBAL SQL_MODE=STRICT_ALL_TABLES")
        else:
            return False
        return True

    def run(self):
        run_ok = super(test, self).run()
        # if it ran ok, check if sql_mode is the same at the end
        if run_ok:
            sql_mode = self.server1.select_variable('sql_mode', 'global')

            if not sql_mode.upper() == "STRICT_ALL_TABLES":
                return False
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # restore sql_mode
        self.server1.exec_query("SET GLOBAL SQL_MODE="
                                "'{0}'".format(self.old_sql_mode))
        return super(test, self).cleanup()
