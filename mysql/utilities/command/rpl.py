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

def replicate(master_vals, slave_vals, slave_id, rpl_user,
              test_db=None, verbose=False):
    """
    """
    
    from mysql.utilities.common import connect_servers
    from mysql.utilities.common import Rpl
    from mysql.utilities.common import Server

    try:
        servers = connect_servers(master_vals, slave_vals, False, "5.0.0",
                                  "master", "slave")
    except MySQLUtilError, e:
        raise e
    
    # Fail if master and slave are using the same connection parameters.
    if (slave_vals["socket"] and \
        slave_vals["socket"] == master_vals["socket"] or \
        slave_vals["port"] == master_vals["port"]):
        raise MySQLUtilError("You must specify two different servers for "
                             "the operation.")

    # Create an instance of the replication object
    rpl = Rpl(servers[0], servers[1], verbose)
    
    # Check master for binary logging
    print "# Checking for binary logging on master..."
    if not rpl.check_master():
        raise MySQLUtilError("Master must have binary logging turned on.")
        
    # Setup replication
    print "# Setting up replication..."
    if not rpl.replicate(slave_id,  rpl_user, 10):
        raise MySQLUtilError("Cannot setup replication.")
        
    # Test the replication setup.
    if test_db:
        rpl.test(test_db, 10)
        
    print "# ...done."

