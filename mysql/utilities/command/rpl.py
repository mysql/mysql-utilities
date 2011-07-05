#!/usr/bin/env python
#
# Copyright (c) 2010, 2011 Oracle and/or its affiliates. All rights reserved.
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
This file contains the replicate utility. It is used to establish a
master/slave replication topology among two servers.
"""

import sys
from mysql.utilities.exception import MySQLUtilError

def replicate(master_vals, slave_vals, rpl_user,
              options, test_db=None):
    """Setup replication among a master and a slave.
    
    master_vals[in]    Master connection in form user:passwd@host:port:sock
    slave_vals[in]     Slave connection in form user:passwd@host:port:sock
    rpl_user[in]       Replication user in the form user:passwd
    options[in]        dictionary of options (verbosity, quiet, pedantic)
    test_db[in]        Test replication using this database name (optional)
                       default = None
    """
    
    from mysql.utilities.common.server import connect_servers
    from mysql.utilities.common.rpl import Replication
    
    verbosity = options.get("verbosity", 0)

    conn_options = {
        'src_name'  : "master",
        'dest_name' : 'slave',
        'version'   : "5.0.0",
        'unique'    : True,
    }
    servers = connect_servers(master_vals, slave_vals, conn_options)
    master = servers[0]
    slave = servers[1]
    
    # Create an instance of the replication object
    rpl = Replication(master, slave, verbosity > 0)
    errors = rpl.check_server_ids()
    for error in errors:
        print error
            
    # Check for server_id uniqueness
    if verbosity > 0:
        print "# master id = %s" % rpl.master_server_id
        print "#  slave id = %s" % rpl.slave_server_id
    
    # Check InnoDB compatibility
    if verbosity > 0:
        print "# Checking InnoDB statistics for type and version conflicts."

    errors = rpl.check_innodb_compatibility(options)
    for error in errors:
        print error
    
    # Checking storage engines                
    if verbosity > 0:
        print "# Checking storage engines..."
        
    errors = rpl.check_storage_engines(options)
    for error in errors:
        print error
            
    # Check master for binary logging
    print "# Checking for binary logging on master..."
    errors = rpl.check_master_binlog()
    if not errors == []:
        raise MySQLUtilError(errors[0])
        
    # Setup replication
    print "# Setting up replication..."
    if not rpl.replicate(rpl_user, 10):
        raise MySQLUtilError("Cannot setup replication.")
        
    # Test the replication setup.
    if test_db:
        rpl.test(test_db, 10)
        
    print "# ...done."


def check_replication(master_vals, slave_vals, options):
    """Check replication among a master and a slave.
    
    master_vals[in]    Master connection in form user:passwd@host:port:sock
    slave_vals[in]     Slave connection in form user:passwd@host:port:sock
    options[in]        dictionary of options (verbosity, quiet, pedantic)
    
    Returns bool - True if all tests pass, False if errors, warnings, failures
    """
    
    from mysql.utilities.common.server import connect_servers
    from mysql.utilities.common.rpl import Replication, get_replication_tests
    
    quiet = options.get("quiet", False)
    width = options.get("width", 75)
    slave_status = options.get("slave_status", False)

    test_errors = False

    conn_options = {
        'quiet'     : quiet,
        'src_name'  : "master",
        'dest_name' : 'slave',
        'version'   : "5.0.0",
        'unique'    : True,
    }
    servers = connect_servers(master_vals, slave_vals, conn_options)
    
    # Create an instance of the replication object
    rpl = Replication(servers[0], servers[1], options.get("verbosity", 0) > 0)
    
    if not quiet:
        print "Test Description",
        print ' ' * (width-24),
        print "Status"
        print '-' * width
    
    for test in get_replication_tests(rpl, options):
        if test.exec_test():
            test_errors = True
                
    if slave_status and not quiet:
        try:
            print "\n#\n# Slave status: \n#" 
            rpl.show_slave_status()
        except MySQLUtilError, e:
            print "ERROR:", e.errmsg
                        
    if not quiet:
        print "# ...done."
        
    return test_errors
