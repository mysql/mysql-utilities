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

from .. import VERSION_FRM
from mysql.utilities.exception import MySQLUtilError

def setup_common_options(program_name, desc_str, usage_str):
    """Setup option parser and options common to all MySQL Utilities.
 
    This method creates an option parser and adds options for user
    login and connection options to a MySQL database system including
    user, password, host, socket, and port.
    
    program_name[in]   The program name
    desc_str[in]       The description of the utility
    usage_str[in]      A brief usage example
    
    Returns parser object
    """
    
    parser = optparse.OptionParser(
        version=VERSION_FRM.format(program=program_name),
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



_SKIP_VALUES = (
    "TABLES","VIEWS","TRIGGERS","PROCEDURES",
    "FUNCTIONS","EVENTS","GRANTS","DATA",
    "CREATE_DB"
)

def add_skip_options(parser):
    """Add the common --skip options for database utilties.
    """
    parser.add_option("--skip", action="store", dest="skip_objects",
                      default=None, help="specify objects to skip in the "
                      "operation in the form of a comma-separated list (no "
                      "spaces). Valid values = TABLES, VIEWS, TRIGGERS, PROC"
                      "EDURES, FUNCTIONS, EVENTS, GRANTS, DATA, CREATE_DB")
    
    
def check_skip_options(skip_list):
    """Check skip options for validity
    
    skip_list[in]     List of items from parser option.
    
    Returns new skip list with items converted to upper case.
    """
    new_skip_list = []
    if skip_list is not None:
        items = skip_list.split(",")
        for object in items:
            if object.upper() in _SKIP_VALUES:
                new_skip_list.append(object.upper())
            else:
                raise MySQLUtilError("The value %s is not a valid value for "
                                     "--skip." % object)
    return new_skip_list


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
        from mysql.utilities.exception import MySQLUtilError
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

