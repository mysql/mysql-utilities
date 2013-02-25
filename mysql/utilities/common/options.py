#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
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
parsing among the multiple utilities.

Methods:
  setup_common_options()     Setup standard options for utilities
  parse_connection()         Parse connection parameters
"""

import copy
import optparse
import os.path
import re

from mysql.utilities import VERSION_FRM
from mysql.utilities.exception import FormatError
from mysql.utilities.exception import UtilError
from optparse import Option as CustomOption, OptionValueError as ValueError

from mysql.utilities.common.my_print_defaults import MyDefaultsReader
from mysql.utilities.common.my_print_defaults import my_login_config_exists
from mysql.utilities.common.my_print_defaults import my_login_config_path

_PERMITTED_FORMATS = ["grid", "tab", "csv", "vertical"]
_PERMITTED_DIFFS = ["unified", "context", "differ"]
_PERMITTED_RPL_DUMP = ["master", "slave"]

def prefix_check_choice(option, opt, value):
    """Check option values using case insensitive prefix compare

    This method checks to see if the value specified is a prefix of one of the
    choices. It converts the string provided by the user (value) to lower case
    to permit case insensitive comparison of the user input. If multiple
    choices are found for a prefix, an error is thrown. If the value being
    compared does not match the list of choices, an error is thrown.

    option[in]             Option class instance
    opt[in]                option name
    value[in]              the value provided by the user

    Returns string - valid option chosen
    """
    choices = ", ".join(map(repr, option.choices)) # String of choices

    # Get matches for prefix given
    alts = [alt for alt in option.choices if alt.startswith(value.lower())]
    if len(alts) == 1:   # only 1 match
       return alts[0]
    elif len(alts) > 1:  # multiple matches
        raise ValueError(("option %s: there are multiple prefixes matching: "
                          "%r (choose from %s)") % (opt, value, choices))

    # Doesn't match. Show user possible choices.
    raise ValueError("option %s: invalid choice: %r (choose from %s)"
                     % (opt, value, choices))


class CaseInsensitiveChoicesOption(CustomOption):
    """Case insensitive choices option class

    This is an extension of the Option class. It replaces the check_choice
    method with the prefix_check_choice() method above to provide
    shortcut aware choice selection. It also ensures the choice compare is
    done with a case insensitve test.
    """
    TYPE_CHECKER = copy.copy(CustomOption.TYPE_CHECKER)
    TYPE_CHECKER["choice"] = prefix_check_choice

    def __init__(self, *opts, **attrs):
        if 'choices' in attrs:
            attrs['choices'] = [ attr.lower() for attr in attrs['choices'] ]
        CustomOption.__init__(self, *opts, **attrs)


def setup_common_options(program_name, desc_str, usage_str,
                         append=False, server=True,
                         server_default="root@localhost:3306"):
    """Setup option parser and options common to all MySQL Utilities.

    This method creates an option parser and adds options for user
    login and connection options to a MySQL database system including
    user, password, host, socket, and port.

    program_name[in]   The program name
    desc_str[in]       The description of the utility
    usage_str[in]      A brief usage example
    append[in]         If True, allow --server to be specified multiple times
                       (default = False)
    server[in]         If True, add the --server option
                       (default = True)
    server_default[in] Default value for option
                       (default = "root@localhost:3306")

    Returns parser object
    """

    parser = optparse.OptionParser(
        version=VERSION_FRM.format(program=program_name),
        description=desc_str,
        usage=usage_str,
        add_help_option=False,
        option_class=CaseInsensitiveChoicesOption)
    parser.add_option("--help", action="help", help="display a help message "
                      "and exit")

    if server:
        # Connection information for the first server
        if append:
            parser.add_option("--server", action="append", dest="server",
                              help="connection information for the server in "
                              "the form: <user>[:<password>]@<host>[:<port>]"
                              "[:<socket>] or <login-path>[:<port>]"
                              "[:<socket>].")
        else:
            parser.add_option("--server", action="store", dest="server",
                              type="string", default=server_default,
                              help="connection information for the server in "
                              "the form: <user>[:<password>]@<host>[:<port>]"
                              "[:<socket>] or <login-path>[:<port>]"
                              "[:<socket>].")

    return parser


_SKIP_VALUES = (
    "tables","views","triggers","procedures",
    "functions","events","grants","data",
    "create_db"
)

def add_skip_options(parser):
    """Add the common --skip options for database utilties.

    parser[in]        the parser instance
    """
    parser.add_option("--skip", action="store", dest="skip_objects",
                      default=None, help="specify objects to skip in the "
                      "operation in the form of a comma-separated list (no "
                      "spaces). Valid values = tables, views, triggers, proc"
                      "edures, functions, events, grants, data, create_db")


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
            obj = object.lower()
            if obj in _SKIP_VALUES:
                new_skip_list.append(obj)
            else:
                raise UtilError("The value %s is not a valid value for "
                                "--skip." % object)
    return new_skip_list


def add_format_option(parser, help_text, default_val, sql=False):
    """Add the format option.

    parser[in]        the parser instance
    help_text[in]     help text
    default_val[in]   default value
    sql[in]           if True, add 'sql' format
                      default=False

    Returns corrected format value
    """
    formats = _PERMITTED_FORMATS
    if sql:
        formats.append('sql')
    parser.add_option("-f", "--format", action="store", dest="format",
                      default=default_val, help=help_text, type="choice",
                      choices=formats)


def add_format_option_with_extras(parser, help_text, default_val,
                                  extra_formats):
    """Add the format option.

    parser[in]        the parser instance
    help_text[in]     help text
    default_val[in]   default value
    extra_formats[in] list of additional formats to support

    Returns corrected format value
    """
    formats = _PERMITTED_FORMATS
    formats.extend(extra_formats)
    parser.add_option("-f", "--format", action="store", dest="format",
                      default=default_val, help=help_text, type="choice",
                      choices=formats)


def add_verbosity(parser, quiet=True):
    """Add the verbosity and quiet options.

    parser[in]        the parser instance
    quiet[in]         if True, include the --quiet option
                      (default is True)

    """
    parser.add_option("-v", "--verbose", action="count", dest="verbosity",
                      help="control how much information is displayed. "
                      "e.g., -v = verbose, -vv = more verbose, -vvv = debug")
    if quiet:
        parser.add_option("-q", "--quiet", action="store_true", dest="quiet",
                          help="turn off all messages for quiet execution.",
                          default=False)


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
                      type="choice", default="server1", help="specify the "
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
                      default=None, help="change all tables to use this "\
                      "storage engine if storage engine exists on the destination.")
    # Add default storage engine
    parser.add_option("--default-storage-engine", action="store",
                      dest="def_engine", default=None, help="change all "
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


def add_locking(parser):
    """Add the --locking option.

    parser[in]        the parser instance
    """
    parser.add_option("--locking", action="store", dest="locking",
                      type="choice", default="snapshot",
                      choices=['no-locks', 'lock-all', 'snapshot'],
                      help="choose the lock type for the operation: no-locks "
                      "= do not use any table locks, lock-all = use table "
                      "locks but no transaction and no consistent read, "
                      "snaphot (default): consistent read using a single "
                      "transaction.")


def add_regexp(parser):
    """Add the --regexp option.

    parser[in]        the parser instance
    """
    parser.add_option("-G", "--basic-regexp", "--regexp", dest="use_regexp",
                      action="store_true", default=False, help="use 'REGEXP' "
                      "operator to match pattern. Default is to use 'LIKE'.")


def add_rpl_user(parser, default_val="rpl:rpl"):
    """Add the --rpl-user option.

    parser[in]        the parser instance
    default_val[in]   default value for user, password
                      Default = rpl, rpl
    """
    parser.add_option("--rpl-user", action="store", dest="rpl_user",
                      type="string", default=default_val,
                      help="the user and password for the replication "
                           "user requirement, in the form: <user>[:<password>]"
                           " or <login-path>. E.g. rpl:passwd - By default = "
                           "%default")


def add_rpl_mode(parser, do_both=True, add_file=True):
    """Add the --rpl and --rpl-file options.

    parser[in]        the parser instance
    do_both[in]       if True, include the "both" value for the --rpl option
                      Default = True
    add_file[in]      if True, add the --rpl-file option
                      Default = True
    """
    rpl_mode_both = ""
    rpl_mode_options = _PERMITTED_RPL_DUMP
    if do_both:
        rpl_mode_options.append("both")
        rpl_mode_both = ", and 'both' = include 'master' and 'slave' " + \
                        "options where applicable"
    parser.add_option("--rpl", "--replication", dest="rpl_mode", action="store",
                      help="include replication information. Choices = 'master'"
                      " = include the CHANGE MASTER command using source "
                      "server as the master, 'slave' = include the CHANGE "
                      "MASTER command using the destination server's master "
                      "information%s." % rpl_mode_both,
                      choices=rpl_mode_options)
    if add_file:
        parser.add_option("--rpl-file", "--replication-file", dest="rpl_file",
                          action="store", help="path and file name to place the "
                          "replication information generated. Valid on if the "
                          "--rpl option is specified.")


def check_rpl_options(parser, options):
    """Check replication dump options for validity

    This method ensures the optional --rpl-* options are valid only when
    --rpl is specified.

    parser[in]        the parser instance
    options[in]       command options
    """
    if options.rpl_mode is None:
        errors = []
        if parser.has_option("--comment-rpl") and options.rpl_file is not None:
            errors.append("--rpl-file")

        if options.rpl_user is not None:
            errors.append("--rpl-user")

        # It's Ok if the options do not include --comment-rpl
        if parser.has_option("--comment-rpl") and options.comment_rpl:
            errors.append("--comment-rpl")

        if len(errors) > 1:
            num_opt_str = "s"
        else:
            num_opt_str = ""

        if len(errors) > 0:
            parser.error("The %s option%s must be used with the --rpl "
                         "option." % (", ".join(errors), num_opt_str))



def add_failover_options(parser):
    """Add the common failover options.

    This adds the following options:

      --candidates
      --discover-slaves-login
      --exec-after
      --exec-before
      --log
      --log-age
      --master
      --max-position
      --ping
      --seconds-behind
      --slaves
      --timeout

    parser[in]        the parser instance
    """
    parser.add_option("--candidates", action="store", dest="candidates",
                      type="string", default=None,
                      help="connection information for candidate slave servers"
                      " for failover in the form: <user>[:<password>]@<host>[:"
                      "<port>][:<socket>] or <login-path>[:<port>][:<socket>]."
                      " Valid only with failover command. List multiple slaves"
                      " in comma-separated list.")

    parser.add_option("--discover-slaves-login", action="store", dest="discover",
                      default=None, type="string", help="at startup, query "
                      "master for all registered slaves and use the user name "
                      "and password specified to connect. Supply the user and "
                      "password in the form <user>[:<password>] or "
                      "<login-path>. For example, --discover-slaves-login="
                      "joe:secret will use 'joe' as the user and 'secret' as "
                      "the password for each discovered slave.")

    parser.add_option("--exec-after", action="store", dest="exec_after",
                      default=None, type="string", help="name of script to "
                      "execute after failover or switchover")

    parser.add_option("--exec-before", action="store", dest="exec_before",
                      default=None, type="string", help="name of script to "
                      "execute before failover or switchover")

    parser.add_option("--log", action="store", dest="log_file", default=None,
                      type="string", help="specify a log file to use for "
                      "logging messages")

    parser.add_option("--log-age", action="store", dest="log_age", default=7,
                      type="int", help="specify maximum age of log entries in "
                      "days. Entries older than this will be purged on startup. "
                      "Default = 7 days.")

    parser.add_option("--master", action="store", dest="master", default=None,
                      type="string", help="connection information for master "
                      "server in the form: <user>[:<password>]@<host>[:<port>]"
                      "[:<socket>] or <login-path>[:<port>][:<socket>]")

    parser.add_option("--max-position", action="store", dest="max_position",
                      default=0, type="int", help="Used to detect slave "
                      "delay. The maximum difference between the master's "
                      "log position and the slave's reported read position of "
                      "the master. A value greater than this means the slave "
                      "is too far behind the master. Default is 0.")

    parser.add_option("--ping", action="store", dest="ping", default=None,
                      help="Number of ping attempts for detecting downed "
                      "server.")

    parser.add_option("--seconds-behind", action="store", dest="max_delay",
                      default=0, type="int", help="Used to detect slave "
                      "delay. The maximum number of seconds behind the master "
                      "permitted before slave is considered behind the master. "
                      "Default is 0.")

    parser.add_option("--slaves", action="store", dest="slaves",
                      type="string", default=None,
                      help="connection information for slave servers in "
                      "the form: <user>[:<password>]@<host>[:<port>]"
                      "[:<socket>] or <login-path>[:<port>][:<socket>]. "
                      "List multiple slaves in comma-separated list.")

    parser.add_option("--timeout", action="store", dest="timeout", default=300,
                      help="Maximum timeout in seconds to wait for each "
                      "replication command to complete. For example, timeout "
                      "for slave waiting to catch up to master. "
                      "Default = 300.")


def check_server_lists(parser, master, slaves):
    """Check to see if master is listed in slaves list

    Returns bool - True = master not in slaves, issue error if it appears
    """
    if slaves:
        for slave in slaves.split(',', 1):
            if master == slave:
                parser.error("You cannot list the master as a slave.")

    return True


def obj2sql(obj):
    """Convert a Python object to an SQL object.

    This function convert Python objects to SQL values using the
    conversion functions in the database connector package."""
    from mysql.connector.conversion import MySQLConverter
    return MySQLConverter().quote(obj)


_CONN_USERPASS = re.compile(
    r"(\w+)"                     # User name
    r"(?:\:(\w+))?"              # Optional password
    )

_CONN_LOGINPATH = re.compile(
    r"(\w+)"                     # login-path
    r"(?:\:(\d+))?"              # Optional port number
    r"(?:\:([\/\\w+.\w+.\-]+))?" # Optional path to socket
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

_CONN_IPv4_NUM_ONLY = re.compile(
    # we match IPv4 addresses only
    r"(?:[\d]{1,3}(?:\.[\d]{1,3})(?:\.[\d]{1,3})(?:\.[\d]{1,3}))"
    )

_CONN_IPv6 = re.compile(
    r"((?!.*::.*::)"             # Only a single whildcard allowed
     "(?:(?!:)|:(?=:))"          # Colon iff it would be part of a wildcard
     "(?:"                       # Repeat 6 times:
     "[0-9a-f]{0,4}"             #   A group of at most four hexadecimal digits
     "(?:(?<=::)|(?<!::):)"      #   Colon unless preceded by wildcard
     "){6}(?:"                   # Either
     "[0-9a-f]{0,4}"             #   Another group
     "(?:(?<=::)|(?<!::):)"      #   Colon unless preceded by wildcard
     "[0-9a-f]{0,4}"             #   Last group
     "(?:(?<=::)"                #   Colon iff preceded by exacly one colon
     "|(?<!:)|(?<=:)(?<!::) :)"  # OR
     "|"                         #   A v4 address with NO leading zeros
     "(?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)"
     "(?: \.(?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))"
    r"(?:\:(\d+))?"              # Optional port number
    r"(?:\:([\/\\w+.\w+.\-]+))?" # Optional path to socket
    )

_BAD_CONN_FORMAT = ("Connection '{0}' cannot be parsed. Please review the "
                    "used connection string (accepted formats: "
                    "<user>[:<password>]@<host>[:<port>][:<socket>] or "
                    "<login-path>[:<port>][:<socket>])")
_BAD_QUOTED_HOST = "Connection '{0}' has a malformed quoted host"


def hostname_is_ip(hostname):
    """Determine hostname is an IP address.

    Return bool - True = is IP address
    """
    if len(hostname.split(":")) <= 3:  # if fewer colons, must be IPv4
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
    conn_format = connection_values.split('@')

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
        user, passwd = _match(_CONN_USERPASS, userpass)

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
        elif len(hostportsock.split(":")) <= 3:  # if fewer colons, must be IPv4
            host, port, socket = _match(_CONN_IPv4, hostportsock)
        else:
            host, port, socket = _match(_CONN_IPv6, hostportsock)

    else:
        # Unrecognized format
        raise FormatError(_BAD_CONN_FORMAT.format(connection_values))

    # Set parsed connection values
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


def parse_user_password(userpass_values, my_defaults_reader=None, options={}):
    """ This function parses a string with the user/password credentials.

    This function parses the login string, determines the used format, i.e.
    user[:password] or login-path. If the ':' (colon) is not in the login
    string, the it can refer to a login-path or to a username (without a
    password). In this case, first it is assumed that the specified value is a
    login-path and the function attempts to retrieve the associated username
    and password, in a quiet way (i.e., without raising exceptions). If it
    fails to retrieve the login-path data, then the value is assumed to be a
    username.

    userpass_values[in]     String indicating the user/password credentials. It
                            must be in the form: user[:password] or login-path.
    my_defaults_reader[in]  Instance of MyDefaultsReader to read the
                            information of the login-path from configuration
                            files. By default, the value is None.
    options[in]             Dictionary of options (e.g. basedir), from the used
                            utility. By default, it set with an empty
                            dictionary. Note: also supports options values
                            from optparse.

    Returns a tuple with the username and password.
    """
    # Split on the ':' to determine if a login-path is used.
    login_values = userpass_values.split(':')
    if len(login_values) == 1:
        # Format is login-path or user (without a password): First, assume it
        # is a login-path and quietly try to retrieve the user and password.
        # If it fails, assume a user name is being specified.

        #Check if the login configuration file (.mylogin.cnf) exists
        if login_values[0] and not my_login_config_exists():
            return login_values[0], None

        if not my_defaults_reader:
            # Attempt to create the MyDefaultsReader
            try:
                my_defaults_reader = MyDefaultsReader(options)
            except UtilError:
                # Raise an UtilError when my_print_defaults tool is not found.
                return login_values[0], None
        elif not my_defaults_reader.tool_path:
            # Try to find the my_print_defaults tool
            try:
                my_defaults_reader.search_my_print_defaults_tool()
            except UtilError:
                # Raise an UtilError when my_print_defaults tool is not found.
                return login_values[0], None

        # Check if the my_print_default tool is able to read a login-path from
        # the mylogin configuration file
        if not my_defaults_reader.check_login_path_support():
            return login_values[0], None

        # Read and parse the login-path data (i.e., user and password)
        try:
            loginpath_data = my_defaults_reader.get_group_data(login_values[0])
            if loginpath_data:
                user = loginpath_data.get('user', None)
                passwd = loginpath_data.get('password', None)
                return user, passwd
            else:
                return login_values[0], None
        except UtilError:
            # Raise an UtilError if unable to get the login-path group data
            return login_values[0], None

    elif len(login_values) == 2:
        # Format is user:password; return a tuple with the user and password
        return login_values[0], login_values[1]
    else:
        # Invalid user credentials format
        return FormatError("Unable to parse the specified user credentials "
                           "(accepted formats: <user>[:<password> or "
                           "<login-path>): %s" % userpass_values)


def add_basedir_option(parser):
    """ Add the --basedir option.
    """
    parser.add_option("--basedir", action="store", dest="basedir",
                      default=None, type="string",
                      help="the base directory for the server")


def check_basedir_option(parser, opt_basedir):
    """ Check if the specified --basedir option is valid.
    """
    if opt_basedir and not os.path.isdir(opt_basedir):
        parser.error("The specified path for --basedir option is not a "
                     "directory: %s" % opt_basedir)
