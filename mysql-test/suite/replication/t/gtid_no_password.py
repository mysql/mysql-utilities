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
import failover
import time
from mysql.utilities.exception import MUTLibError

_DEFAULT_MYSQL_OPTS = '"--log-bin=mysql-bin --skip-slave-start ' + \
                      '--log-slave-updates --gtid-mode=on ' + \
                      '--enforce-gtid-consistency --report-host=localhost ' + \
                      '--report-port=%s "'

_TIMEOUT = 30

class test(failover.test):
    """test replication failover utility
    This test exercises the mysqlfailover utility on slaves without passwords.
    """

    def check_prerequisites(self):
        if not self.servers.get_server(0).check_version_compat(5, 6, 5):
            raise MUTLibError("Test requires server version prior to 5.6.5")
        return self.check_num_servers(1)
    
    def _get_server(self, role, mysqld):
        if self.debug:
            print "# Spawning %s" % role
        index = self.servers.find_server_by_name(role)
        if index >= 0:
            if self.debug:
                print "# Found it in the servers list."
            server = self.servers.get_server(index)
            try:
                res = server.show_server_variable("server_id")
            except MUTLibError, e:
                raise MUTLibError("Cannot get replication server "
                                   "server_id: %s" % e.errmsg)
        else:
            if self.debug:
                print "# Cloning server0."
            serverid = self.servers.get_next_id()
            port = int(self.servers.get_next_port())
            if mysqld is None:
                mysqld = _DEFAULT_MYSQL_OPTS % port
            res = self.servers.start_new_server(self.server0, port, serverid,
                                                "", role, mysqld)
            if not res:
                raise MUTLibError("Cannot spawn replication server '%s'." %
                                  role)
            self.servers.add_new_server(res[0], True)
            server = res[0]

        return server

    def _poll_console(self, start, name, proc, comment):
        msg = "Timeout waiting for console %s to %s." % (name,
              "start." if start else "end.")
        if self.debug:
            print '#', msg
        elapsed = 0
        delay = 1
        done = False
        while not done:
            if start:
                done = proc.poll() is None
            else:
                done = proc.poll() is not None
            time.sleep(delay)
            elapsed += delay
            if elapsed >= _TIMEOUT:
                if self.debug:
                    print "#", msg
                raise MUTLibError(comment + ":" + msg)

    def setup(self):
        self.res_fname = "result.txt"
        
        # Spawn servers
        self.server0 = self.servers.get_server(0)
        mysqld = _DEFAULT_MYSQL_OPTS % self.servers.view_next_port()
        self.server1 = self._get_server("rep_master_no_pass", mysqld)
        mysqld = _DEFAULT_MYSQL_OPTS % self.servers.view_next_port()
        self.server2 = self._get_server("rep_slave1_no_pass", mysqld)

        self.master_str = "--master=%s" % \
                          self.build_connection_string(self.server1)
        slave_str = " --slave=%s" % self.build_connection_string(self.server2)
        conn_str = self.master_str + slave_str
        cmd = "mysqlreplicate.py --rpl-user=rpl:rpl %s" % conn_str
        res = self.exec_util(cmd, self.res_fname)
        if res != 0:
            return False

        return True
    
    def run(self):
        import subprocess
        
        comment = "Test case 1 - No password test"
        cmd_str = "mysqlrpladmin.py health %s %s" % (self.master_str, 
                  " --discover-slaves-login=root")
        
        res = self.exec_util(cmd_str, self.res_fname)
        if res != 0:
            return False

        # Test should show one master and one slave.
        self.results = []
        file_out = open(self.res_fname, 'r')
        for line in file_out.readlines():
            # Save only the report.
            if line[0] in ('+', '|'):
                self.results.append(line)
        file_out.close()

        self.replace_substring(str(self.server1.port), "PORT1")
        self.replace_substring(str(self.server2.port), "PORT2")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except:
                pass
        return True

