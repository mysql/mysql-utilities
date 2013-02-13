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
import audit_log_admin
import os
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
        comment = "Test case %d - Missing server option" % num_test
        cmd_opts = "--show-options"
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        num_test += 1
        comment = "Test case %d - Server connection parse error" % num_test
        cmd_opts = " --show-options --server=xpto"
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        num_test += 1
        comment = "Test case %d - Server connection empty" % num_test
        cmd_opts = " --show-options --server="
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        num_test += 1
        comment = "Test case %d - Invalid option" % num_test
        cmd_opts = " --xpto"
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        s_conn = "--server=" + self.build_connection_string(self.server1)
        
        num_test += 1
        comment = "Test case %d - Invalid command" % num_test
        cmd_opts = "%s xpto" % s_conn
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        num_test += 1
        comment = "Test case %d - Invalid policy value" % num_test
        cmd_opts = "%s policy --value=XPTO" % s_conn
        res = self.run_test_case(1, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        num_test += 1
        comment = "Test case %d - Invalid rotate_on_size value" % num_test
        cmd_opts = "%s rotate_on_size --value=XPTO" % s_conn
        res = self.run_test_case(1, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        
        num_test += 1
        comment = "Test case %d - Missing audit-log-name" % num_test
        cmd_opts = "--file-stats"
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
                        
        num_test += 1
        comment = "Test case %d - Invalid file specified by audit-log-name" \
                  % num_test
        cmd_opts = "--file-stats --audit-log-name=/xpto/xpto.log"
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Missing audit-log-name for command copy" \
                  % num_test
        cmd_opts = "copy --copy-to=."
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        data_dir = self.server1.show_server_variable('datadir')[0][1]
        audit_log = self.server1.show_server_variable('audit_log_file')[0][1]
        audit_log_name = os.path.join(data_dir, audit_log)

        num_test += 1
        comment = "Test case %d - Missing copy-to for command copy" % num_test
        cmd_opts = "copy --audit-log-name=%s" % audit_log_name
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Copy audit log to a non existing destination"\
                  % num_test
        cmd_opts = "copy --audit-log-name=%s --copy-to=/xpto" % audit_log_name
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Invalid remote-login format"\
                  % num_test
        cmd_opts = "copy --audit-log-name=%s --copy-to=%s --remote-login=xpto"\
                   % (audit_log_name, data_dir)
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Value required for command rotate_on_size" \
                  % num_test
        cmd_opts = "%s rotate_on_size" % s_conn
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Value required for command policy" % num_test
        cmd_opts = "%s policy" % s_conn
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Server option required for command rotate" \
                  % num_test
        cmd_opts = "rotate --show-options"
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Only one command at a time" % num_test
        cmd_opts = "copy policy"
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - No option specified" % num_test
        res = self.run_test_case(2, cmd_base, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        s1_conn = "--server=" + self.build_connection_string(self.server1)

        num_test += 1
        comment = "Test case %d - Additional server option/command missing" \
                  % num_test
        cmd_opts = s1_conn
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Value option requires a valid command" \
                  % num_test
        cmd_opts = "--value=XPTO"
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = ("Test case %d - Additional audit log name option\command "
                  "missing" % num_test)
        cmd_opts = "--audit-log-name=%s" % audit_log_name
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Copy-to option requires command COPY" \
                  % num_test
        cmd_opts = "--copy-to=%s" % data_dir
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        self.replace_result("mysqlauditadmin.py: error: Server connection "
                            "values invalid",
                            "mysqlauditadmin.py: error: Server connection "
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
