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
audit_log_grep test.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError


class test(mutlib.System_test):
    """audit log search utility
    This test runs the mysqlauditgrep utility to test its features.
    Requires a server with the audit log plugin enabled.
    """

    server0 = None
    server1 = None
    need_servers = False

    def check_prerequisites(self):
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
                                    " 'audit_log{0}'".format(ext))
        else:
            #Restart plugin to force generation of an Audit event
            self.server1.exec_query("UNINSTALL PLUGIN audit_log")
            self.server1.exec_query("INSTALL PLUGIN audit_log SONAME "
                                    " 'audit_log{0}'".format(ext))
        return True

    def run(self):
        self.res_fname = "result.txt"

        cmd_base = "mysqlauditgrep.py {0}"

        num_test = 1
        comment = "Test case {0} - Show the help".format(num_test)
        cmd_opts = "--help "
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Get the current (malformed) audit log file used by the server
        data_dir = self.server1.show_server_variable('datadir')[0][1]
        audit_log = self.server1.show_server_variable('audit_log_file')[0][1]
        audit_log_name = os.path.join(data_dir, audit_log)

        num_test += 1
        comment = "Test case {0} - Show audit log statistics".format(num_test)
        cmd_opts = "--file-stats {0} --format=VERTICAL".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = "Test case {0} - No search criteria defined".format(num_test)
        cmd_opts = "{0} ".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Audit log for tests (old format).
        audit_log_name = os.path.normpath(
            "./std_data/audit.log.13488316109086370")

        # Audit log for tests (NEW format).
        new_audit_log_name = os.path.normpath(
            "./std_data/audit.log.13951424704434196.xml")

        num_test += 1
        comment = ("Test case {0} - Show all records in the RAW "
                   "format".format(num_test))
        cmd_opts = "{0} --format=RAW".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        comment = ("Test case {0} (NEW) - Show all records in the RAW "
                   "format".format(num_test))
        cmd_opts = "{0} --format=RAW".format(new_audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        users = "tester"

        num_test += 1
        comment = ("Test case {0} - Search entries of specific "
                   "users".format(num_test))
        cmd_opts = "--users={0} {1} ".format(users, audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        comment = ("Test case {0} (NEW) - Search entries of specific "
                   "users".format(num_test))
        cmd_opts = "--users={0} {1} ".format(users, new_audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - No entry found for specified "
                   "users".format(num_test))
        cmd_opts = "--users=xpto,,fake, {0} ".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        comment = ("Test case {0} (NEW) - No entry found for specified "
                   "users".format(num_test))
        cmd_opts = "--users=xpto,,fake, {0} ".format(new_audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        startdate = "2012-09-27T13:33:47"
        enddate = "2012-09-28"

        num_test += 1
        comment = ("Test case {0} - Search entries for a specific datetime "
                   "range".format(num_test))
        cmd_opts = ("--start-date={0} --end-date={1} "
                    "{2}".format(startdate, enddate, audit_log_name))
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        startdate = "2014-03-18T11:34:30"
        enddate = "2014-03-25"

        comment = ("Test case {0} (NEW) - Search entries for a specific "
                   "datetime range".format(num_test))
        cmd_opts = ("--start-date={0} --end-date={1} "
                    "{2}".format(startdate, enddate, new_audit_log_name))
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - No entry found for specified datetime "
                   "range".format(num_test))
        cmd_opts = ("--start-date=2012-01-01 --end-date=2012-01-01T23:59:59 "
                    "{0}".format(audit_log_name))
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        comment = ("Test case {0} (NEW) - No entry found for specified "
                   "datetime range".format(num_test))
        cmd_opts = ("--start-date=2012-01-01 --end-date=2012-01-01T23:59:59 "
                    "{0}".format(new_audit_log_name))
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        pattern = '"% = ___"'

        num_test += 1
        comment = ("Test case {0} - Search entries matching SQL LIKE "
                   "pattern ".format(num_test))
        cmd_opts = "--pattern={0} {1}".format(pattern, audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        comment = ("Test case {0} (NEW) - Search entries matching SQL LIKE "
                   "pattern ".format(num_test))
        cmd_opts = "--pattern={0} {1}".format(pattern, new_audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        pattern = '".* = ..."'

        num_test += 1
        comment = ("Test case {0} - Search entries matching REGEXP "
                   "pattern ".format(num_test))
        cmd_opts = "--pattern={0} --regexp {1}".format(pattern, audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        comment = ("Test case {0} (NEW) - Search entries matching REGEXP "
                   "pattern ".format(num_test))
        cmd_opts = "--pattern={0} --regexp {1}".format(pattern,
                                                       new_audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - No entry found matching specified "
                   "pattern ".format(num_test))
        cmd_opts = '--pattern="%% = ___" --regexp {0}'.format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        comment = ("Test case {0} (NEW) - No entry found matching specified "
                   "pattern ".format(num_test))
        cmd_opts = '--pattern="%% = ___" --regexp {0}'.format(
            new_audit_log_name
        )
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        query_types = "show,SET"

        num_test += 1
        comment = ("Test case {0} - Search entries of specific query "
                   "types".format(num_test))
        cmd_opts = "--query-type={0} {1}".format(query_types, audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        comment = ("Test case {0} (NEW) - Search entries of specific query "
                   "types".format(num_test))
        cmd_opts = "--query-type={0} {1}".format(query_types,
                                                 new_audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - No entry found for specified query "
                   "types".format(num_test))
        cmd_opts = "--query-type=GRANT,REVOKE {0}".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        comment = ("Test case {0} (NEW) - No entry found for specified query "
                   "types".format(num_test))
        cmd_opts = "--query-type=GRANT,REVOKE {0}".format(new_audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        event_types = "Ping,cONNECT"

        num_test += 1
        comment = ("Test case {0} - Search entries of specific event "
                   "types".format(num_test))
        cmd_opts = "--event-type={0} {1}".format(event_types, audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        comment = ("Test case {0} (NEW) - Search entries of specific event "
                   "types".format(num_test))
        cmd_opts = "--event-type={0} {1}".format(event_types,
                                                 new_audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - No entry found for specified event "
                   "types".format(num_test))
        cmd_opts = ('--event-type="Binlog Dump,NoAudit" '
                    '{0}'.format(audit_log_name))
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        comment = ("Test case {0} (NEW) - No entry found for specified event "
                   "types".format(num_test))
        cmd_opts = ('--event-type="Binlog Dump,NoAudit" '
                    '{0}'.format(new_audit_log_name))
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        status = "1100-1199,1046"
        num_test += 1
        comment = ("Test case {0} - Search entries with specific "
                   "status".format(num_test))
        cmd_opts = "--status={0} {1}".format(status, audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        comment = ("Test case {0} (NEW) - Search entries with specific "
                   "status".format(num_test))
        cmd_opts = "--status={0} {1}".format(status, new_audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        status = ",100,500-750,50,25,999,,8000-9000,10-30,,"
        num_test += 1
        comment = ("Test case {0} - No entry found for specific "
                   "status".format(num_test))
        cmd_opts = "--status={0} {1}".format(status, audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        comment = ("Test case {0} (NEW) - No entry found for specific "
                   "status".format(num_test))
        cmd_opts = "--status={0} {1}".format(status, new_audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        users = "tester"
        startdate = "2012-10-10"
        enddate = "0"
        pattern = '".*<>.*"'
        query_types = "SELECT"
        event_types = "query"
        status = "1-9999"

        num_test += 1
        comment = "Test case {0} - Apply all search criteria".format(num_test)
        cmd_opts = ("--users={0} --start-date={1} --end-date={2} "
                    "--pattern={3} --regexp --query-type={4} --event-type={5} "
                    "--status={6} {7}".format(users, startdate, enddate,
                                              pattern, query_types,
                                              event_types, status,
                                              audit_log_name))
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        startdate = "2013-03-25"
        comment = ("Test case {0} (NEW) - Apply all search criteria"
                   "").format(num_test)
        cmd_opts = ("--users={0} --start-date={1} --end-date={2} "
                    "--pattern={3} --regexp --query-type={4} --event-type={5} "
                    "--status={6} {7}".format(users, startdate, enddate,
                                              pattern, query_types,
                                              event_types, status,
                                              new_audit_log_name))
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Test query-type false "
                   "positives".format(num_test))
        cmd_opts = "--query-type={0} {1}".format(query_types, audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        comment = ("Test case {0} (NEW) - Test query-type false "
                   "positives".format(num_test))
        cmd_opts = "--query-type={0} {1}".format(query_types,
                                                 new_audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        query_types = "COMMIT,SET,PREPARE"
        num_test += 1
        comment = ("Test case {0} - Test query-type false "
                   "positives (particular cases)".format(num_test))
        cmd_opts = "--query-type={0} {1}".format(query_types, audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        comment = ("Test case {0} (NEW) - Test query-type false "
                   "positives (particular cases)".format(num_test))
        cmd_opts = "--query-type={0} {1}".format(query_types,
                                                 new_audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Search entries of "
                   "multi-line log".format(num_test))
        audit_log_name = os.path.normpath("./std_data/multi.log")
        cmd_opts = "--format=csv --query=CREATE {0}".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        comment = ("Test case {0} (NEW) - Search entries of "
                   "multi-line log".format(num_test))
        audit_log_name = os.path.normpath("./std_data/multi_sqltext.log.xml")
        cmd_opts = "--format=csv --query=CREATE {0}".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        num_test += 1
        comment = ("Test case {0} - Search entries of "
                   "single line log".format(num_test))
        audit_log_name = os.path.normpath("./std_data/single.log")
        cmd_opts = "--format=csv --query=CREATE {0}".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        comment = ("Test case {0} (NEW) - Search entries of "
                   "single line log".format(num_test))
        audit_log_name = os.path.normpath("./std_data/single_sqltext.log.xml")
        cmd_opts = "--format=csv --query=CREATE {0}".format(audit_log_name)
        cmd = cmd_base.format(cmd_opts)
        res = self.run_test_case(0, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        self.do_replacements()

        return True

    def do_replacements(self):
        """Apply masks in the result.
        """
        server_id = self.server1.show_server_variable('server_id')[0][1]
        audit_log = self.server1.show_server_variable('audit_log_file')[0][1]
        self.replace_result("          File: " + audit_log,
                            "          File: audit.log\n")
        self.replace_result("          Size:", "          Size: ...\n")
        self.replace_result("       Created:", "       Created: ...\n")
        self.replace_result(" Last Modified:", " Last Modified: ...\n")
        self.replace_result("       SERVER_ID: " + server_id,
                            "       SERVER_ID: <SERVER_ID>\n")
        self.replace_result(" STARTUP_OPTIONS:", " STARTUP_OPTIONS: ...\n")
        self.replace_result("       TIMESTAMP:", "       TIMESTAMP: ...\n")
        self.replace_result("   MYSQL_VERSION:", "   MYSQL_VERSION: ...\n")
        self.replace_result("      OS_VERSION:", "      OS_VERSION: ...\n")
        self.replace_result("         VERSION:", "         VERSION: ...\n")

        # Remove version information
        self.remove_result_and_lines_after("MySQL Utilities mysqlauditgrep "
                                           "version", 6)

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return True
