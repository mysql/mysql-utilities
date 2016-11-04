#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights reserved.
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

from mysql.utilities.exception import UtilError, FormatError
from mysql.utilities.common.my_print_defaults import (MyDefaultsReader,
                                                      my_login_config_exists,
                                                      my_login_config_path)
from mysql.utilities.common.options_parser import MySQLOptionsParser


log = logging.getLogger('ip_parser')

_BAD_CONN_FORMAT = (u"Connection '{0}' cannot be parsed. Please review the "
                    u"used connection string (accepted formats: "
                    u"<user>[:<password>]@<host>[:<port>][:<socket>] or "
                    u"<login-path>[:<port>][:<socket>])")

_BAD_QUOTED_HOST = u"Connection '{0}' has a malformed quoted host"

_MULTIPLE_CONNECTIONS = (u"It appears you are attempting to specify multiple "
                         u"connections. This option does not permit multiple "
                         u"connections")

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
    r"((?:^[\'].*[\'])|(?:^[\"].*[\"]))"  # quoted host name
    r"(?:\:(\d+))?"                       # Optional port number
    r"(?:\:([\/\\w+.\w+.\-]+))?"          # Optional path to socket
)

_CONN_LOGINPATH = re.compile(
    r"((?:\\\"|[^:])+|(?:\\\'|[^:])+)"  # login-path
    r"(?:\:(\d+))?"                     # Optional port number
    r"(?:\:([\/\\w+.\w+.\-]+))?"        # Optional path to socket
)

_CONN_CONFIGPATH = re.compile(
    r"([\w\:]+(?:\\\"|[^[])+|(?:\\\'|[^[])+)"  # config-path
    r"(?:\[([^]]+))?",                         # group
    re.U
)

_CONN_ANY_HOST = re.compile(
    r"""([\w\.]*%)
       (?:\:{0,1}(.*))                   # capture all the rest
    """, re.VERBOSE)

