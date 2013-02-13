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
import audit_log_grep
import os
from mysql.utilities.exception import MUTLibError


class test(audit_log_grep.test):
    """ Check errors of the mysqlauditgrep utility
    This test runs the mysqlauditgrep utility with several misconfigurations
    and wrong options to test known error conditions.
    It requires a server with the audit log plug-in enabled.
    """

    def check_prerequisites(self):
        # Prerequisites are the same of audit_log_grep test
        return audit_log_grep.test.check_prerequisites(self)

    def setup(self):
        # Setup is the same of the audit_log_grep test
        return audit_log_grep.test.setup(self)

    def run(self):
        #Run the following test cases...

        self.res_fname = "result.txt"

        cmd_base = "mysqlauditgrep.py "

        num_test = 1
        comment = "Test case %d - Missing audit log file" % num_test
        cmd_opts = ""
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Specified argument is not a file" % num_test
        cmd_opts = "--file-stats xpto.log"
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        #Invalid audit log
        audit_log_name = os.path.normpath("./std_data/audit.log.invalid")

        num_test += 1
        comment = "Test case %d - Malformed log file" % num_test
        cmd_opts = "--file-stats %s" % audit_log_name
        res = self.run_test_case(1, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        #Read audit log for testes
        audit_log_name = os.path.normpath("./std_data/audit.log.13488316109086370")

        num_test += 1
        comment = "Test case %d - Only one file search at a time" % num_test
        cmd_opts = "--file-stats %s xpto.log" % audit_log_name
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Invalid --users value" % num_test
        cmd_opts = "--users=,, %s" % audit_log_name
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Invalid --start-date format" % num_test
        cmd_opts = "--start-date=T12:30:05 %s" % audit_log_name
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Invalid --end-date format" % num_test
        cmd_opts = "--end-date=2012/09/30 %s" % audit_log_name
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Invalid --query-type option value" % num_test
        cmd_opts = '--query-type="", %s' % audit_log_name
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Invalid QUERY_TYPE value" % num_test
        cmd_opts = "--query-type=audit %s" % audit_log_name
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Invalid --event-type option value" % num_test
        cmd_opts = '--event-type=,,"", %s' % audit_log_name
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Invalid EVENT_TYPE value" % num_test
        cmd_opts = "--event-type=INSERT %s" % audit_log_name
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Option --pattern required" % num_test
        cmd_opts = "--regexp %s" % audit_log_name
        res = self.run_test_case(2, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - Invalid regexp pattern" % num_test
        cmd_opts = '--pattern="*." --regexp %s' % audit_log_name
        res = self.run_test_case(1, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        self.do_replacements()

        return True

    def do_replacements(self):
        invalid_audit_log = os.path.normpath("./std_data/audit.log.invalid")
        self.replace_result("ERROR: Malformed XML - Cannot parse log file: '" +
                            invalid_audit_log + "'",
                            "ERROR: Malformed XML - Cannot parse log file: "
                            "'std_data/audit.log.invalid'\n")

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return True
