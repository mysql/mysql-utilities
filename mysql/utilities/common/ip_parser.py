#
# Copyright (c) 2010, 2013 Oracle and/or its affiliates. All rights reserved.
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
This module contains the following methods design to support common operations
over the ip address or hostnames among the multiple utilities.

Methods:
  parse_connection()         Parse connection parameters
"""

import re
import os
import logging

from mysql.utilities.exception import FormatError
from mysql.utilities.common.my_print_defaults import MyDefaultsReader
from mysql.utilities.common.my_print_defaults import my_login_config_exists
from mysql.utilities.common.my_print_defaults import my_login_config_path
from mysql.utilities.exception import UtilError

log = logging.getLogger('ip_parser')

_BAD_CONN_FORMAT = (u"Connection '{0}' cannot be parsed. Please review the "
                    u"used connection string (accepted formats: "
                    u"<user>[:<password>]@<host>[:<port>][:<socket>] or "
                    u"<login-path>[:<port>][:<socket>])")

_BAD_QUOTED_HOST = u"Connection '{0}' has a malformed quoted host"

_UNPARSED_CONN_FORMAT = ("Connection '{0}' not parsed completely. Parsed "
                         "elements '{1}', unparsed elements '{2}'")

_CONN_USERPASS = re.compile(
    r"(?P<fquote>[\'\"]?)"    # First quote
    r"(?P<user>.+?)"          # User name
    r"(?:(?P=fquote))"        # First quote match
    r"(?:\:"                  # Optional :
    r"(?P<squote>[\'\"]?)"    # Second quote
    r"(?P<passwd>.+)"         # Password
    r"(?P=squote))"           # Second quote match
    r"|(?P<sfquote>[\'\"]?)"  # Quote on single user name
    r"(?P<suser>.+)"          # Single user name
    r"(?:(?P=sfquote))"       # Quote match on single user name
    )

_CONN_QUOTEDHOST = re.compile(
    r"((?:^[\'].*[\'])|(?:^[\"].*[\"]))" # quoted host name
    r"(?:\:(\d+))?"              # Optional port number
    r"(?:\:([\/\\w+.\w+.\-]+))?" # Optional path to socket
    )

_CONN_LOGINPATH = re.compile(
    r"(\w+)"                     # login-path
    r"(?:\:(\d+))?"              # Optional port number
    r"(?:\:([\/\\w+.\w+.\-]+))?" # Optional path to socket
    )

_CONN_ANY_HOST = re.compile(
    """([\w\.]*%)
       (?:\:{0,1}(.*))                   # capture all the rest
    """,re.VERBOSE)

_CONN_HOST_NAME = re.compile(
    """(
        (?:
           (?:
              (?:
                 (?!-)         # must not start with hyphen '-'
                 (?:[\w\d-])*  # must not end with the hyphen
                 [A-Za-z]      # starts with a character from the alphabet 
                 (?:[\w\d-])*  
                 (?:
                    (?<!-)     # end capturing if a '-' is followed by '.'
                 )
               ){1,63}         # limited length for segment
            )
         (?:                   # following segments 
            (?:\.)?            # the segment separator  the dot '.'
            (?:
               (?!-)
               [\w\d-]{1,63}   # last segment 
               (?<!-)          #shuld not end with hyphen
            )
          )* 
         )
        )
       (.*)                    # capture all the rest
     """, re.VERBOSE)

_CONN_IPv4_NUM_ONLY = re.compile(
    """(             
          (?:         # start of the IPv4 1st group
             25[0-4]  # this match numbers 250 to 254
                    | # or 
             2[0-4]\d # this match numbers from 200 to 249
                    | # or
             1\d\d    # this match numbers from 100 to 199
                    | # or
             [1-9]{0,1}\d # this match numbers from 0 to 99
           )  
          (?:         # start of the 3 next groups
             \.       # the prefix '.' like in '.255'
             (?:
                25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d
                      # same group as before
              )
           ) 
             {3}      # but it will match 3 times of it and prefixed by '.'  
          )
          (?:\:{0,1}(.*))
          """, re.VERBOSE)

_CONN_port_ONLY = re.compile(
    """(?:         
          \]{0,1}             # the ']' of IPv6 -optional
                 \:{0,1}      # the ':' for port number  -optional
                        (
                         \d*  # matches any sequence of numbers
                         )
         )          # end of port number group
        (?:\:{0,1}(.*))      # all the rest to extract the socket
        """, re.VERBOSE)

_CONN_socket_ONLY = re.compile(
    """(?:           # Not capturing group of ':'
           \:{0,1}
             ([      # Capturing '\' or '/' file name.ext 
               \/\\w+.\w+.\-
               ]+    # to match a path  
              )
        )?
       (.*)          # all the rest to advice the user.
    """, re.VERBOSE)

_CONN_IPv6 = re.compile(
    """
    \[{0,1}                   # the optional heading '[' 
    (
     (?!.*::.*::)              # Only a single whildcard allowed
     (?:(?!:)|:(?=:))          # Colon iff it would be part of a wildcard
     (?:                       # Repeat 6 times:
        [0-9a-f]{0,4}          # A group of at most four hexadecimal digits
        (?:(?<=::)|(?<!::):)   # Colon unless preceded by wildcard
     ){6}                      # expecting 6 groups 
     (?:                       # Either
        [0-9a-f]{0,4}          # Another group
        (?:(?<=::)|(?<!::):)   # Colon unless preceded by wildcard
        [0-9a-f]{0,4}          # Last group
        (?:(?<=::)             # Colon iff preceded by exacly one colon
           |(?<!:)
           |(?<=:)(?<!::): 
         )  
      )
     )
     (?:
        \]{0,1}\:{0,1}(.*)     # optional closing ']' and group for the rest
      )
    """,re.VERBOSE)

# Type of address amd Key names for the dictionary IP_matchers
HN = "hostname"
ipv4 = "IPv4"
ipv6 = "IPv6"
ANY_LIKE = "host like"
# This list is used to set an order to the matchers.
IP_matchers_list = [ipv4, ipv6, ANY_LIKE, HN]
# This dictionary is used to identify the matched type..
IP_matchers = {
    ANY_LIKE: _CONN_ANY_HOST,
    HN: _CONN_HOST_NAME,
    ipv4: _CONN_IPv4_NUM_ONLY,
    ipv6: _CONN_IPv6
    }

def hostname_is_ip(hostname):
    """Determine hostname is an IP address.
    
    Return bool - True = is IP address
    """
    if len(hostname.split(":")) <= 1:  # if fewer colons, must be IPv4
        grp = _CONN_IPv4_NUM_ONLY.match(hostname)
    else:
        grp = _CONN_IPv6.match(hostname)
    if not grp:
        return False
    return True


def parse_connection(connection_values, my_defaults_reader=None, options={}):
    """Parse connection values.

    The function parses a connection specification of one of the forms::

      - user[:password]@host[:port][:socket]
      - login-path[:port][:socket]

    A dictionary is returned containing the connection parameters. The
    function is designed so that it shall be possible to use it with a
    ``connect`` call in the following manner::

      options = parse_connection(spec)
      conn = mysql.connector.connect(**options)

    conn_values[in]         Connection values in the form:
                            user:password@host:port:socket
                            or login-path:port:socket
    my_defaults_reader[in]  Instance of MyDefaultsReader to read the
                            information of the login-path from configuration
                            files. By default, the value is None.
    options[in]             Dictionary of options (e.g. basedir), from the used
                            utility. By default, it set with an empty
                            dictionary. Note: also supports options values
                            from optparse.

    Notes:

    This method validates IPv4 addresses and standard IPv6 addresses.

    This method accepts quoted host portion strings. If the host is marked
    with quotes, the code extracts this without validation and assigns it to
    the host variable in the returned tuple. This allows users to specify host
    names and IP addresses that are outside of the supported validation.

    Returns dictionary (user, passwd, host, port, socket)
            or raise an exception if parsing error
    """

    def _match(pattern, search_str):
        grp = pattern.match(search_str)
        if not grp:
            raise FormatError(_BAD_CONN_FORMAT.format(connection_values))
        return grp.groups()

    # Split on the '@' to determine the connection string format.
    # The user/password may have the '@' character, split by last occurrence.
    conn_format = connection_values.rsplit('@', 1)

    if len(conn_format) == 1:
        # No '@' then handle has in the format: login-path[:port][:socket]
        login_path, port, socket = _match(_CONN_LOGINPATH, conn_format[0])

        #Check if the login configuration file (.mylogin.cnf) exists
        if login_path and not my_login_config_exists():
            raise UtilError(".mylogin.cnf was not found at is default "
                            "location: %s."
                            "Please configure your login-path data before "
                            "using it (use the mysql_config_editor tool)."
                            % my_login_config_path())

        # If needed, create a MyDefaultsReader and search for my_print_defaults
        # tool.
        if not my_defaults_reader:
            my_defaults_reader = MyDefaultsReader(options)
        elif not my_defaults_reader.tool_path:
            my_defaults_reader.search_my_print_defaults_tool()

        # Check if the my_print_default tool is able to read a login-path from
        # the mylogin configuration file
        if not my_defaults_reader.check_login_path_support():
            raise UtilError("the used my_print_defaults tool does not "
                            "support login-path options: %s. "
                            "Please confirm that the location to a tool with "
                            "login-path support is included in the PATH "
                            "(at the beginning)."
                            % my_defaults_reader.tool_path)

        # Read and parse the login-path data (i.e., user, password and host)
        login_path_data = my_defaults_reader.get_group_data(login_path)

        if login_path_data:
            user = login_path_data.get('user', None)
            passwd = login_path_data.get('password', None)
            host = login_path_data.get('host', None)
            if not port:
                port = login_path_data.get('port', 3306)
            if not socket:
                socket = login_path_data.get('socket', None)
        else:
            raise UtilError("No login credentials found for login-path: %s. "
                            "Please review the used connection string: %s"
                            % (login_path, connection_values))

    elif len(conn_format) == 2:

        # Handle as in the format: user[:password]@host[:port][:socket]
        userpass, hostportsock = conn_format

        # Get user, password
        match = _CONN_USERPASS.match(userpass)
        if not match:
            raise FormatError(_BAD_CONN_FORMAT.format(connection_values))
        user = match.group('user')
        if user is None:
            # No password provided
            user = match.group('suser').rstrip(':')
        passwd = match.group('passwd')

        # Handle host, port and socket
        if len(hostportsock) <= 0:
            raise FormatError(_BAD_CONN_FORMAT.format(connection_values))

        if hostportsock[0] in ['"', "'"]:
            # need to strip the quotes
            host, port, socket = _match(_CONN_QUOTEDHOST, hostportsock)
            if host[0] == '"':
                host = host.strip('"')
            if host[0] == "'":
                host = host.strip("'")

        else:
            host, port, socket, add_type = parse_server_address(hostportsock)

    else:
        # Unrecognized format
        raise FormatError(_BAD_CONN_FORMAT.format(connection_values))

    # Set parsed connection values
    connection = {
        "user" : user,
        "host" : host,
        "port" : int(port) if port else 3306,
        "passwd" : passwd if passwd else ''
        }

    # Handle optional parameters. They are only stored in the dict if
    # they were provided in the specifier.
    if socket is not None and os.name == "posix":
        connection['unix_socket'] = socket

    return connection


def parse_server_address(connection_str):
    """Parses host, port and socket from the given connection string.

    Returns a tuple of (host, port, socket, add_type) where add_type is
    the name of the parser that successfully parsed the hostname from
    the connection string.
    """
    # Default values to return.
    host = None
    port = None
    socket = None
    address_type = None
    unparsed = None
    # From the matchers look the one that match a host.
    for IP_matcher in IP_matchers_list:
        try:
            group = _match(IP_matchers[IP_matcher], connection_str)
            if group:
                host = group[0]
                if IP_matcher == ipv6:
                    host = "[%s]" % host
                
                if group[1]:
                    part2_port_socket = _match(_CONN_port_ONLY, group[1],
                                               trow_error=False)
                    if not part2_port_socket:
                        unparsed = group[1]
                    else: 
                        port = part2_port_socket[0]
                        if part2_port_socket[1]:
                            part4 = _match(_CONN_socket_ONLY,
                                           part2_port_socket[1],
                                           trow_error=False)
                            if not part4:
                                unparsed = part2_port_socket[1]
                            else:
                                socket = part4[0]
                                unparsed = part4[1]

            # If host is match we stop looking as is the most significant.
            if host:
                address_type = IP_matcher
                break
        # ignore the error trying to match.
        except FormatError as err:
            pass
    # we must alert, that the connection could not be parsed. 
    if host is None:
        raise FormatError(_BAD_CONN_FORMAT.format(connection_str))
    _verify_parsing(connection_str, host, port, socket, address_type, unparsed)

    return host, port, socket, address_type

def _verify_parsing(connection_str, host, port, socket, address_type, unparsed):
    """Verify that the connection string was totally parsed and not parts of
    it where not matched, otherwise raise an error.
    """
    exp_connection_str = connection_str
    log.debug("exp_connection_str %s" % exp_connection_str)
    #exp_connection_str = connection_str.replace("[","")
    #exp_connection_str = exp_connection_str.replace("]","")
    parsed_connection_list = []
    if host:
        log.debug("host %s" % host)
        if address_type == ipv6 and not "[" in connection_str:
            host = host.replace("[","")
            host = host.replace("]","")
        parsed_connection_list.append(host)
    if port:
        log.debug("port %s" % port)
        parsed_connection_list.append(port)
    if socket:
        log.debug("socket %s" % socket)
        parsed_connection_list.append(socket)
    parsed_connection = ":".join(parsed_connection_list)
    log.debug('parsed_connection %s' % parsed_connection)
    diff = None
    if not unparsed:
        log.debug('not unparsed found, creating diff')
        diff = connection_str.replace(host,"")
        if port:
            diff = diff.replace(port,"")
        if socket:
            diff = diff.replace(socket,"")
        log.debug("diff %s" % diff)
    log.debug("unparsed %s" % unparsed)
    if unparsed or (exp_connection_str != parsed_connection 
                    and (diff and diff != ":")):
        log.debug("raising exception")
        parsed_args = "host:%s, port:%s, socket:%s" % (host, port, socket)
        log.debug(_UNPARSED_CONN_FORMAT.format(connection_str,
                                                       parsed_args,
                                                       unparsed))
        raise FormatError(_UNPARSED_CONN_FORMAT.format(connection_str,
                                                       parsed_args,
                                                       unparsed))

def _match(pattern, connection_str, trow_error=True):
    grp = pattern.match(connection_str)
    if not grp:
        if trow_error:
            raise FormatError(_BAD_CONN_FORMAT.format(connection_str))
        return False
    return grp.groups()


def clean_IPv6(host_address):
    if host_address:
        host_address = host_address.replace("[","")
        host_address = host_address.replace("]","")
    return host_address


def format_IPv6(host_address):
    if host_address:
        if not "]" in host_address:
            host_address = "[{0}]".format(host_address)
    return host_address