_CONN_HOST_NAME = re.compile(
    r"""(
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
    r"""(
          (?:         # start of the IPv4 1st group
             25[0-5]  # this match numbers 250 to 255
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
                25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d
                      # same group as before
              )
           )
             {3}      # but it will match 3 times of it and prefixed by '.'
          )
          (?:\:{0,1}(.*))
          """, re.VERBOSE)

_CONN_port_ONLY = re.compile(
    r"""(?:
          \]{0,1}             # the ']' of IPv6 -optional
                 \:{0,1}      # the ':' for port number  -optional
                        (
                         \d*  # matches any sequence of numbers
                         )
         )          # end of port number group
        (?:\:{0,1}(.*))      # all the rest to extract the socket
        """, re.VERBOSE)

_CONN_socket_ONLY = re.compile(
    r"""(?:           # Not capturing group of ':'
           \:{0,1}
             ([      # Capturing '\' or '/' file name.ext
               \/\\w+.\w+.\-
               ]+    # to match a path
              )
        )?
       (.*)          # all the rest to advice the user.
    """, re.VERBOSE)

_CONN_IPv6 = re.compile(
    r"""
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
    """, re.VERBOSE)

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


def handle_config_path(config_path, group=None, use_default=True):
    """Retrieve the data associated to the given group.

    config_path[in]    the path to the configuration file.
    group[in]          The group name to retrieve the data from, if None
                       the 'client' group will be use if found and if
                       use_default is True.
    use_default[in]    Use the default 'client' group name, True by default,
                       used if no group is given.

    Returns a dictionary with the options data.
    """
    # first verify if the configuration file exist on the given config_path
    # check config_path as near file as normalized path, then
    # at the default location file.

    if os.name == 'nt':
        default_loc = os.path.join('c:\\', config_path)
    else:
        default_loc = os.path.join('/etc/mysql/', config_path)

    # default group
    default_group = 'client'
    # first look at the given path, if not found look at the default location
    paths = [os.path.normpath(config_path), os.path.normpath(default_loc)]
    req_group = group
    # if not group is given use default.
    if not req_group and use_default:
        req_group = default_group
    for file_loc in paths:
        if os.path.exists(file_loc) and os.path.isfile(file_loc):
            opt_par = MySQLOptionsParser(file_loc)
            dict_grp = opt_par.get_groups_as_dict(req_group)
            if dict_grp:
                return dict_grp[req_group]
            else:
                if group:
                    raise UtilError("The given group '{0}' was not found on "
                                    "the configuration file '{1}'"
                                    "".format(group, file_loc))
                else:
                    raise UtilError("The default group '{0}' was not found "
                                    "on the configuration file '{1}'"
                                    "".format(req_group, file_loc))

    # No configuration file was found
    if paths[0] != paths[1]:
        raise UtilError("Could not find a configuration file neither in the "
                        "given path '{0}' nor the default path '{1}'."
                        "".format(*paths))
    raise UtilError("Could not find a configuration file in the given "
                    "path '{0}'.".format(paths[0]))


def parse_connection(connection_values, my_defaults_reader=None, options=None):
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
    if options is None:
        options = {}

    def _match(pattern, search_str):
        """Returns the groups from string search or raise FormatError if it
        does not match with the pattern.
        """
        grp = pattern.match(search_str)
        if not grp:
            raise FormatError(_BAD_CONN_FORMAT.format(connection_values))
        return grp.groups()

    # SSL options, must not be overwritten with those from options.
    ssl_ca = None
    ssl_cert = None
    ssl_key = None
    ssl = None

    # Split on the '@' to determine the connection string format.
    # The user/password may have the '@' character, split by last occurrence.
    conn_format = connection_values.rsplit('@', 1)

    if len(conn_format) == 1:
        # No '@' so try config-path and login-path

        # The config_path and login-path collide on their first element and
        # only differs on their secondary optional values.
        # 1. Try match config_path and his optional value group. If both
        #    matches and the connection data can be retrieved, return the data.
        #    If errors occurs in this step raise them immediately.
        # 2. If config_path matches but group does not, and connection data
        #    can not be retrieved, do not raise errors and try to math
        #    login_path on step 4.
        # 3. If connection data is retrieved on step 2, then try login_path on
        #    next step to overwrite values from the new configuration.
        # 4. If login_path matches, check is .mylogin.cnf exists, if it doesn't
        #    and data configuration was found verify it  for missing values and
        #    continue if they are not any missing.
        # 5. If .mylogin.cnf exists and data configuration is found, overwrite
        #    any previews value from config_path if there is any.
        # 6. If login_path matches a secondary value but the configuration data
        #    could not be retrieved, do not continue and raise any error.
        # 7. In case errors have occurred trying to get data from config_path,
        #    and group did not matched, and in addition no secondary value,
        #    matched from login_path (port of socket) mention that config_path
        #    and login_path were not able to retrieve the connection data.

        # try login_path and overwrite the values.
        # Handle the format: config-path[[group]]
        config_path, group = _match(_CONN_CONFIGPATH, conn_format[0])
        port = None
        socket = None
        config_path_data = None
        login_path_data = None
        config_path_err_msg = None
        login_path = None
        if config_path:
            try:
                # If errors occurs, and group matched: raise any errors as the
                # group is exclusive of config_path.
                config_path_data = handle_config_path(config_path, group)
            except UtilError as err:
                if group:
                    raise
                else:
                    # Convert first letter to lowercase to include in error
                    # message with the correct case.
                    config_path_err_msg = \
                        err.errmsg[0].lower() + err.errmsg[1:]

        if group is None:
            # the conn_format can still be a login_path so continue
            # No '@' then handle has in the format: login-path[:port][:socket]
            login_path, port, socket = _match(_CONN_LOGINPATH, conn_format[0])

            # Check if the login configuration file (.mylogin.cnf) exists
            if login_path and not my_login_config_exists():
                if not config_path_data:
                    util_err_msg = (".mylogin.cnf was not found at is default "
                                    "location: {0}. Please configure your "
                                    "login-path data before using it (use the "
                                    "mysql_config_editor tool)."
                                    "".format(my_login_config_path()))
                    if config_path_err_msg and not (port or socket):
                        util_err_msg = ("{0} In addition, {1}"
                                        "").format(util_err_msg,
                                                   config_path_err_msg)
                    raise UtilError(util_err_msg)

            else:
                # If needed, create a MyDefaultsReader and search for
                # my_print_defaults tool.
                if not my_defaults_reader:
                    try:
                        my_defaults_reader = MyDefaultsReader(options)
                    except UtilError as err:
                        if config_path_err_msg and not (port or socket):
                            util_err_msg = ("{0} In addition, {1}"
                                            "").format(err.errmsg,
                                                       config_path_err_msg)
                            raise UtilError(util_err_msg)
                        else:
                            raise

                elif not my_defaults_reader.tool_path:
                    my_defaults_reader.search_my_print_defaults_tool()

                # Check if the my_print_default tool is able to read a
                # login-path from the mylogin configuration file
                if not my_defaults_reader.check_login_path_support():
                    util_err_msg = ("the used my_print_defaults tool does not "
                                    "support login-path options: {0}. "
                                    "Please confirm that the location to a "
                                    "tool with login-path support is included "
                                    "in the PATH (at the beginning)."
                                    "".format(my_defaults_reader.tool_path))
                    if config_path_err_msg and not (port or socket):
                        util_err_msg = ("{0} In addition, {1}"
                                        "").format(util_err_msg,
                                                   config_path_err_msg)
                    raise UtilError(util_err_msg)

                # Read and parse the login-path data (i.e., user, password and
                # host)
                login_path_data = my_defaults_reader.get_group_data(login_path)

        if config_path_data or login_path_data:
            if config_path_data:
                if not login_path_data:
                    login_path_data = config_path_data
                else:
                    # Overwrite values from login_path_data
                    config_path_data.update(login_path_data)
                    login_path_data = config_path_data

            user = login_path_data.get('user', None)
            passwd = login_path_data.get('password', None)
            host = login_path_data.get('host', None)
            if not port:
                port = login_path_data.get('port', None)
            if not socket:
                socket = login_path_data.get('socket', None)

            if os.name == "posix" and socket is not None:
                # if we are on unix systems and used a socket, hostname can be
                # safely assumed as being localhost so it is not required
                required_options = ('user', 'socket')
                host = 'localhost' if host is None else host
            else:
                required_options = ('user', 'host', 'port')

            missing_options = [opt for opt in required_options
                               if locals()[opt] is None]
            # If we are on unix and port is missing, user might have specified
            # a socket instead
            if os.name == "posix" and "port" in missing_options:
                i = missing_options.index("port")
                if socket:  # If we have a socket, port is not needed
                    missing_options.pop(i)
                else:
                    # if we don't have neither a port nor a socket, we need
                    # either a port or a socket
                    missing_options[i] = "port or socket"

            if missing_options:
                message = ",".join(missing_options)
                if len(missing_options) > 1:
                    comma_idx = message.rfind(",")
                    message = "{0} and {1}".format(message[:comma_idx],
                                                   message[comma_idx + 1:])
                pluralize = "s" if len(missing_options) > 1 else ""
                raise UtilError("Missing connection value{0} for "
                                "{1} option{0}".format(pluralize, message))

            # optional options, available only on config_path_data
            if config_path_data:
                ssl_ca = config_path_data.get('ssl-ca', None)
                ssl_cert = config_path_data.get('ssl-cert', None)
                ssl_key = config_path_data.get('ssl-key', None)
                ssl = config_path_data.get('ssl', None)

        else:
            if login_path and not config_path:
                raise UtilError("No login credentials found for login-path: "
                                "{0}. Please review the used connection string"
                                ": {1}".format(login_path, connection_values))
            elif not login_path and config_path:
                raise UtilError("No login credentials found for config-path: "
                                "{0}. Please review the used connection string"
                                ": {1}".format(login_path, connection_values))
            elif login_path and config_path:
                raise UtilError("No login credentials found for either "
                                "login-path: '{0}' nor config-path: '{1}'. "
                                "Please review the used connection string: {2}"
                                "".format(login_path, config_path,
                                          connection_values))

    elif len(conn_format) == 2:

        # Check to see if the user attempted to pass a list of connections.
        # This is true if there is at least one comma and multiple @ symbols.
        if ((connection_values.find(',') > 0) and
                (connection_values.find('@') > 1)):
            raise FormatError(_MULTIPLE_CONNECTIONS.format(connection_values))

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
            host, port, socket, _ = parse_server_address(hostportsock)

    else:
        # Unrecognized format
        raise FormatError(_BAD_CONN_FORMAT.format(connection_values))

    # Get character-set from options
    if isinstance(options, dict):
        charset = options.get("charset", None)
        # If one SSL option was found before, not mix with those in options.
        if not ssl_cert and not ssl_ca and not ssl_key and not ssl:
            ssl_cert = options.get("ssl_cert", None)
            ssl_ca = options.get("ssl_ca", None)
            ssl_key = options.get("ssl_key", None)
            ssl = options.get("ssl", None)

    else:
        # options is an instance of optparse.Values
        try:
            charset = options.charset  # pylint: disable=E1103
        except AttributeError:
            charset = None
        # If one SSL option was found before, not mix with those in options.
        if not ssl_cert and not ssl_ca and not ssl_key and not ssl:
            try:
                ssl_cert = options.ssl_cert  # pylint: disable=E1103
            except AttributeError:
                ssl_cert = None
            try:
                ssl_ca = options.ssl_ca  # pylint: disable=E1103
            except AttributeError:
                ssl_ca = None
            try:
                ssl_key = options.ssl_key  # pylint: disable=E1103
            except AttributeError:
                ssl_key = None
            try:
                ssl = options.ssl  # pylint: disable=E1103
            except AttributeError:
                ssl = None

    # Set parsed connection values
    connection = {
        "user": user,
        "host": host,
        "port": int(port) if port else 3306,
        "passwd": passwd if passwd else ''
    }

    if charset:
        connection["charset"] = charset
    if ssl_cert:
        connection["ssl_cert"] = ssl_cert
    if ssl_ca:
        connection["ssl_ca"] = ssl_ca
    if ssl_key:
        connection["ssl_key"] = ssl_key
    if ssl:
        connection["ssl"] = ssl
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
    # pylint: disable=R0101
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
        except FormatError:
            pass
    # we must alert, that the connection could not be parsed.
    if host is None:
        raise FormatError(_BAD_CONN_FORMAT.format(connection_str))
    _verify_parsing(connection_str, host, port, socket, address_type, unparsed)

    return host, port, socket, address_type


def _verify_parsing(connection_str, host, port, socket, address_type,
                    unparsed):
    """Verify that the connection string was totally parsed and not parts of
    it where not matched, otherwise raise an error.
    """
    exp_connection_str = connection_str
    log.debug("exp_connection_str {0}".format(exp_connection_str))
    parsed_connection_list = []
    if host:
        log.debug("host {0}".format(host))
        if address_type == ipv6 and "[" not in connection_str:
            host = host.replace("[", "")
            host = host.replace("]", "")
        parsed_connection_list.append(host)
    if port:
        log.debug("port {0}".format(port))
        parsed_connection_list.append(port)
    if socket:
        log.debug("socket {0}".format(socket))
        parsed_connection_list.append(socket)
    parsed_connection = ":".join(parsed_connection_list)
    log.debug('parsed_connection {0}'.format(parsed_connection))
    diff = None
    if not unparsed:
        log.debug('not unparsed found, creating diff')
        diff = connection_str.replace(host, "")
        if port:
            diff = diff.replace(port, "")
        if socket:
            diff = diff.replace(socket, "")
        log.debug("diff {0}".format(diff))
    log.debug("unparsed {0}".format(unparsed))
    if unparsed or (exp_connection_str != parsed_connection and
                    (diff and diff != ":")):
        log.debug("raising exception")
        parsed_args = "host:%s, port:%s, socket:%s" % (host, port, socket)
        log.debug(_UNPARSED_CONN_FORMAT.format(connection_str,
                                               parsed_args,
                                               unparsed))
        raise FormatError(_UNPARSED_CONN_FORMAT.format(connection_str,
                                                       parsed_args,
                                                       unparsed))


def _match(pattern, connection_str, trow_error=True):
    """Tries to match a pattern with the connection string and returns the
    groups.
    """
    grp = pattern.match(connection_str)
    if not grp:
        if trow_error:
            raise FormatError(_BAD_CONN_FORMAT.format(connection_str))
        return False
    return grp.groups()


def clean_IPv6(host_address):
    """Clean IPv6 host address
    """
    if host_address:
        host_address = host_address.replace("[", "")
        host_address = host_address.replace("]", "")
    return host_address


def format_IPv6(host_address):
    """Format IPv6 host address
    """
    if host_address:
        if "]" not in host_address:
            host_address = "[{0}]".format(host_address)
    return host_address


def parse_login_values_config_path(login_values, quietly=True):
    """Parse the login values to retrieve the user and password from a
    configuration file.

    login_values[in]    The login values to be parsed.
    quietly[in]         Do not raise exceptions (Default True).

    returns parsed (user, password) tuple or (login_values, None) tuple.
    """
    try:
        matches = _match(_CONN_CONFIGPATH, login_values, trow_error=False)
        if matches:
            path = matches[0]
            group = matches[1]
            data = handle_config_path(path, group, use_default=False)
            user = data.get('user', None)
            passwd = data.get('password', None)
            return user, passwd
    except (FormatError, UtilError):
        if not quietly:
            raise
    return login_values, None


def find_password(value):
    """Search for password in a string

    value[in]           String to search for password
    """
    if not isinstance(value, str):
        return False
    # has to have an @ sign
    if '@' not in value:
        return False
    match = _CONN_USERPASS.match(value)
    if not match:
        return False
    if match.group('passwd'):
        return True
    return False
