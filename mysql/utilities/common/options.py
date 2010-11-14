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

def setup_common_options(program_name, desc_str, usage_str, append=False):
    """Setup option parser and options common to all MySQL Utilities.
 
    This method creates an option parser and adds options for user
    login and connection options to a MySQL database system including
    user, password, host, socket, and port.
    
    program_name[in]   The program name
    desc_str[in]       The description of the utility
    usage_str[in]      A brief usage example
    append[in]         If True, allow --server to be specified multiple times
                       (default = False)
    
    Returns parser object
    """
    
    parser = optparse.OptionParser(
        version=VERSION_FRM.format(program=program_name),
        description=desc_str,
        usage=usage_str,
        add_help_option=False)
    parser.add_option("--help", action="help")
    
    # Connection information for the first server
    if append:
        parser.add_option("--server", action="append", dest="server",
                          help="connection information for the server in " + \
                          "the form: <user>:<password>@<host>:<port>:<socket>")
    else:
        parser.add_option("--server", action="store", dest="server",
                          type = "string", default="root@localhost:3306",
                          help="connection information for the server in " + \
                          "the form: <user>:<password>@<host>:<port>:<socket>")

    return parser


_SKIP_VALUES = (
    "TABLES","VIEWS","TRIGGERS","PROCEDURES",
    "FUNCTIONS","EVENTS","GRANTS","DATA",
    "CREATE_DB"
)

def add_skip_options(parser):
    """Add the common --skip options for database utilties.
    
    parser[in]        the parser instance
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
    
    from mysql.utilities.exception import MySQLUtilError
    
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


def add_verbosity(parser, silent=True):
    """Add the verbosity and silent options.
    
    parser[in]        the parser instance
    silent[in]        if True, include the --silent option
                      (default is True)
    
    """
    parser.add_option("-v", "--verbose", action="count", dest="verbosity",
                      help="Control how much information is displayed. "
                      "e.g., -v = verbose, -vv = more verbose, -vvv = debug")
    if silent:
        parser.add_option("-s", "--silent", action="store_true", dest="silent",
                          help="Turn off all messages for silent execution.")
        

def check_verbosity(options):
    """Check to see if both verbosity and silent are being used.
    """
    # Warn if silent and verbosity are both specified
    if options.silent is not None and options.silent and \
       options.verbosity is not None and options.verbosity > 0:
        print "WARNING: --verbosity is ignored when --silent is specified."
        options.verbosity = None


_CONN_CRE = re.compile(
    r"(\w+)"                    # User name
    r"(?:\:(\w+))?"             # Optional password
    r"@"
    r"([\w+|\d+|.]+)"           # Domain name or IP address
    r"(?:\:(\d+))?"             # Optional port number
    r"(?:\:([\/\\w+.\w+.\-]+))?" # Optional path to socket
    )

_BAD_CONN_FORMAT = "Connection '{0}' cannot be parsed as a connection"

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
        from mysql.utilities.exception import FormatError
        raise FormatError(_BAD_CONN_FORMAT.format(connection_values))
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

def test_suite():
    import tests.test_options
    return tests.test_options.test_suite()
