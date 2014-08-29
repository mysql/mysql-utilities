#
# Copyright (c) 2014, Oracle and/or its affiliates. All rights reserved.
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

import audit_log_admin

from mysql.utilities.exception import MUTLibError


class test(audit_log_admin.test):
    """Audit log maintenance utility tests for older server versions.

    This test runs the mysqlauditadmin utility to test its features for older
    MySQL server versions. Requires a server with the audit log plug-in
    enabled and a version < 5.5.40, or >= 5.6.0 and < 5.6.21, or >= 5.7.0 and
    < 5.7.5.
    """

    def check_prerequisites(self):
        # First, make sure the server to be clone has the audit log included.
        srv = self.servers.get_server(0)
        if not srv.supports_plugin("audit"):
            raise MUTLibError("Test requires a server with the audit log "
                              "plug-in installed and enabled.")

        # Check the server version.
        if ((srv.check_version_compat(5, 5, 40) and  # >= 5.5.40 and < 5.6
             not srv.check_version_compat(5, 6, 0)) or
            (srv.check_version_compat(5, 6, 21) and  # >= 5.6.21 and < 5.7
             not srv.check_version_compat(5, 7, 0)) or
                srv.check_version_compat(5, 7, 5)):  # >= 5.7.5
            raise MUTLibError("Test requires a server with version < 5.5.40, "
                              "or >= 5.6.0 and < 5.6.21, or >= 5.7.0 and "
                              "< 5.7.5.")
        return self.check_num_servers(1)

    def run(self):
        """Run test cases.
        """
        # Run all test cases from the parent class audit_log_admin.test.
        return super(test, self).run()

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)
