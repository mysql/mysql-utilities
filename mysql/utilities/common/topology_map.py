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
This module contains an abstraction of a topolgy map object used to discover
slaves and down-stream replicants for mapping topologies.
"""

import os
from mysql.utilities.exception import UtilError

class TopologyMap(object):
    """The TopologyMap class can be used to connect to a running MySQL server
    and discover its slaves. Setting the option "recurse" permits the
    class to discover a replication topology by finding the slaves for each
    slave for the first master requested.

    To generate a topology map, the caller must call the generate_topology_map()
    method to build the topology. This is left as a separate state because it
    can be a lengthy process thereby too long for a constructor method.
 
    The class also includes methods for printing a graph of the topology
    as well as returning a list of master, slave tuples reporting the
    host name and port for each.
    """

    def __init__(self, seed_server, options={}):
        """Constructor

        seed_server[in]    Master (seed) server connection dictionary                           
        options[in]        options for controlling behavior:
          recurse          If True, check each slave found for add'l slaves
                           Default = False
          prompt_user      If True, prompt user if slave connection fails with
                           master connection parameters
                           Default = False
          quiet            if True, print only the data
                           Default = False
          width            width of report
                           Default = 75
          num_retries      Number of times to retry a failed connection attempt
                           Default = 0
        """
        from mysql.utilities.common.server import get_connection_dictionary
        
        self.recurse = options.get("recurse", False)
        self.quiet = options.get("quiet", False)
        self.prompt_user = options.get("prompt", False)
        self.num_retries = options.get("num_retries", 0)
        self.socket_path = options.get("socket_path", None)
        self.seed_server = seed_server
        self.topology = []


    def _connect(self, conn):
        """Find the attached slaves for a list of server connections.
        
        This method connects to each server in the list and retrieves its slaves.
        It can be called recursively if the recurse parameter is True.
        
        conn[in]           Connection dictionary used to connect to server
    
        Returns tuple - master Server class instance, master:host string
        """
        import getpass
        
        from mysql.utilities.common.server import connect_servers
    
        conn_options = {
            'quiet'     : self.quiet,
            'src_name'  : "master",
            'dest_name' : None,
            'version'   : "5.0.0",
            'unique'    : True,
        }
        
        master_info = "%s:%s" % (conn['host'],
                                 conn['port'])
        master = None
        
        # Clear socket if used with a local server
        if (conn['host'] == 'localhost' or \
            conn['host'] == "127.0.0.1"):
            conn['unix_socket'] = None
        
        # Increment num_retries if not set when --prompt is used
        if self.prompt_user and self.num_retries == 0:
            self.num_retries += 1
    
        # Attempt to connect to the server given the retry limit
        for i in range(0,self.num_retries+1):
            try:
                servers = connect_servers(conn, None, conn_options)
                master = servers[0]
                break
            except UtilError, e:
                print "FAILED.\n"
                if i < self.num_retries and self.prompt_user:
                    print "Connection to %s has failed.\n" % master_info + \
                    "Please enter the following information " + \
                    "to connect to this server."
                    conn['user'] = raw_input("User name: ")
                    conn['passwd'] = getpass.getpass("Password: ")
                else:
                    # retries expired - re-raise error if still failing
                    raise UtilError(e.errmsg)
    
        return (master, master_info)
    
    
    def _check_permissions(self, server, priv):
        """Check to see if user has permissions to execute.
        
        server[in]     Server class instance
        priv[in]       privilege to check
        
        Returns True if permissions available, raises exception if not
        """
        from mysql.utilities.common.user import User

        # Check user permissions 
        user_pass_host = server.user
        if server.passwd is not None and len(server.passwd) > 0:
            user_pass_host += ":" + server.passwd
        user_pass_host += "@" + server.host
        user = User(server, user_pass_host, False)
        if not user.has_privilege("*", "*", priv):
            raise UtilError("Not enough permissions. The user must have the "
                            "%s privilege." % priv)
    

    def _get_slaves(self, max_depth, seed_conn=None, masters_found=[]):
        """Find the attached slaves for a list of server connections.
        
        This method connects to each server in the list and retrieves its slaves.
        It can be called recursively if the recurse option is True.
    
        max_depth[in]       Maximum depth of recursive search
        seed_conn[in]       Current master connection dictionary. Initially,
                            this is the seed server (original master defined
                            in constructor)
        masters_found[in]   a list of all servers in master roles - used to
                            detect a circular replication topology. Initially,
                            this is an empty list as the master detection must
                            occur as the topology is traversed.
    
        Returns list - list of slaves connected to each server in list
        """
        topology = []
        if seed_conn is None:
            seed_conn = self.seed_server
    
        master, master_info = self._connect(seed_conn)
        if master is None:
            return []
   
        # Check user permissions 
        self._check_permissions(master, "REPLICATION SLAVE")

        # Save the master for circular replication identification
        masters_found.append(master_info)
        
        if not self.quiet:
            print "# Finding slaves for master: %s" % master_info
    
        # Get replication topology
        slaves = master.get_slaves()
        slave_list = []
        depth = 0
        if len(slaves) > 0:
            for slave in slaves:
                if slave.find(":") > 0:
                    host, port = slave.split(":")
                else:
                    host = slave
                    port = START_PORT  # Use the default
                slave_conn = self.seed_server.copy()
                slave_conn['host'] = host
                slave_conn['port'] = port
                
                # Now check for circular replication topology - do not recurse
                # if slave is also a master.
                if self.recurse and not slave in masters_found and \
                   ((max_depth is None) or (depth < max_depth)):
                    new_list = self._get_slaves(max_depth, slave_conn,
                                                masters_found)
                    if new_list == []:
                        slave_list.append((slave, []))
                    else:
                        slave_list.append(new_list)
                    depth += 1
                else:
                    slave_list.append((slave, []))
        topology.append((master_info, slave_list))
    
        return topology


    def generate_topology_map(self, max_depth):
        """Find the attached slaves for a list of server connections.
        
        This method generates the topology for the seed server specified at
        instantiation.

        max_depth[in]       Maximum depth of recursive search
        """
        self.topology = self._get_slaves(max_depth)


    def depth(self):
        """Return depth of the topology tree.
        
        Returns int - depth of topology tree.
        """
        return len(self.topology)


    def slaves_found(self):
        """Check to see if any slaves were found.
        
        Returns bool - True if slaves found, False if no slaves.
        """
        return not (len(self.topology) and self.topology[0][1] == [])


    def print_graph(self, topology_list=[], masters_found=[],
                    level=0, preamble=""):
        """Prints a graph of the topology map to standard output.
        
        This method traverses a list of the topology and prints a graph. The
        method is designed to be recursive traversing the list to print the
        slaves for each master in the topology. It will also detect a circular
        replication segment and indicate it on the graph.
        
        topology_list[in]   a list in the form (master, slave) of server
        masters_found[in]   a list of all servers in master roles - used to
                            detect a circular replication topology. Initially,
                            this is an empty list as the master detection must
                            occur as the toplogy is traversed.
        level[in]           the level of indentation - increases with each
                            set of slaves found in topology
        preamble[in]        prefix calculated during recursion to indent text
        """
        # if first iteration, use the topology list generated earlier
        if topology_list == []:
            if self.topology == []:
                # topology not generated yet
                raise UtilError("You must first generate the topology.")
            topology_list = self.topology

        # Detect if we are looking at a sublist or not. Get sublist.
        if len(topology_list) == 1:
            topology_list = topology_list[0]
        master = topology_list[0]
        
        # Save the master for circular replication identification
        masters_found.append(master)

        # For each slave, print the graph link
        slaves = topology_list[1]
        stop = len(slaves)
        if stop > 0:
            # Level 0 is always the first master in the topology.
            if level == 0:
                print "%s (MASTER)" % master
            for i in range(0,stop):
                if len(slaves[i]) == 1:
                    slave = slaves[i][0]
                else:
                    slave = slaves[i]
                new_preamble = preamble + "   "
                print new_preamble+"|"
                role = "(SLAVE"
                if not slave[1] == [] or slave[0] in masters_found:
                    role += " + MASTER"
                role += ")"
                print "%s+--- %s" % (new_preamble, slave[0]),
                
                if (slave[0] in masters_found):
                    print "<-->",
                else:
                    print "-",
                print "%s" % role
                    
                if not slave[1] == []:
                    if i < stop-1:
                        new_preamble += "|"
                    else:
                        new_preamble += " "
                    self.print_graph(slave, masters_found,
                                     level+1, new_preamble)


    def _get_row(self, topology_list):
        """Get a row (master, slave) for the topology map.
        
        topology_list[in]  The topology list
        
        Returns tuple - a row (master, slave)
        """
        new_row = []
        if len(topology_list) == 1:
            topology_list = topology_list[0]
        master = topology_list[0]
        slaves = topology_list[1]
        for slave in slaves:
            if len(slave) == 1:
                new_slave = slave[0]
            else:
                new_slave = slave
            new_row.append((master, new_slave[0]))
            new_row.extend(self._get_row(new_slave))
        return new_row


    def get_topology_map(self):
        """Get a list of the topology map suitable for export
        
        Returns list - a list of masters and their slaves in two columns
        """
        # Get a row for the list
        # make a list from the topology
        master_slaves = [self._get_row(row) for row in self.topology]
        return master_slaves[0]

