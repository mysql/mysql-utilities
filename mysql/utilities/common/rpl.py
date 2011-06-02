#
# Copyright (c) 2010, Oracle and/or its affiliates. All rights reserved.
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
This module contains abstractions of MySQL replication functionality.
"""

#import datetime
#import optparse
#import os
import re
import time
from mysql.utilities.exception import MySQLUtilError
from mysql.utilities.common.user import User

# List of database objects for enumeration
DATABASE, TABLE, VIEW, TRIGGER, PROC, FUNC, EVENT, GRANT = "DATABASE", \
    "TABLE", "VIEW", "TRIGGER", "PROCEDURE", "FUNCTION", "EVENT", "GRANT"

class Rpl(object):
    """
    The Rpl class can be used to establish a replication connection between
    a master and a slave with the following utilities:

        - Setup replication between master and slave
        - Test the replication topology
    """   
    
    def __init__(self, master, slave, verbose=False):
        """Constructor
        
        master[in]         Master Server object
        slave[in]          Slave Server object
        verbose[in]        print extra data during operations (optional)
                           default value = False
        """
        self.verbose = verbose
        self.master = master
        self.slave = slave


    def check_master(self):
        """Check prerequisites for master for replication
        
        Returns True if master ok, False if no binary logging turned on.
        """
        
        res = self.master.show_server_variable("log_bin")
        if not res:
            print "ERROR: Cannot retrieve status of log_bin variable."
            return False
        log_bin = res[0][1]
        if log_bin == "OFF" or log_bin == "0":
            return False
        return True
        
    def replicate(self, rpl_user, num_tries):
        """Setup replication among a slave and master.
        
        Note: Must have connected to a master and slave before calling this
        method.

        rpl_user[in]       Replication user in form user:passwd
        num_tries[in]      Number of attempts to wait for slave synch
        
        Returns True if success, False if error
        """
        
        if self.master is None or self.slave is None:
            print "ERROR: Must connect to master and slave before " \
                  "calling replicate()"
            return False
        
        self.replicating = False
        result = True
        
        # Create user class instance
        user_str = "%s@%s:%s" % (rpl_user, self.master.host, self.master.port)
        user = User(self.master, user_str, self.verbose)

        m_obj = re.match("(\w+)(?:\:(\w+))?", rpl_user)
        r_user, r_pass = m_obj.groups()
        
        # Check to see if rpl_user is present, else create her
        if not user.exists():
            if self.verbose:
                print "# Creating replication user..."
            user.create()
        
        # Check to see if rpl_user has the correct grants, else grant rights
        if not user.has_privilege("*", "*", "REPLICATION SLAVE"):
            if self.verbose:
                print "# Granting replication access to replication user..."
            query_str = "GRANT REPLICATION SLAVE ON *.* TO '%s'@'%s' " % \
                        (r_user, self.slave.host)
            if r_pass:
                query_str += "IDENTIFIED BY '%s'" % r_pass
            try:
                self.master.exec_query(query_str, (), False, False)
            except:
                print "ERROR: Cannot grant replication slave to " + \
                      "replication user."
                return False

        # Flush tables on master
        if self.verbose:
            print "# Flushing tables on master with read lock..."
        query_str = "FLUSH TABLES WITH READ LOCK"
        res = self.master.exec_query(query_str, (), False, False)
        
        # Read master log file information
        res = self.master.exec_query("SHOW MASTER STATUS")
        if not res:
            print "ERROR: Cannot retrieve master status."
            exit(1)
            
        master_file = res[0][0]
        master_pos = res[0][1]
         
        # Stop slave first
        res = self.slave.exec_query("SHOW SLAVE STATUS")
        if res != () and res != []:
            if res[0][10] == "Yes" or res[0][11] == "Yes":
                res = self.slave.exec_query("STOP SLAVE", (), False, False)
        
        # Connect slave to master
        if self.verbose:
            print "# Connecting slave to master..."
        change_master = "CHANGE MASTER TO MASTER_HOST = '%s', " % \
                        self.master.host
        change_master += "MASTER_USER = '%s', " % r_user
        change_master += "MASTER_PASSWORD = '%s', " % r_pass
        change_master += "MASTER_PORT = %s, " % self.master.port
        change_master += "MASTER_LOG_FILE = '%s', " % master_file
        change_master += "MASTER_LOG_POS = %s" % master_pos
        res = self.slave.exec_query(change_master, (), False, False)
        if self.verbose:
            print "# %s" % change_master
        
        # Start slave
        if self.verbose:
            print "# Starting slave..."
        res = self.slave.exec_query("START SLAVE", (), False, False)
        
        # Check slave status
        i = 0
        while i < num_tries:
            time.sleep(1)
            res = self.slave.exec_query("SHOW SLAVE STATUS")
            status = res[0][0]
            if self.verbose:
                print "# status: %s" % status
                print "# error: %s:%s" % (res[0][34], res[0][35])
            if status == "Waiting for master to send event":
                break;
            if self.verbose:
                print "# Waiting for slave to synchronize with master"
            i += 1
        if i == num_tries:
            print "ERROR: failed to synch slave with master."
            result = False
            
        # unlock tables on master
        if self.verbose:
            print "# Unlocking tables on master..."
        query_str = "UNLOCK TABLES"
        res = self.master.exec_query(query_str, (), False, False)
        if result is True:
            self.replicating = True
        return result

        
    def test(self, db, num_tries):
        """Test the replication setup.

        Requires a database name which is created on the master then
        verified it appears on the slave.
        
        db[in]             Name of a database to use in test
        num_tries[in]      Number of attempts to wait for slave synch
        """
        
        if not self.replicating:
            print "ERROR: Replication is not running among master and slave."
        print "# Testing replication setup..."
        if self.verbose:
            print "# Creating a test database on master named %s..." % db
        res = self.master.exec_query("CREATE DATABASE %s" % db,
                                     (), False, False)
        i = 0
        while i < num_tries:
            time.sleep (1)
            res = self.slave.exec_query("SHOW DATABASES")
            for row in res:
                if row[0] == db:
                    res = self.master.exec_query("DROP DATABASE %s" % db,
                                                 (), False, False)
                    print "# Success! Replication is running."
                    i = num_tries
                    break
            i += 1
            if i < num_tries and self.verbose:
                print "# Waiting for slave to synchronize with master"
        if i == num_tries:
            print "ERROR: Unable to complete testing."
        

