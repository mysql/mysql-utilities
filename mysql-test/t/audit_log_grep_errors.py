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
audit_log_grep_errors test.
"""

import os

import audit_log_grep

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

        cmd_base = "mysqlauditgrep.py {0}"

        num_test = 1
        comment = "Test case {0} - Missing audit log file".format(num_test)
        cmd_opts = ""
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Specified argument is not a "
                   "file".format(num_test))
        cmd_opts = "--file-stats xpto.log"
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        #Invalid audit log
        audit_log_name = os.path.normpath("./std_data/audit.log.invalid")

        num_test += 1
        comment = "Test case {0} - Malformed log file".format(num_test)
        cmd_opts = "--file-stats {0}".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        #Read audit log for testes
        audit_log_name = os.path.normpath(
            "./std_data/audit.log.13488316109086370")

        num_test += 1
        comment = ("Test case {0} - Only one file search at a "
                   "time".format(num_test))
        cmd_opts = "--file-stats {0} xpto.log".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = "Test case {0} - Invalid --users value".format(num_test)
        cmd_opts = "--users=,, {0}".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = "Test case {0} - Invalid --start-date format".format(
            num_test)
        cmd_opts = "--start-date=T12:30:05 {0}".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = "Test case {0} - Invalid --end-date format".format(num_test)
        cmd_opts = "--end-date=2012/09/30 {0}".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Invalid --query-type option "
                   "value".format(num_test))
        cmd_opts = '--query-type="", {0}'.format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = "Test case {0} - Invalid QUERY_TYPE value".format(num_test)
        cmd_opts = "--query-type=audit {0}".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Invalid --event-type option "
                   "value".format(num_test))
        cmd_opts = '--event-type=,,"", {0}'.format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = "Test case {0} - Invalid EVENT_TYPE value".format(num_test)
        cmd_opts = "--event-type=INSERT {0}".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = "Test case {0} - Option --pattern required".format(num_test)
        cmd_opts = "--regexp {0}".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = "Test case {0} - Invalid regexp pattern".format(num_test)
        cmd_opts = '--pattern="*." --regexp {0}'.format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Invalid --status option "
                   "value".format(num_test))
        cmd_opts = '--status="",, {0}'.format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = "Test case {0} - Invalid STATUS value".format(num_test)
        cmd_opts = "--status=HY000 {0}".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Invalid STATUS interval "
                   "format".format(num_test))
        cmd_opts = "--status=1046,200-250-300 {0}".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Invalid STATUS interval "
                   "lower bound".format(num_test))
        cmd_opts = "--status=1.0-100 {0}".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Invalid STATUS interval "
                   "upper bound".format(num_test))
        cmd_opts = "--status=1- {0}".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.do_replacements()

        return True

    def do_replacements(self):
        invalid_audit_log = os.path.normpath("./std_data/audit.log.invalid")
        self.replace_result("ERROR: Malformed XML - Cannot parse log file: "
                            "'{0}'".format(invalid_audit_log),
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
