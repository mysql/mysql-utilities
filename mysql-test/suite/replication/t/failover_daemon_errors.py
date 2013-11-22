#
# Copyright (c) 2013 Oracle and/or its affiliates. All rights reserved.
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

import rpl_admin_gtid

from mysql.utilities.exception import MUTLibError


class test(rpl_admin_gtid.test):
    """Test replication failover daemon utility
    This test exercises the mysqlfailover daemon utility known error
    conditions.
    Note: this test requires a POSIX system and GTID enabled servers.
    """

    def check_prerequisites(self):
        if os.name != "posix":
            raise MUTLibError("Test requires a POSIX system.")
        return super(test, self).check_prerequisites()

    def setup(self):
        return super(test, self).setup()

    def run(self):
        self.res_fname = "result.txt"

        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')

        i = 1
        comment = "Test case {0} - Missing --log when using --daemon".format(i)
        cmd_str = "mysqlfailover.py --daemon=start {0}"
        cmd_opts = (
            "--master={0}".format(master_conn),
            "--slaves={0}".format(",".join([slave1_conn, slave2_conn])),
        )
        res = self.run_test_case(
            2, cmd_str.format(" ".join(cmd_opts)), comment
        )
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        i += 1
        comment = ("Test case {0} - Missing --daemon when using --pidfile"
                   "".format(i))
        cmd_str = "mysqlfailover.py --pidfile=failover.pid {0}"
        res = self.run_test_case(
            2, cmd_str.format(" ".join(cmd_opts)), comment
        )
        if not res:
                raise MUTLibError("{0}: failed".format(comment))

        i += 1
        comment = "Test case {0} - Invalid --report-values value".format(i)
        cmd_str = ("mysqlfailover.py --daemon=start --log=failover.log "
                   "--report-values=unknown {0}")
        res = self.run_test_case(
            2, cmd_str.format(" ".join(cmd_opts)), comment
        )
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        i += 1
        comment = "Test case {0} - Pidfile does not exist".format(i)
        cmd_str = ("mysqlfailover.py --daemon=stop --log=failover.log "
                   "--pidfile=nonexistent.pid {0}")
        res = self.run_test_case(
            2, cmd_str.format(" ".join(cmd_opts)), comment
        )
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        pidfile = os.path.realpath(os.path.normpath("nonexistent.pid"))
        self.mask_result_portion("mysqlfailover.py: error: pidfile ", pidfile,
                                 " does not exist.", "######")
        self.remove_result("NOTE: Log file")

        self.reset_topology()

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink("failover.log")
            except OSError:
                pass
        return super(test, self).cleanup()
