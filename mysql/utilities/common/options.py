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
This module contains the following methods design to support common option
parsing among the multiple utlities.

Methods:
  setup_common_options()     Setup standard options for utilities
  parse_connection()         Parse connection parameters
"""

import copy
import optparse
import re

from .. import VERSION_FRM
from mysql.utilities.exception import UtilError
from optparse import Option as CustomOption, OptionValueError as ValueError

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
    raise ValueError(("option %s: invalid choice: %r (choose from %s)")
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
                              "the form: <user>:<password>@<host>:<port>:"
                              "<socket>")
        else:
            parser.add_option("--server", action="store", dest="server",
                              type = "string", default=server_default,
                              help="connection information for the server in "
                              "the form: <user>:<password>@<host>:<port>:"
                              "<socket>")

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
                      type = "string", default=default_val,
                      help="the user and password for the replication " 
                           "user requirement - e.g. rpl:passwd " 
                           "- default = %default")


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
                      "server as the mastert, 'slave' = include the CHANGE "
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
                      help="connection information for candidate slave servers "
                      "for failover in the form: <user>:<password>@<host>:"
                      "<port>:<socket>. Valid only with failover command. "
                      "List multiple slaves in comma-separated list.")

    parser.add_option("--discover-slaves-login", action="store", dest="discover",
                      default=None, type="string", help="at startup, query "
                      "master for all registered slaves and use the user name "
                      "and password specified to connect. Supply the user and "
                      "password in the form user:password. For example, "
                      "--discover=joe:secret will use 'joe' as the user and "
                      "'secret' as the password for each discovered slave.")

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
                      "server in the form: <user>:<password>@<host>:<port>:"
                      "<socket>")
    
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
                      "the form: <user>:<password>@<host>:<port>:<socket>. "
                      "List multiple slaves in comma-separated list.")
    
    parser.add_option("--timeout", action="store", dest="timeout", default=3,
                      help="Maximum timeout in seconds to wait for each "
                      "replication command to complete. For example, timeout "
                      "for slave waiting to catch up to master. Default = 3.")


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
