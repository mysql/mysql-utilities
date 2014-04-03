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
replicate_ms_privileges test.
"""

import os
import time

import replicate_ms

from mysql.utilities.exception import MUTLibError, UtilError


_RPLMS_LOG = "{0}rplms_log.txt"
_TIMEOUT = 30
_RPLMS_MISSING_PRIV_PHRASE = ("does not have sufficient privileges to perform "
                              "replication")


class test(replicate_ms.test):
    """Test multi-source replication daemon checker privileges.

    This test verify the privileges required by servers to execute the
    multi-source utility.

    Note: Test extend the replicate_ms test and it has the same prerequisites.
    """

    log_range = range(1, 3)

    def setup(self):
        res = super(test, self).setup()
        if not res:
            return res

        # Drop users
        self.drop_users()

        # Create users
        try:
            self.server1.exec_query("CREATE USER 'rpltest'@'localhost'")
            self.server2.exec_query("CREATE USER 'rpltest'@'localhost'")
            self.server3.exec_query("CREATE USER 'rpltest'@'localhost'")
        except UtilError:
            raise MUTLibError("Failed create users.")

        return True

    def test_rplms_missing_privileges(self, cmd, logfile, comment):
        """Test multi-source replication for missing privileges.

        cmd[in]           Command to be executed.
        logfile[in]       Log filename.
        comment[in]       Test comment.
        kill_process[in]  True if the process is to be killed.
        stop_phrase[in]   Stop phrase to be searched in the log.

        This method create a process by executing the command and try to find
        the stop phrase.
        """
        # Since this test case expects the process to stop, we can launch it
        # via a subprocess and wait for it to finish.
        if self.debug:
            print(comment)
            print("# COMMAND: {0}".format(cmd))

        # Run command
        proc, f_out = self.start_process(cmd)

        # Wait for process to load
        if self.debug:
            print("# Waiting for process to start.")
        i = 1
        time.sleep(1)
        while proc.poll() is not None:
            time.sleep(1)
            i += 1
            if i > _TIMEOUT:
                if self.debug:
                    print("# Timeout process to start.")
                # Do not raise error, we need to test if the stop_phrase is
                # present in the log.
                break

        # Wait for logfile file to be created
        if self.debug:
            print("# Waiting for logfile to be created.")
        for i in range(_TIMEOUT):
            if os.path.exists(logfile):
                break
            else:
                time.sleep(1)
        else:
            raise MUTLibError("{0}: failed - timeout waiting for "
                              "logfile '{1}' to be "
                              "created.".format(comment, logfile))

        # Find stop phrase
        stop_phrase_found = False
        try:
            self.find_stop_phrase(logfile, comment, _RPLMS_MISSING_PRIV_PHRASE)
            stop_phrase_found = True
        except MUTLibError:
            pass

        # Cleanup after test case
        try:
            # If not stop_phrase_found the process is still running
            if not stop_phrase_found:
                self.kill_process(proc, f_out, comment)
            os.unlink(logfile)
        except OSError:
            pass

        return stop_phrase_found

    def run(self):
        slave_str = "--slave=rpltest@localhost:{0}".format(self.server1.port)
        masters_str = "--masters={0}".format(
            ",".join(["rpltest@localhost:{0}".format(self.server2.port),
                      "rpltest@localhost:{0}".format(self.server3.port)])
        )

        test_num = 1
        rplms_cmd = ("python ../scripts/mysqlrplms.py --log={0} --interval=5 "
                     "--switchover-interval=30 {1} {2}"
                     "".format(_RPLMS_LOG.format(test_num), slave_str,
                               masters_str))
        comment = ("Test case {0} - User does not have the privileges needed "
                   "for replication".format(test_num))
        res = self.test_rplms_missing_privileges(rplms_cmd,
                                                 _RPLMS_LOG.format(test_num),
                                                 comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Drop all
        self.drop_all()

        # Reset topology
        self.reset_ms_topology()

        # Create data
        self.create_all()

        # Grant privileges
        self.grant_privileges("'rpltest'@'localhost'")

        test_num += 1
        rplms_cmd = ("python ../scripts/mysqlrplms.py --log={0} --interval=5 "
                     "--switchover-interval=30 {1} {2}"
                     "".format(_RPLMS_LOG.format(test_num), slave_str,
                               masters_str))
        comment = ("Test case {0} - User does have the privileges needed for "
                   "replication".format(test_num))
        self.test_rplms(rplms_cmd, _RPLMS_LOG.format(test_num), comment, True)
        return True

    def grant_privileges(self, user):
        """Grant privileges needed for replication.

        user[in]    MySQL user
        """
        base_grants_query = ("GRANT SELECT, INSERT, UPDATE, PROCESS, "
                             "REPLICATION SLAVE, REPLICATION CLIENT, "
                             "CREATE USER ON *.* TO {0}".format(user))
        super_grant_query = ("GRANT SUPER ON *.* TO {0} WITH GRANT OPTION"
                             "".format(user))

        try:
            self.server1.exec_query(base_grants_query)
            self.server1.exec_query(super_grant_query)
            self.server2.exec_query(base_grants_query)
            self.server2.exec_query(super_grant_query)
            self.server3.exec_query(base_grants_query)
            self.server3.exec_query(super_grant_query)
        except UtilError:
            raise MUTLibError("Failed grant privileges.")

    def drop_users(self):
        """Drops all users created.
        """
        try:
            self.server1.exec_query("DROP USER 'rpltest'@'localhost'")
        except UtilError:
            pass
        try:
            self.server2.exec_query("DROP USER 'rpltest'@'localhost'")
        except UtilError:
            pass
        try:
            self.server3.exec_query("DROP USER 'rpltest'@'localhost'")
        except UtilError:
            pass

    def cleanup(self):
        self.drop_users()
        return super(test, self).cleanup()
