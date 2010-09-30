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
This module contains the following methods design to support common option
parsing among the multiple utlities.

Methods:
  setup_common_options()     Setup standard options for utilities
  parse_connection()         Parse connection parameters
"""

import optparse
import re

def setup_common_options(version_str, desc_str, usage_str):
    """Setup option parser and options common to all MySQL Utilities.
 
    This method creates an option parser and adds options for user
    login and connection options to a MySQL database system including
    user, password, host, socket, and port.
    
    version_str[in]    The string representing the utility version number
    desc_str[in]       The description of the utility
    usage_str[in]      A brief usage example
    
    Returns parser object
    """
    
    parser = optparse.OptionParser(version=version_str,
                                   description=desc_str,
                                   usage=usage_str,
                                   add_help_option=False)
    parser.add_option("--help", action="help")
    
    # Login user
    parser.add_option("-u", "--user", action="store",
                      type="string", dest="login_user",
                      help="user name for server login")
    
    # Login user password
    parser.add_option("-p", "--password", action="store",
                      type="string", dest="login_pass",
                      help="password for server login",
                      default="")
    
    # Hostname 
    parser.add_option("-h", "--host", action="store",
                      type="string", dest="host",
                      help="hostname of server to connect " \
                      "(default = %default)",
                      default="localhost")
    
    # Port
    parser.add_option("-P", "--port", action="store",
                      type="int", dest="port",
                      help="port for server login (default = %default)",
                      default=3306)
    
    # Socket
    parser.add_option("-S", "--socket", action="store",
                      type="string", dest="socket",
                      help="socket for server login",
                      default="")
    return parser


_CONN_CRE = re.compile(
    r"(\w+)"                    # User name
    r"(?:\:(\w+))?"             # Optional password
    r"@"
    r"([\w+|\d+|.]+)"           # Domain name or IP address
    r"(?:\:(\d+))?"             # Optional port number
    r"(?:\:([\/\\w+.\w+.\-]+))?" # Optional path to socket
    )

def parse_connection(connection_values):
    """Parse connection values.
    
    The function parses a connection specification of the form::
    
      user[:password]@host[:port[:socket]]

    A dictionary is returned containing the connection parameters. The
    function is designed so that it shall be possible to use it with a
    ``connect`` call in the following manner::

      options = parse_connection(spec)
      conn = MySQLdb.connect(**options)

    conn_values[in]     Connection values in the form:
                        user:password@host:port:socket
                        
    Returns dictionary (user, passwd, host, port, socket)
            or None if parsing error
    """
    
    grp = _CONN_CRE.match(connection_values)
    if not grp:
        from mysql.utilities.common import MySQLUtilError
        raise MySQLUtilError("Cannot parse connection.")
    user, passwd, host, port, socket = grp.groups()

    connection = {
        "user"   : user,
        "host"   : host,
        "port"   : int(port) if port else 3306,
        "passwd" : passwd if passwd else ''
    }
    
    # Handle optional parameters. They are only stored in the dict if
    # they were provided in the specifier.
    if socket is not None:
        connection['unix_socket'] = socket

    return connection

