#
# Copyright (c) 2010, 2014, Oracle and/or its affiliates. All rights reserved.
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
"""

import copy
import optparse
import os.path
import re

from optparse import Option as CustomOption, OptionValueError
from ip_parser import find_password

from mysql.utilities import LICENSE_FRM, VERSION_FRM
from mysql.utilities.exception import UtilError, FormatError
from mysql.connector.conversion import MySQLConverter
from mysql.utilities.common.messages import PARSE_ERR_OBJ_NAME_FORMAT
from mysql.utilities.common.my_print_defaults import (MyDefaultsReader,
                                                      my_login_config_exists)
from mysql.utilities.common.pattern_matching import REGEXP_QUALIFIED_OBJ_NAME
from mysql.utilities.common.sql_transform import (is_quoted_with_backticks,
                                                  remove_backtick_quoting)


_PERMITTED_FORMATS = ["grid", "tab", "csv", "vertical"]
_PERMITTED_DIFFS = ["unified", "context", "differ"]
_PERMITTED_RPL_DUMP = ["master", "slave"]


class UtilitiesParser(optparse.OptionParser):
    """Special subclass of parser that allows showing of version information
       when --help is used.
    """

    def print_help(self, output=None):
        """Show version information before help
        """
        print self.version
        optparse.OptionParser.print_help(self, output)

    def format_epilog(self, formatter):
        return self.epilog if self.epilog is not None else ''


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
    # String of choices
    choices = ", ".join([repr(choice) for choice in option.choices])

    # Get matches for prefix given
    alts = [alt for alt in option.choices if alt.startswith(value.lower())]
    if len(alts) == 1:   # only 1 match
        return alts[0]
    elif len(alts) > 1:  # multiple matches
        raise OptionValueError(
            ("option %s: there are multiple prefixes "
             "matching: %r (choose from %s)") % (opt, value, choices))

    # Doesn't match. Show user possible choices.
    raise OptionValueError("option %s: invalid choice: %r (choose from %s)"
                           % (opt, value, choices))


def license_callback(self, opt, value, parser, *args, **kwargs):
    """Show license information and exit.
    """
    print(LICENSE_FRM.format(program=parser.prog))
    parser.exit()


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
            attrs['choices'] = [attr.lower() for attr in attrs['choices']]
        CustomOption.__init__(self, *opts, **attrs)


def setup_common_options(program_name, desc_str, usage_str,
                         append=False, server=True,
                         server_default="root@localhost:3306",
                         extended_help=None):
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
    extended_help[in]  Extended help (by default: None).

    Returns parser object
    """

    program_name = program_name.replace(".py", "")
    parser = UtilitiesParser(
        version=VERSION_FRM.format(program=program_name),
        description=desc_str,
        usage=usage_str,
        add_help_option=False,
        option_class=CaseInsensitiveChoicesOption,
        epilog=extended_help,
        prog=program_name)
    parser.add_option("--help", action="help", help="display a help message "
                      "and exit")
    parser.add_option("--license", action='callback',
                      callback=license_callback,
                      help="display program's license and exit")

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


def add_character_set_option(parser):
    """Add the --character-set option.

    parser[in]        the parser instance
    """
    parser.add_option("--character-set", action="store", dest="charset",
                      type="string", default=None,
                      help="sets the client character set. The default is "
                      "retrieved from the server variable "
                      "'character_set_client'.")


