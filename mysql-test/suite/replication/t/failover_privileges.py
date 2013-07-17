#
# Copyright (c) 2013, Oracle and/or its affiliates. All rights reserved.
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

import failover

from mysql.utilities.exception import MUTLibError


class test(failover.test):
    """Test failover privileges
    This test verify the privileges required by servers to execute the
    mysqlfailover utility. Note: It extends the failover test.
    """

    def check_prerequisites(self):
        # Use the same requisites as failover test case.
        return failover.test.check_prerequisites(self)

    def setup(self):
        self.temp_files = []
        self.test_results = []
        self.test_cases = []
        self.res_fname = "result.txt"
        res = failover.test.setup(self)
        if not res:
            return False

        # Range used for log filename (one for each test).
        self.log_range = range(1, 8)

        # Create replication user and grant REPLICATION SLAVE privilege.
        grants = ['REPLICATION SLAVE']
        for slave in [self.server2, self.server3, self.server4]:
            self.change_user_privileges(slave, 'repl', 'repl',
                                        self.server1.host,
                                        grant_list=grants, revoke_list=None,
                                        disable_binlog=True, create_user=True)

        # Configure the replication topology for the new user.
        self.reset_topology(rpl_user='repl', rpl_passwd='repl')

        return True

    def change_user_privileges(self, server, user_name, user_passwd, host,
                               grant_list=None, revoke_list=None,
                               disable_binlog=False, create_user=False):
        """ Change the privileges of a new or existing user.

        This method GRANT or REVOKE privileges to a new user (creating it) or
        existing user.

        server[in]          MySQL server instances to apply changes.
        user_name[in]       user name to apply changes.
        user_passwd[in]     user's password.
        host[in]            host name associated to the user account.
        grant_list[in]      List of privileges to GRANT.
        revoke_list[in]     List of privileges to REVOKE.
        disable_binlog[in]  Boolean value to determine if the binary logging
                            will be disabled to perform this operation (and
                            re-enabled at the end). By default: False (do not
                            disable binary logging).
        create_user[in]     Boolean value to determine if the user will be
                            created before changing its privileges. By default:
                            False (do no create user).
        """
        if disable_binlog:
            server.exec_query("SET SQL_LOG_BIN=0")
        if create_user:
            server.exec_query("CREATE USER '{0}'@'{1}' IDENTIFIED BY "
                              "'{2}'".format(user_name, host, user_passwd))
        if grant_list:
            grants_str = ", ".join(grant_list)
            server.exec_query("GRANT {0} ON *.* TO '{1}'@'{2}' IDENTIFIED BY "
                              "'{3}'".format(grants_str, user_name, host,
                                             user_passwd))
        if revoke_list:
            revoke_str = ", ".join(revoke_list)
            server.exec_query("REVOKE {0} ON *.* FROM '{1}'@'{2}'"
                              "".format(revoke_str, user_name, host))
        if disable_binlog:
            server.exec_query("SET SQL_LOG_BIN=1")

    def run(self):
        # Create connection strings.
        master_conn = self.build_connection_string(self.server1).strip(' ')
        slave1_conn = self.build_connection_string(self.server2).strip(' ')
        slave2_conn = self.build_connection_string(self.server3).strip(' ')
        slave3_conn = self.build_connection_string(self.server4).strip(' ')

        # Use 'repl' user for all slaves.
        slaves_str = ",".join([slave1_conn, slave2_conn, slave3_conn])
        slaves_str = slaves_str.replace('root', 'repl')

        base_cmd = (
            '{0}mysqlfailover.py --interval=10 --timeout=5 '
            '--master={1} --slaves={2} --discover-slaves-login=repl:repl '
            '--failover-mode={3} --exec-post-failover="{4}" --log={5}'
        )

        # Test failover using a user with missing privileges.
        # Only: REPLICATION SLAVE.
        # This privilege is mandatory for slaves to connect to the master.
        test_num = 1
        comment = ("Test case {0} - failover (fail) using 'repl' only with: "
                   "REPLICATION SLAVE.").format(test_num)
        log_file = failover._FAILOVER_LOG.format(test_num)
        cmd = base_cmd.format('', master_conn, slaves_str, 'auto',
                              self.fail_event_script, log_file)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Grant all required privileges except SUPER to user on slaves.
        grants = ['GRANT OPTION', 'SELECT', 'RELOAD', 'DROP', 'CREATE']
        for slave in [self.server2, self.server3, self.server4]:
            self.change_user_privileges(slave, 'repl', 'repl',
                                        self.server1.host,
                                        grant_list=grants, revoke_list=None,
                                        disable_binlog=True, create_user=False)

        # Test failover using a user with missing privilege: SUPER.
        test_num += 1
        comment = ("Test case {0} - failover (fail) using 'repl' without: "
                   "SUPER.").format(test_num)
        log_file = failover._FAILOVER_LOG.format(test_num)
        cmd = base_cmd.format('', master_conn, slaves_str, 'auto',
                              self.fail_event_script, log_file)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Grant all required privileges except DROP to user on slaves.
        grants = ['SUPER']
        revokes = ['DROP']
        for slave in [self.server2, self.server3, self.server4]:
            self.change_user_privileges(slave, 'repl', 'repl',
                                        self.server1.host,
                                        grant_list=grants, revoke_list=revokes,
                                        disable_binlog=True, create_user=False)

        # Test failover using a user with missing privilege: DROP.
        test_num += 1
        comment = ("Test case {0} - failover (fail) using 'repl' without: "
                   "DROP.").format(test_num)
        log_file = failover._FAILOVER_LOG.format(test_num)
        cmd = base_cmd.format('', master_conn, slaves_str, 'auto',
                              self.fail_event_script, log_file)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Grant all required privileges except CREATE to user on slaves.
        grants = ['DROP']
        revokes = ['CREATE']
        for slave in [self.server2, self.server3, self.server4]:
            self.change_user_privileges(slave, 'repl', 'repl',
                                        self.server1.host,
                                        grant_list=grants, revoke_list=revokes,
                                        disable_binlog=True, create_user=False)

        # Test failover using a user with missing privilege: CREATE.
        test_num += 1
        comment = ("Test case {0} - failover (fail) using 'repl' without: "
                   "CREATE.").format(test_num)
        log_file = failover._FAILOVER_LOG.format(test_num)
        cmd = base_cmd.format('', master_conn, slaves_str, 'auto',
                              self.fail_event_script, log_file)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Grant all required privileges except GRANT OPTION to user on slaves.
        grants = ['CREATE']
        revokes = ['GRANT OPTION']
        for slave in [self.server2, self.server3, self.server4]:
            self.change_user_privileges(slave, 'repl', 'repl',
                                        self.server1.host,
                                        grant_list=grants, revoke_list=revokes,
                                        disable_binlog=True, create_user=False)

        # Test failover using a user with missing privilege: GRANT OPTION.
        test_num += 1
        comment = ("Test case {0} - failover (fail) using 'repl' without: "
                   "GRANT OPTION.").format(test_num)
        log_file = failover._FAILOVER_LOG.format(test_num)
        cmd = base_cmd.format('', master_conn, slaves_str, 'auto',
                              self.fail_event_script, log_file)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Grant all required privileges except SELECT to user on slaves.
        grants = ['GRANT OPTION']
        revokes = ['SELECT']
        for slave in [self.server2, self.server3, self.server4]:
            self.change_user_privileges(slave, 'repl', 'repl',
                                        self.server1.host,
                                        grant_list=grants, revoke_list=revokes,
                                        disable_binlog=True, create_user=False)

        # Test failover using a user with missing privilege: SELECT.
        test_num += 1
        comment = ("Test case {0} - failover (fail) using 'repl' without: "
                   "SELECT.").format(test_num)
        log_file = failover._FAILOVER_LOG.format(test_num)
        cmd = base_cmd.format('', master_conn, slaves_str, 'auto',
                              self.fail_event_script, log_file)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Grant all required privileges except RELOAD to user on slaves.
        grants = ['SELECT']
        revokes = ['RELOAD']
        for slave in [self.server2, self.server3, self.server4]:
            self.change_user_privileges(slave, 'repl', 'repl',
                                        self.server1.host,
                                        grant_list=grants, revoke_list=revokes,
                                        disable_binlog=True, create_user=False)

        # Test failover using a user with missing privilege: RELOAD.
        test_num += 1
        comment = ("Test case {0} - failover (fail) using 'repl' without: "
                   "RELOAD.").format(test_num)
        log_file = failover._FAILOVER_LOG.format(test_num)
        cmd = base_cmd.format('', master_conn, slaves_str, 'auto',
                              self.fail_event_script, log_file)
        res = self.run_test_case(1, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        # Grant all required privileges to user on slaves.
        grants = ['RELOAD']
        for slave in [self.server2, self.server3, self.server4]:
            self.change_user_privileges(slave, 'repl', 'repl',
                                        self.server1.host,
                                        grant_list=grants, revoke_list=None,
                                        disable_binlog=True, create_user=False)

        # Apply masks.
        self.do_masks()
        self.replace_substring(" (42000)", "")

        # Test failover using a user with all required privileges:
        # REPLICATION SLAVE, SUPER, GRANT OPTION, SELECT, RELOAD.
        test_num += 1
        comment = ("Test case {0} - failover (succeed) using 'repl' with: "
                   "REPLICATION SLAVE, SUPER, GRANT OPTION, SELECT, RELOAD."
                   "").format(test_num)
        log_file = failover._FAILOVER_LOG.format(test_num)
        key_phrase = "Failover complete"
        cmd = base_cmd.format('python ../scripts/', master_conn, slaves_str,
                              'auto', self.fail_event_script, log_file)
        test_case = (self.server1, cmd, True, log_file, comment, key_phrase,
                     False)
        res = self.test_failover_console(test_case)
        if res:
            self.test_results.append(res)
        else:
            raise MUTLibError("{0}: failed".format(test_case[4]))

        self.remove_result("NOTE: Log file")

        return True

    def get_result(self):
        # Get output comparison results
        comp_res = self.compare(__name__, self.results)

        # Get failover execution results
        fail_res = failover.test.get_result(self)

        # Combine comparison and failover results
        res_value = comp_res[0] and fail_res[0]
        if comp_res[1]:
            res_msg = comp_res[1]
            res_msg.append(fail_res[1])
        else:
            res_msg = fail_res[1]
        return res_value, res_msg

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        # Kill all remaining servers (to avoid problems for other tests).
        self.kill_server('rep_slave1_gtid')
        self.kill_server('rep_slave2_gtid')

        # Perform the same cleanup as the failover test case.
        return failover.test.cleanup(self)
