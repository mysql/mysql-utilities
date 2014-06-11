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
audit_log_admin_errors test.
"""

import os

import audit_log_admin

from mysql.utilities.exception import MUTLibError


class test(audit_log_admin.test):
    """ Check errors of the mysqlauditadmin utility
    This test runs the mysqlauditadmin utility with several misconfigurations
    and wrong options to test known error conditions. It requires a server with
    the audit log plug-in enabled.
    """

    def check_prerequisites(self):
        # Prerequisites are the same of audit_log_admin test
        return audit_log_admin.test.check_prerequisites(self)

    def setup(self):
        # Setup is the same of the audit_log_admin test
        return audit_log_admin.test.setup(self)

    def run(self):
        #Run the following test cases...

        self.res_fname = "result.txt"

        cmd_base = "mysqlauditadmin.py "

        num_test = 1
        comment = "Test case {0} - Missing server option".format(num_test)
        cmd_opts = "--show-options"
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Server connection parse "
                   "error".format(num_test))
        cmd_opts = " --show-options --server=xpto"
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = "Test case {0} - Server connection empty".format(num_test)
        cmd_opts = " --show-options --server="
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = "Test case {0} - Invalid option".format(num_test)
        cmd_opts = " --xpto"
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        s_conn = "--server=" + self.build_connection_string(self.server1)

        num_test += 1
        comment = "Test case {0} - Invalid command".format(num_test)
        cmd_opts = "{0} xpto".format(s_conn)
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = "Test case {0} - Invalid policy value".format(num_test)
        cmd_opts = "{0} policy --value=XPTO".format(s_conn)
        res = self.run_test_case(1, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Invalid rotate_on_size "
                   "value".format(num_test))
        cmd_opts = "{0} rotate_on_size --value=XPTO".format(s_conn)
        res = self.run_test_case(1, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = "Test case {0} - Missing audit-log-name".format(num_test)
        cmd_opts = "--file-stats"
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Invalid file specified by "
                   "audit-log-name".format(num_test))
        cmd_opts = "--file-stats --audit-log-name=/xpto/xpto.log"
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Missing audit-log-name for command "
                   "copy".format(num_test))
        cmd_opts = "copy --copy-to=."
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        data_dir = self.server1.show_server_variable('datadir')[0][1]
        audit_log = self.server1.show_server_variable('audit_log_file')[0][1]
        audit_log_name = os.path.join(data_dir, audit_log)

        num_test += 1
        comment = ("Test case {0} - Missing copy-to for "
                   "command copy".format(num_test))
        cmd_opts = "copy --audit-log-name={0}".format(audit_log_name)
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Copy audit log to a non existing "
                   "destination".format(num_test))
        cmd_opts = ("copy --audit-log-name={0} "
                    "--copy-to=/xpto".format(audit_log_name))
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Invalid remote-login "
                   "format".format(num_test))
        cmd_opts = ("copy --audit-log-name={0} --copy-to={0} --remote-login="
                    "xpto".format(audit_log_name, data_dir))
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Value required for command "
                   "rotate_on_size".format(num_test))
        cmd_opts = "{0} rotate_on_size".format(s_conn)
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Value required for command "
                   "policy".format(num_test))
        cmd_opts = "{0} policy".format(s_conn)
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Server option required for command "
                   "rotate".format(num_test))
        cmd_opts = "rotate --show-options"
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = "Test case {0} - Only one command at a time".format(num_test)
        cmd_opts = "copy policy"
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = "Test case {0} - No option specified".format(num_test)
        res = self.run_test_case(2, cmd_base, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        s1_conn = "--server={0}".format(
            self.build_connection_string(self.server1))

        num_test += 1
        comment = ("Test case {0} - Additional server option/command "
                   "missing".format(num_test))
        cmd_opts = s1_conn
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Value option requires a valid "
                   "command".format(num_test))
        cmd_opts = "--value=XPTO"
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Additional audit log name option/command "
                   "missing".format(num_test))
        cmd_opts = "--audit-log-name={0}".format(audit_log_name)
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Copy-to option requires command "
                   "COPY".format(num_test))
        cmd_opts = "--copy-to={0}".format(data_dir)
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - User connection failure "
                   "".format(num_test))
        cmd_opts = "--server=r:r@notthere --show-options"
        res = self.run_test_case(1, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.replace_result("ERROR: Can't connect",
                            "ERROR: Can't connect to XXXX\n")
        self.replace_result("mysqlauditadmin: error: Server connection values"
                            " invalid",
                            "mysqlauditadmin: error: Server connection "
                            "values invalid\n")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return True
