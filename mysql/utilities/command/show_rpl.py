#!/usr/bin/env python
#
# Copyright (c) 2010, 2012 Oracle and/or its affiliates. All rights reserved.
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
This file contains the show replication topology functionality.
"""

import sys
from mysql.utilities.exception import UtilError

def show_topology(master_vals, options={}):
    """Show the slaves/topology map for a master.

    This method find the slaves attached to a server if it is a master. It
    can also discover the replication topology if the recurse option is
    True (default = False).
    
    It prints a tabular list of the master(s) and slaves found. If the
    show_list option is True, it will also print a list of the output
    (default = False).
    
    master_vals[in]    Master connection in form user:passwd@host:port:sock
    options[in]        dictionary of options
      recurse     If True, check each slave found for additional slaves
                       Default = False
      prompt_user      If True, prompt user if slave connection fails with
                       master connection parameters
                       Default = False
      num_retries      Number of times to retry a failed connection attempt
                       Default = 0
      quiet            if True, print only the data
                       Default = False
      format           Format of list
                       Default = Grid
      width            width of report
                       Default = 75
      max_depth        maximum depth of recursive search
                       Default = None
    """
    from mysql.utilities.common.topology_map import TopologyMap
    
    topo = TopologyMap(master_vals, options)
    topo.generate_topology_map(options.get('max_depth', None))

    if not options.get("quiet", False) and topo.depth():
        print "\n# Replication Topology Graph"
   
    if not topo.slaves_found():
        print "No slaves found."
        
    topo.print_graph()
    print

    if options.get("show_list", False):
        from mysql.utilities.common.format import print_list
        
        # make a list from the topology
        topology_list = topo.get_topology_map()
        print_list(sys.stdout, options.get("format", "GRID"),
                   ["Master", "Slave"], topology_list, False, True)