_SKIP_VALUES = (
    "tables", "views", "triggers", "procedures",
    "functions", "events", "grants", "data",
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
    new_skip_list = []
    if skip_list is not None:
        items = skip_list.split(",")
        for item in items:
            obj = item.lower()
            if obj in _SKIP_VALUES:
                new_skip_list.append(obj)
            else:
                raise UtilError("The value %s is not a valid value for "
                                "--skip." % item)
    return new_skip_list


def add_format_option(parser, help_text, default_val, sql=False,
                      extra_formats=None):
    """Add the format option.

    parser[in]        the parser instance
    help_text[in]     help text
    default_val[in]   default value
    sql[in]           if True, add 'sql' format
                      default=False
    extra_formats[in] list with extra formats

    Returns corrected format value
    """
    formats = _PERMITTED_FORMATS
    if sql:
        formats.append('sql')
    if extra_formats:
        formats.extend(extra_formats)
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


def add_no_headers_option(parser, restricted_formats=None, help_msg=None):
    """Add the --no-headers option.

    parser[in]              The parser instance.
    restricted_formats[in]  List of formats supported by this option (only
                            applies to them).
    help_msg[in]            Alternative help message to use, otherwise a
                            default one is used.
    """
    # Create the help message according to any format restriction.
    if restricted_formats:
        plural = "s" if len(restricted_formats) > 1 else ""
        formats_msg = (" (only applies to format{0}: "
                       "{1})").format(plural, ", ".join(restricted_formats))
    else:
        formats_msg = ""
    if help_msg:
        help_msg = "{0}{1}.".format(help_msg, formats_msg)
    else:
        help_msg = "do not show column headers{0}.".format(formats_msg)
    # Add the option.
    parser.add_option("-h", "--no-headers", action="store_true",
                      dest="no_headers", default=False, help=help_msg)


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


def add_changes_for(parser, default="server1"):
    """Add the changes_for option.

    parser[in]        the parser instance
    """
    parser.add_option("--changes-for", action="store", dest="changes_for",
                      type="choice", default=default, help="specify the "
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
                      "containing the SQL statements to transform the object "
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
    parser.add_option("--new-storage-engine", action="store",
                      dest="new_engine", default=None, help="change all "
                      "tables to use this storage engine if storage engine "
                      "exists on the destination.")
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
        """Find engine
        """
        if target is not None:
            found = server.has_storage_engine(target)
            if not found and fail:
                raise UtilError(message)
            elif not found and not quiet:
                print message

    server.get_storage_engines()
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


def add_rpl_user(parser):
    """Add the --rpl-user option.

    parser[in]        the parser instance
    """
    parser.add_option("--rpl-user", action="store", dest="rpl_user",
                      type="string",
                      help="the user and password for the replication "
                           "user requirement, in the form: <user>[:<password>]"
                           " or <login-path>. E.g. rpl:passwd")


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
        rpl_mode_both = (", and 'both' = include 'master' and 'slave' options "
                         "where applicable")
    parser.add_option("--rpl", "--replication", dest="rpl_mode",
                      action="store", help="include replication information. "
                      "Choices: 'master' = include the CHANGE MASTER command "
                      "using the source server as the master, "
                      "'slave' = include the CHANGE MASTER command for "
                      "the source server's master (only works if the source "
                      "server is a slave){0}.".format(rpl_mode_both),
                      choices=rpl_mode_options)
    if add_file:
        parser.add_option("--rpl-file", "--replication-file", dest="rpl_file",
                          action="store", help="path and file name to place "
                          "the replication information generated. Valid on if "
                          "the --rpl option is specified.")


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


def add_discover_slaves_option(parser):
    """Add the --discover-slaves-login option.

    This method adds the --discover-slaves-login option that is used to
    discover the list of slaves associated to the specified login (user and
    password).

    parser[in]      the parser instance.
    """
    parser.add_option("--discover-slaves-login", action="store",
                      dest="discover", default=None, type="string",
                      help="at startup, query master for all registered "
                      "slaves and use the user name and password specified to "
                      "connect. Supply the user and password in the form "
                      "<user>[:<password>] or <login-path>. For example, "
                      "--discover-slaves-login=joe:secret will use 'joe' as "
                      "the user and 'secret' as the password for each "
                      "discovered slave.")


def add_log_option(parser):
    """Add the --log option.

    This method adds the --log option that is used the specify the target file
    for logging messages from the utility.

    parser[in]      the parser instance.
    """
    parser.add_option("--log", action="store", dest="log_file", default=None,
                      type="string", help="specify a log file to use for "
                      "logging messages")


def add_master_option(parser):
    """Add the --master option.

    This method adds the --master option that is used to specify the connection
    string for the server with the master role.

    parser[in]      the parser instance.
    """
    parser.add_option("--master", action="store", dest="master", default=None,
                      type="string", help="connection information for master "
                      "server in the form: <user>[:<password>]@<host>[:<port>]"
                      "[:<socket>] or <login-path>[:<port>][:<socket>]")


def add_slaves_option(parser):
    """Add the --slaves option.

    This method adds the --slaves option that is used to specify a list of
    slaves, more precisely their connection strings (separated by comma).

    parser[in]      the parser instance.
    """
    parser.add_option("--slaves", action="store", dest="slaves",
                      type="string", default=None,
                      help="connection information for slave servers in "
                      "the form: <user>[:<password>]@<host>[:<port>]"
                      "[:<socket>] or <login-path>[:<port>][:<socket>]. "
                      "List multiple slaves in comma-separated list.")


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
      --script-threshold

    parser[in]        the parser instance
    """
    parser.add_option("--candidates", action="store", dest="candidates",
                      type="string", default=None,
                      help="connection information for candidate slave servers"
                      " for failover in the form: <user>[:<password>]@<host>[:"
                      "<port>][:<socket>] or <login-path>[:<port>][:<socket>]."
                      " Valid only with failover command. List multiple slaves"
                      " in comma-separated list.")

    add_discover_slaves_option(parser)

    parser.add_option("--exec-after", action="store", dest="exec_after",
                      default=None, type="string", help="name of script to "
                      "execute after failover or switchover")

    parser.add_option("--exec-before", action="store", dest="exec_before",
                      default=None, type="string", help="name of script to "
                      "execute before failover or switchover")

    add_log_option(parser)

    parser.add_option("--log-age", action="store", dest="log_age", default=7,
                      type="int", help="specify maximum age of log entries in "
                      "days. Entries older than this will be purged on "
                      "startup. Default = 7 days.")

    add_master_option(parser)

    parser.add_option("--max-position", action="store", dest="max_position",
                      default=0, type="int", help="used to detect slave "
                      "delay. The maximum difference between the master's "
                      "log position and the slave's reported read position of "
                      "the master. A value greater than this means the slave "
                      "is too far behind the master. Default is 0.")

    parser.add_option("--ping", action="store", dest="ping", default=None,
                      help="Number of ping attempts for detecting downed "
                      "server.")

    parser.add_option("--seconds-behind", action="store", dest="max_delay",
                      default=0, type="int", help="used to detect slave "
                      "delay. The maximum number of seconds behind the master "
                      "permitted before slave is considered behind the "
                      "master. Default is 0.")

    add_slaves_option(parser)

    parser.add_option("--timeout", action="store", dest="timeout", default=300,
                      help="maximum timeout in seconds to wait for each "
                      "replication command to complete. For example, timeout "
                      "for slave waiting to catch up to master. "
                      "Default = 300.")

    parser.add_option("--script-threshold", action="store", default=None,
                      dest="script_threshold",
                      help="Value for external scripts to trigger aborting "
                      "the operation if result is greater than or equal to "
                      "the threshold. Default = None (no threshold "
                      "checking).")


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
    return MySQLConverter().quote(obj)


def parse_user_password(userpass_values, my_defaults_reader=None,
                        options=None):
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
    if options is None:
        options = {}
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


def check_dir_option(parser, opt_value, opt_name, check_access=False,
                     read_only=False):
    """ Check if the specified directory option is valid.

    Check if the value specified for the option is a valid directory, and if
    the user has appropriate access privileges. An appropriate  parser error
    is issued if the specified directory is invalid.

    parser[in]          Instance of the option parser (optparse).
    opt_value[in]       Value specified for the option.
    opt_name[in]        Option name (e.g., --basedir).
    check_access[in]    Flag specifying if the access privileges need to be
                        checked. By default, False (no access check).
    read_only[in]       Flag indicating if the access required is only for
                        read or read/write. By default, False (read/write
                        access). Note: only used if check_access=True.
    """
    # Check existence of specified directory.
    if opt_value and not os.path.isdir(get_absolute_path(opt_value)):
        parser.error("The specified path for {0} option is not a "
                     "directory: {1}".format(opt_name, opt_value))
    if check_access:
        mode = os.R_OK if read_only else os.R_OK | os.W_OK
        if not os.access(opt_value, mode):
            parser.error("You do not have enough privileges to access the "
                         "folder specified by {0}.".format(opt_name))


def get_absolute_path(path):
    """ Returns the absolute path.
    """
    return os.path.abspath(os.path.expanduser(os.path.normpath(path)))


def db_objects_list_to_dictionary(parser, obj_list, option_desc):
    """Process database object list and convert to a dictionary.

    Check the qualified name format of the given database objects and convert
    the given list of object to a dictionary organized by database names and
    sets of specific objects.

    Note: It is assumed that the given object list is obtained from the
    arguments or an option returned by the parser.

    parser[in]      Instance of the used option/arguments parser
    obj_list[in]    List of objects to process.
    option_desc[in] Short description of the option for the object list (e.g.,
                    "the --exclude option", "the database/table arguments") to
                    refer appropriately in any parsing error.

    returns a dictionary with the objects grouped by database (without
    duplicates). None value associated to a database entry means that all
    objects are to be considered.
    E.g. {'db_name1': set(['table1','table2']), 'db_name2': None}.
    """
    db_objs_dict = {}
    obj_name_regexp = re.compile(REGEXP_QUALIFIED_OBJ_NAME)
    for obj_name in obj_list:
        m_obj = obj_name_regexp.match(obj_name)
        if not m_obj:
            parser.error(PARSE_ERR_OBJ_NAME_FORMAT.format(
                obj_name=obj_name, option=option_desc
            ))
        else:
            db_name, obj_name = m_obj.groups()
            # Remove backtick quotes.
            db_name = remove_backtick_quoting(db_name) \
                if is_quoted_with_backticks(db_name) else db_name
            obj_name = remove_backtick_quoting(obj_name) \
                if obj_name and is_quoted_with_backticks(obj_name) \
                else obj_name
            # Add database object to result dictionary.
            if not obj_name:
                # If only the database is specified, then add entry with
                # db name and value None (to include all object) even if a
                # previous specific object was already added.
                if db_name in db_objs_dict:
                    if db_objs_dict[db_name]:
                        db_objs_dict[db_name] = None
                else:
                    db_objs_dict[db_name] = None
            else:
                # If a specific object object is given add it to the set
                # associated to the database, except if the database entry
                # is None (meaning that all objects are included).
                if db_name in db_objs_dict:
                    if db_objs_dict[db_name]:
                        db_objs_dict[db_name].add(obj_name)
                else:
                    db_objs_dict[db_name] = set([obj_name])
    return db_objs_dict


def check_password_security(options, args, prefix=""):
    """Check command line for passwords and report a warning.

    This method checks all options for passwords in the form ':%@'. If
    this pattern is found, the method with issue a warning to stdout and
    return True, else it returns False.

    Note: this allows us to make it possible to abort if command-line
          passwords are found (not the default...yet).

    options[in]     list of options
    args[in]        list of arguments
    prefix[in]      (optional) allows preface statement with # or something
                    for making the message a comment in-stream

    Returns - bool : False = no passwords, True = password found and msg shown
    """
    result = False
    for value in options.__dict__.values():
        if type(value) == list:
            for item in value:
                if find_password(item):
                    result = True
        else:
            if find_password(value):
                result = True
    for arg in args:
        if find_password(arg):
            result = True
    if result:
        print("{0}WARNING: Using a password on the command line interface"
              " can be insecure.".format(prefix))

    return result
