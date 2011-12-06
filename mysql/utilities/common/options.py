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
This module contains the following methods design to support common option
parsing among the multiple utlities.

Methods:
  setup_common_options()     Setup standard options for utilities
  parse_connection()         Parse connection parameters
"""

import optparse
import re

from .. import VERSION_FRM
from mysql.utilities.exception import UtilError

_PERMITTED_FORMATS = ["GRID", "TAB", "CSV", "VERTICAL"]
_PERMITTED_DIFFS = ["unified", "context", "differ"]

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

    from mysql.utilities.exception import UtilError

    new_skip_list = []
    if skip_list is not None:
        items = skip_list.split(",")
        for object in items:
            if object.upper() in _SKIP_VALUES:
                new_skip_list.append(object.upper())
            else:
                raise UtilError("The value %s is not a valid value for "
                                     "--skip." % object)
    return new_skip_list


def check_format_option(option, sql=False, initials=False):
    """Check format option for validity.
    
    option[in]        value specified
    sql[in]           if True, add 'SQL' format
                      default=False
    initials[in]      if True, add initial caps for compares
                      default=False
    
    Returns corrected format value
    """
    formats = _PERMITTED_FORMATS
    if sql:
        formats.append('SQL')
    candidates = [ f for f in formats if f.startswith(option.upper()) ]
    if len(candidates) > 1:
        message = ''.join([value, "is ambigous. Alternatives:"] + candidates)
        raise UtilError(message)
    if len(candidates) == 0:
        raise UtilError(option + " is not a valid format option.")

    return candidates[0]


def add_verbosity(parser, quiet=True):
    """Add the verbosity and quiet options.

    parser[in]        the parser instance
    quiet[in]         if True, include the --quiet option
                      (default is True)

    """
    parser.add_option("-v", "--verbose", action="count", dest="verbosity",
                      help="Control how much information is displayed. "
                      "e.g., -v = verbose, -vv = more verbose, -vvv = debug")
    if quiet:
        parser.add_option("-q", "--quiet", action="store_true", dest="quiet",
                          help="Turn off all messages for quiet execution.")


def check_verbosity(options):
    """Check to see if both verbosity and quiet are being used.
    """
    # Warn if quiet and verbosity are both specified
    if options.quiet is not None and options.quiet and \
       options.verbosity is not None and options.verbosity > 0:
        print "WARNING: --verbosity is ignored when --quiet is specified."
        options.verbosity = None


def add_changes_for(parser):
    """Add the changes_for option.

    parser[in]        the parser instance
    """
    parser.add_option("--changes-for", action="store", dest="changes_for",
                      type="choice", default="server1", help="Specify the "
                      "server to show transformations to match the other "
                      "server. For example, to see the transformation for "
                      "transforming server1 to match server2, use "
                      "--changes-for=server1. Valid values are 'server1' or "
                      "'server2'. The default is 'server1'.",
                      choices=['server1', 'server2'])


def add_reverse(parser):
    """Add the show-reverse option.

    parser[in]        the parser instance
    """
    parser.add_option("--show-reverse", action="store_true", dest="reverse",
                      default=False, help="produce a transformation report "
                      "containing the SQL statements to conform the object "
                      "definitions specified in reverse. For example if "
                      "--changes-for is set to server1, also generate the "
                      "transformation for server2. Note: the reverse changes "
                      "are annotated and marked as comments.")


def add_difftype(parser, allow_sql=False, default="unified"):
    """Add the difftype option.
    
    parser[in]        the parser instance
    allow_sql[in]     if True, allow sql as a valid option
                      (default is False)
    default[in]       the default option
                      (default is unified)
    """
    choice_list = ['unified', 'context', 'differ']
    if allow_sql:
        choice_list.append('sql')
    parser.add_option("-d", "--difftype", action="store", dest="difftype",
                      type="choice", default="unified", choices=choice_list,
                      help="display differences in context format in one of "
                      "the following formats: [%s] (default: unified)." %
                      '|'.join(choice_list))


def add_engines(parser):
    """Add the engine and default-storage-engine options.
    
    parser[in]        the parser instance
    """
    # Add engine
    parser.add_option("--new-storage-engine", action="store", dest="new_engine",
                      default=None, help="Change all tables to use this "\
                      "storage engine if storage engine exists on the destination.")
    # Add default storage engine
    parser.add_option("--default-storage-engine", action="store",
                      dest="def_engine", default=None, help="Change all "
                      "tables to use this storage engine if the original "
                      "storage engine does not exist on the destination.")


def check_engine_options(server, new_engine, def_engine,
                         fail=False, quiet=False):
    """Check to see if storage engines specified in options exist.
    
    This method will check to see if the storage engine in new exists on the
    server. If new_engine is None, the check is skipped. If the storage engine
    does not exist and fail is True, an exception is thrown else if quiet is
    False, a warning message is printed.
    
    Similarly, def_engine will be checked and if not present and fail is True,
    an exception is thrown else if quiet is False a warning is printed.
    
    server[in]         server instance to be checked
    new_engine[in]     new storage engine
    def_engine[in]     default storage engine
    fail[in]           If True, issue exception on failure else print warning
                       default = False
    quiet[in]          If True, suppress warning messages (not exceptions)
                       default = False
    """
    def _find_engine(server, target, message, fail, default):
        if target is not None:
            found = server.has_storage_engine(target)
            if not found and fail:
                raise UtilError(message)
            elif not found and not quiet:
                print message
        
    engines = server.get_storage_engines()
    message = "WARNING: %s storage engine %s is not supported on the server."
              
    _find_engine(server, new_engine,
                 message % ("New", new_engine),
                 fail, quiet)    
    _find_engine(server, def_engine,
                 message % ("Default", def_engine),
                 fail, quiet)    


def add_all(parser, objects):
    """Add the --all option.

    parser[in]        the parser instance
    objects[in]       name of the objects for which all includes
    """
    parser.add_option("-a", "--all", action="store_true", dest="all",
                      default=False, help="include all %s" % objects)


def check_all(parser, options, args, objects):
    """Check to see if both all and specific arguments are used.
    
    This method will throw an exception if there are arguments listed and
    the all option has been turned on.

    parser[in]        the parser instance
    options[in]       command options
    args[in]          arguments list
    objects[in]       name of the objects for which all includes
    """
    if options.all and len(args) > 0:
        parser.error("You cannot use the --all option with a list of "
                     "%s." % objects)


_CONN_USERPASS = re.compile(
    r"(\w+)"                     # User name
    r"(?:\:(\w+))?"              # Optional password
    )

_CONN_QUOTEDHOST = re.compile(
    r"((?:^[\'].*[\'])|(?:^[\"].*[\"]))" # quoted host name
    r"(?:\:(\d+))?"              # Optional port number
    r"(?:\:([\/\\w+.\w+.\-]+))?" # Optional path to socket
    )

_CONN_IPv4 = re.compile(
    # we match either: labels sized from 1-63 chars long, first label has alpha character
    # or we match IPv4 addresses
    # it is missing a RE for IPv6
    r"((?:(?:(?:(?!-)(?:[\w\d-])*[A-Za-z](?:[\w\d-])*(?:(?<!-))){1,63})"
     "(?:(?:\.)?(?:(?!-)[\w\d-]{1,63}(?<!-)))*|"
     "(?:[\d]{1,3}(?:\.[\d]{1,3})(?:\.[\d]{1,3})(?:\.[\d]{1,3}))))"  
                                 # Domain name or IP address
    r"(?:\:(\d+))?"              # Optional port number
    r"(?:\:([\/\\w+.\w+.\-]+))?" # Optional path to socket
    )

_CONN_IPv6 = re.compile(
    r"((?!.*::.*::)"             # Only a single whildcard allowed
     "(?:(?!:)|:(?=:))"          # Colon iff it would be part of a wildcard
     "(?:"                       # Repeat 6 times:
     "[0-9a-f]{0,4}"             #   A group of at most four hexadecimal digits
     "(?:(?<=::)|(?<!::):)"      #   Colon unless preceeded by wildcard
     "){6}(?:"                   # Either
     "[0-9a-f]{0,4}"             #   Another group
     "(?:(?<=::)|(?<!::):)"      #   Colon unless preceeded by wildcard
     "[0-9a-f]{0,4}"             #   Last group
     "(?:(?<=::)"                #   Colon iff preceeded by exacly one colon
     "|(?<!:)|(?<=:)(?<!::) :)"  # OR
     "|"                         #   A v4 address with NO leading zeros 
     "(?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)"
     "(?: \.(?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))"
    r"(?:\:(\d+))?"              # Optional port number
    r"(?:\:([\/\\w+.\w+.\-]+))?" # Optional path to socket
    )

_BAD_CONN_FORMAT = "Connection '{0}' cannot be parsed as a connection"
_BAD_QUOTED_HOST = "Connection '{0}' has a malformed quoted host"

def parse_connection(connection_values):
    """Parse connection values.

    The function parses a connection specification of the form::

      user[:password]@host[:port[:socket]]

    A dictionary is returned containing the connection parameters. The
    function is designed so that it shall be possible to use it with a
    ``connect`` call in the following manner::

      options = parse_connection(spec)
      conn = mysql.connector.connect(**options)

    conn_values[in]     Connection values in the form:
                        user:password@host:port:socket
                        
    Notes:
    
    This method validates IPv4 addresses and standard IPv6 addresses.
    
    This method accepts quoted host portion strings. If the host is marked
    with quotes, the code extracts this without validation and assigns it to
    the host variable in the returned tuple. This allows users to specify host
    names and IP addresses that are outside of the supported validation.

    Returns dictionary (user, passwd, host, port, socket)
            or None if parsing error
    """
    import os
    from mysql.utilities.exception import FormatError
    
    def _match(pattern, search_str):
        grp = pattern.match(search_str)
        if not grp:
            raise FormatError(_BAD_CONN_FORMAT.format(connection_values))
        return grp.groups()

    # Split on the '@'
    try:
        userpass, hostportsock = connection_values.split('@')
    except:
        raise FormatError(_BAD_CONN_FORMAT.format(connection_values))

    # Get user, password    
    user, passwd = _match(_CONN_USERPASS, userpass)

    if len(hostportsock) <= 0:
        raise FormatError(_BAD_CONN_FORMAT.format(connection_values))

    if hostportsock[0] in ['"', "'"]:
        # need to strip the quotes
        host, port, socket = _match(_CONN_QUOTEDHOST, hostportsock)
        if host[0] == '"':
            host = host.strip('"')
        if host[0] == "'":
            host = host.strip("'")
    elif len(hostportsock.split(":")) <= 3:  # if fewer colons, must be IPv4
        host, port, socket = _match(_CONN_IPv4, hostportsock)
    else:
        host, port, socket = _match(_CONN_IPv6, hostportsock)

    connection = {
        "user"   : user,
        "host"   : host,
        "port"   : int(port) if port else 3306,
        "passwd" : passwd if passwd else ''
    }

    # Handle optional parameters. They are only stored in the dict if
    # they were provided in the specifier.
    if socket is not None and os.name == "posix":
        connection['unix_socket'] = socket

    return connection

def test_suite():
    import tests.test_options
    return tests.test_options.test_suite()
