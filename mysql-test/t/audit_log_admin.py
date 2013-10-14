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
import mutlib
from mysql.utilities.exception import MUTLibError


class test(mutlib.System_test):
    """audit log maintenance utility
    This test runs the mysqlauditadmin utility to test its features. Requires
    a server with the audit log plug-in enabled.
    """

    def check_prerequisites(self):
        # First, make sure the server to be clone has the audit log included.
        if not self.servers.get_server(0).supports_plugin("audit"):
            raise MUTLibError("Test requires a server with the audit log "
                              "plug-in installed and enabled.")
        self.server1 = None
        self.need_servers = False
        if not self.check_num_servers(2):
            self.need_servers = True
        return self.check_num_servers(1)

    def setup(self):
        self.server0 = self.servers.get_server(0)
        num_server = self.servers.num_servers()
        if self.need_servers:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers: "
                                  "{0}".format(err.errmsg))
        else:
            num_server -= 1  # Get last server in list
        self.server1 = self.servers.get_server(num_server)

        # Now install the audit log plugin
        if os.name == "posix":
            ext = ".so"
        else:
            ext = ".dll"
        if not self.server1.supports_plugin("audit"):
            self.server1.exec_query("INSTALL PLUGIN audit_log SONAME "
                                    " 'audit_log%s'" % ext)
        return True

    def run(self):
        self.res_fname = "result.txt"

        s1_conn = "--server=" + self.build_connection_string(self.server1)

        cmd_base = "mysqlauditadmin.py "

        num_test = 1
        comment = "Test case %d - show the help " % num_test
        cmd_opts = " --help "
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        num_test += 1

        comment = "Test case %d - show the audit options " % num_test
        cmd_opts = " --show-options %s " % s1_conn
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        num_test += 1

        data_dir = self.server1.show_server_variable('datadir')[0][1]
        audit_log = self.server1.show_server_variable('audit_log_file')[0][1]

        comment = "Test case %d - show file stats - before rotate " % num_test
        cmd_opts = " --file-stats --audit-log-name=%s " % \
                   os.path.join(data_dir, audit_log)
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        num_test += 1

        comment = "Test case %d - rotate the audit log " % num_test
        cmd_opts = " --show-options %s rotate " % s1_conn
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        num_test += 1

        # To show last test case succeeded, we need to show the log files again
        comment = "Test case %d - show file stats after rotate " % num_test
        cmd_opts = " --file-stats --audit-log-name=%s " % \
                   os.path.join(data_dir, audit_log)
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        num_test += 1

        comment = "Test case %d - change the policy to QUERIES" % num_test
        cmd_opts = " --show-options %s policy --value=QUERIES " % s1_conn
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        num_test += 1

        comment = "Test case %d - change the policy to default" % num_test
        cmd_opts = " --show-options %s policy --value=DEFAULT " % s1_conn
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        num_test += 1

        comment = "Test case %d - change the rotate_on_size to 32535" \
                  % num_test
        cmd_opts = " --show-options %s rotate_on_size --value=32535 " \
                   % s1_conn
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        num_test += 1

        comment = "Test case %d - change the rotate_on_size to default" \
                  % num_test
        cmd_opts = " --show-options %s rotate_on_size --value=0 " % s1_conn
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        self.do_replacements()

        return True

    def do_replacements(self):
        self.replace_substring("127.0.0.1", "localhost")
        self.replace_result("| audit.log", "| audit.log [...] \n")

        # Remove new audit log variable recently introduced.
        self.remove_result("| audit_log_format")

        # Mask output of file stats after rotate to support filename changes
        # (e.g. filename with and without .xml extension).
        self.replace_substring_portion("+------------------------------",
                                       "---------------------------+"
                                       "---------------------------+",
                                       "+------------------------------+"
                                       "-------+---------------------------+"
                                       "---------------------------+")
        self.replace_substring_portion("| File                             ",
                                       " Created                   |"
                                       " Last Modified             |",
                                       "| File                         "
                                       "| Size  | Created                   |"
                                       " Last Modified             |")

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqlauditadmin"
                                           ".py version", 6)

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return True
