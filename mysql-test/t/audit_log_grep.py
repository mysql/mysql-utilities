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
from mysql.utilities.exception import MUTLibError, UtilError
from mysql.utilities.common.tools import check_python_version


class test(mutlib.System_test):
    """audit log search utility
    This test runs the mysqlauditgrep utility to test its features.
    Requires a server with the audit log plugin enabled.
    """

    def check_prerequisites(self):
        # Check Python version compatibility
        try:
            check_python_version(min_version=(2, 7, 0),
                                 max_version=(3, 0, 0),
                                 raise_exception_on_fail=True,
                                 name='audit_log_grep')
        except UtilError as e:
            raise MUTLibError(e.errmsg)

        # First, make sure the server to be clone has the audit log included.
        if not self.servers.get_server(0).supports_plugin("audit"):
            raise MUTLibError("Test requires a server with the audit log "
                              "plugin installed and enabled.")
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
            except MUTLibError, e:
                raise MUTLibError("Cannot spawn needed servers: %s" % \
                                   e.errmsg)
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
        else:
            #Restart plugin to force generation of an Audit event
            self.server1.exec_query("UNINSTALL PLUGIN audit_log")
            self.server1.exec_query("INSTALL PLUGIN audit_log SONAME "
                                    " 'audit_log%s'" % ext)
        return True

    def run(self):
        self.res_fname = "result.txt"

        cmd_base = "mysqlauditgrep.py "

        num_test = 1
        comment = "Test case %d - Show the help" % num_test
        cmd_opts = "--help "
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # Get the current (malformed) audit log file used by the server
        data_dir = self.server1.show_server_variable('datadir')[0][1]
        audit_log = self.server1.show_server_variable('audit_log_file')[0][1]
        audit_log_name = os.path.join(data_dir, audit_log)

        num_test += 1
        comment = "Test case %d - Show audit log statistics" % num_test
        cmd_opts = "--file-stats %s --format=VERTICAL" % audit_log_name
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - No search criteria defined" % num_test
        cmd_opts = "%s " % audit_log_name
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        #Read audit log for tests
        audit_log_name = os.path.normpath("./std_data/audit.log.13488316109086370")

        num_test += 1
        comment = "Test case %d - Convert all records to the defined format" \
                  % num_test
        cmd_opts = "%s --format=RAW" % audit_log_name
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        users = "tester"

        num_test += 1
        comment = "Test case %d - Search entries of specific users" % num_test
        cmd_opts = "--users=%s %s " % (users, audit_log_name)
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - No entry found for specified users" % \
                  num_test
        cmd_opts = "--users=xpto,,fake, %s " % audit_log_name
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        startdate = "2012-09-27T13:33:47"
        enddate = "2012-09-28"

        num_test += 1
        comment = "Test case %d - Search entries for a specific datetime " \
                  "range" % num_test
        cmd_opts = "--start-date=%s --end-date=%s %s" % (startdate, enddate,
                                                         audit_log_name)
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - No entry found for specified datetime "\
                  "range" % num_test
        cmd_opts = "--start-date=2012-01-01 --end-date=2012-01-01T23:59:59 " \
                   "%s" % audit_log_name
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        pattern = '"% = ___"'

        num_test += 1
        comment = "Test case %d - Search entries matching SQL LIKE pattern "\
                  % num_test
        cmd_opts = "--pattern=%s %s" % (pattern, audit_log_name)
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        pattern = '".* = ..."'

        num_test += 1
        comment = "Test case %d - Search entries matching REGEXP pattern "\
                  % num_test
        cmd_opts = "--pattern=%s --regexp %s" % (pattern, audit_log_name)
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - No entry found matching specified pattern "\
                  % num_test
        cmd_opts = '--pattern="%% = ___" --regexp %s' % audit_log_name
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        query_types = "show,SET"

        num_test += 1
        comment = "Test case %d - Search entries of specific query types" \
                  % num_test
        cmd_opts = "--query-type=%s %s" % (query_types, audit_log_name)
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - No entry found for specified query types" \
                  % num_test
        cmd_opts = "--query-type=GRANT,REVOKE %s" % audit_log_name
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        event_types = "Ping,cONNECT"

        num_test += 1
        comment = "Test case %d - Search entries of specific event types" \
                  % num_test
        cmd_opts = "--event-type=%s %s" % (event_types, audit_log_name)
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        num_test += 1
        comment = "Test case %d - No entry found for specified event types" \
                  % num_test
        cmd_opts = '--event-type="Binlog Dump,NoAudit" %s' % audit_log_name
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        users = "tester"
        startdate = "2012-10-10"
        enddate = "0"
        pattern = '".*<>.*"'
        query_types = "SELECT"
        event_types = "query"

        num_test += 1
        comment = "Test case %d - Apply all search criteria" \
                  % num_test
        cmd_opts = "--users=%s --start-date=%s --end-date=%s --pattern=%s " \
                   "--regexp --query-type=%s --event-type=%s %s" % \
                   (users, startdate, enddate, pattern, query_types, \
                    event_types, audit_log_name)
        res = self.run_test_case(0, cmd_base + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        self.do_replacements()

        return True

    def do_replacements(self):
        server_id = data_dir = self.server1.show_server_variable('server_id')[0][1]
        audit_log = self.server1.show_server_variable('audit_log_file')[0][1]
        self.replace_result("          File: " + audit_log,
                            "          File: audit.log\n")
        self.replace_result("          Size:",
                            "          Size: ...\n")
        self.replace_result("       Created:",
                            "       Created: ...\n")
        self.replace_result(" Last Modified:",
                            " Last Modified: ...\n")
        self.replace_result("       SERVER_ID: " + server_id,
                            "       SERVER_ID: <SERVER_ID>\n")
        self.replace_result(" STARTUP_OPTIONS:",
                            " STARTUP_OPTIONS: ...\n")
        self.replace_result("       TIMESTAMP:",
                            "       TIMESTAMP: ...\n")
        self.replace_result("   MYSQL_VERSION:",
                            "   MYSQL_VERSION: ...\n")
        self.replace_result("      OS_VERSION:",
                            "      OS_VERSION: ...\n")
        self.replace_result("         VERSION:",
                            "         VERSION: ...\n")

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return True
