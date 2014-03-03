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

import os

import mutlib

from mysql.utilities.exception import MUTLibError


class test(mutlib.System_test):
    """Test multi-source replication daemon utility.

    This test exercises the multi-source replication daemon utility known
    error conditions.

    Note: this test requires a POSIX system and GTID enabled servers.
    """

    def check_prerequisites(self):
        if os.name != "posix":
            raise MUTLibError("Test requires a POSIX system.")
        return True

    def setup(self):
        self.res_fname = "result.txt"
        # No need to spawn any server.
        return True

    def run(self):
        self.res_fname = "result.txt"

        slave_conn = "user@slave_host:3306"
        master1_conn = "user@master1_host:3306"
        master2_conn = "user@master2_host:3306"

        test_num = 1
        comment = ("Test case {0} - Missing --log when using --daemon"
                   "".format(test_num))
        cmd_str = "mysqlrplms.py --daemon=start {0}"
        cmd_opts = (
            "--slave={0}".format(slave_conn),
            "--masters={0}".format(",".join([master1_conn, master2_conn])),
        )
        res = self.run_test_case(
            2, cmd_str.format(" ".join(cmd_opts)), comment
        )
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - Missing --daemon when using --pidfile"
                   "".format(test_num))
        cmd_str = "mysqlrplms.py --pidfile=rplms_daemon.pid {0}"
        res = self.run_test_case(
            2, cmd_str.format(" ".join(cmd_opts)), comment
        )
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - Pidfile does not exist".format(test_num)
        cmd_str = ("mysqlrplms.py --daemon=stop --log=rplms_daemon.log "
                   "--pidfile=nonexistent.pid {0}")
        res = self.run_test_case(
            2, cmd_str.format(" ".join(cmd_opts)), comment
        )
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        pidfile = os.path.realpath(os.path.normpath("nonexistent.pid"))
        self.mask_result_portion("mysqlrplms: error: pidfile ", pidfile,
                                 " does not exist.", "######")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
                if os.path.exists("rplms_daemon.log"):
                    os.unlink("rplms_daemon.log")
            except OSError:
                pass
        return True
