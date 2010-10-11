#!/usr/bin/env python
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#

"""
This file contains the replicate utility. It is used to establish a
master/slave replication topology among two servers.
"""

import re
import sys
import MySQLdb
from mysql.utilities.common import MySQLUtilError

def replicate(master_vals, slave_vals, rpl_user,
              test_db=None, verbose=False):
    """Setup replication among a master and a slave.
    
    master_vals[in]    Master connection in form user:passwd@host:port:sock
    slave_vals[in]     Slave connection in form user:passwd@host:port:sock
    rpl_user[in]       Replication user in the form user:passwd
    test_db[in]        If True, test replication using this database name
                       optional - default = False
    verbose[in]        If True, turn on additional information messages
                       optional - default = False
    """
    
    from mysql.utilities.common import connect_servers
    from mysql.utilities.common import Rpl
    from mysql.utilities.common import Server

    # Fail if master and slave are using the same connection parameters.
    dupes = False
    if "unix_socket" in slave_vals and "unix_socket" in master_vals:
        dupes = (slave_vals["unix_socket"] == master_vals["unix_socket"])
    else:
        dupes = (slave_vals["port"] == master_vals["port"]) 
    if dupes:
        raise MySQLUtilError("You must specify two different servers for "
                             "the operation.")

    try:
        servers = connect_servers(master_vals, slave_vals, False, "5.0.0",
                                  "master", "slave")
    except MySQLUtilError, e:
        raise e
    
    master = servers[0]
    slave = servers[1]

    # Get server_id from Master
    try:
        res = master.show_server_variable("server_id")
    except MySQLUtilError, e:
        raise MySQLUtilError("Cannot retrieve server id from master.")
    
    master_server_id = int(res[0][1])
        
    if master_server_id == 0:
        raise MySQLUtilError("Master server_id is set to 0.")
    
    # Get server_id from Slave
    try:
        res = slave.show_server_variable("server_id")
    except MySQLUtilError, e:
        raise MySQLUtilError("Cannot retrieve server id from slave.")
        
    slave_server_id = int(res[0][1])
    
    if slave_server_id == 0:
        raise MySQLUtilError("Slave server_id is set to 0.")
    
    # Check for uniqueness
    if master_server_id == slave_server_id:
        raise MySQLUtilError("The slave's server_id is the same as the "
                             "master. Please set the server_id on the slave "
                             "then retry command.") 
    
    if verbose:
        print "# master id = %s" % master_server_id
        print "#  slave id = %s" % slave_server_id

    # Create an instance of the replication object
    rpl = Rpl(master, slave, verbose)
    
    # Check master for binary logging
    print "# Checking for binary logging on master..."
    if not rpl.check_master():
        raise MySQLUtilError("Master must have binary logging turned on.")
        
    # Setup replication
    print "# Setting up replication..."
    if not rpl.replicate(rpl_user, 10):
        raise MySQLUtilError("Cannot setup replication.")
        
    # Test the replication setup.
    if test_db:
        rpl.test(test_db, 10)
        
    print "# ...done."

