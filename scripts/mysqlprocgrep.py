#!/usr/bin/python
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
This file contains the procgrep utility which allows users to search process
information.
"""

import os.path
import sys

from mysql.utilities.common.tools import check_python_version
from mysql.utilities.exception import EmptyResultError
from mysql.utilities.command.proc import (ProcessGrep, KILL_CONNECTION,
                                          KILL_QUERY, PRINT_PROCESS, ID, USER,
                                          HOST, DB, COMMAND, INFO, STATE)
from mysql.utilities.common.tools import check_connector_python
from mysql.utilities.common.options import (add_regexp, setup_common_options,
                                            add_verbosity, add_format_option,
                                            add_character_set_option,
                                            get_ssl_dict,
                                            check_password_security)
# Check Python version compatibility
check_python_version()


def add_pattern(option, opt, value, parser, field):
    """Callback used in optparse for the --match-<pattern> option.
    """
    entry = (field, value)
    try:
        getattr(parser.values, option.dest).append(entry)
    except AttributeError:
        setattr(parser.values, option.dest, [entry])

# Check for connector/python
if not check_connector_python():
    sys.exit(1)

if __name__ == '__main__':
    # Setup the command parser and setup server, help
    parser = setup_common_options(os.path.basename(sys.argv[0]),
                                  "mysqlprocgrep - search process information",
                                  "%prog --server=user:pass@host:port:socket "
                                  "[options]", True)

    # Add character set option
    add_character_set_option(parser)

    # Add regexp
    add_regexp(parser)

    parser.add_option(
        "-Q", "--print-sql", "--sql",
        dest="print_sql", action="store_true", default=False,
        help="print the statement instead of sending it to the server. If a "
             "kill option is submitted, a procedure will be generated "
             "containing the code for executing the kill."
    )
    parser.add_option(
        "--sql-body",
        dest="sql_body", action="store_true", default=False,
        help="only print the body of the procedure."
    )
    parser.add_option(
        "--kill-connection",
        action="append_const", const=KILL_CONNECTION,
        dest="actions", default=[],
        help="kill all matching connections."
    )
    parser.add_option(
        "--kill-query",
        action="append_const", const=KILL_QUERY,
        dest="actions", default=[],
        help="kill query for all matching processes."
    )
    parser.add_option(
        "--print",
        action="append_const", const=PRINT_PROCESS,
        dest="actions", default=[],
        help="print all matching processes."
    )

    # Output format
    add_format_option(parser, "display the output in either grid (default), "
                      "tab, csv, or vertical format", "grid")

    # Add verbosity mode
    add_verbosity(parser, False)

    # Adding the --match-* options
    for col in (ID, USER, HOST, DB, COMMAND, INFO, STATE):
        parser.add_option(
            "--match-" + col.lower(),
            action="callback", callback=add_pattern, callback_args=(col,),
            dest="matches", type="string", metavar="PATTERN", default=[],
            help="match the '{0}' column of the PROCESSLIST table.".format(col)
        )

    parser.add_option(
        "--age",
        dest="age", default=None,
        help="show only processes that have been in the current state more "
             "than a given time."
    )

    (options, args) = parser.parse_args()

    # Check security settings
    check_password_security(options, args)

    # Print SQL if only --sql-body is given
    if options.sql_body:
        options.print_sql = True

    if (options.server is None or len(options.server) == 0) \
            and not options.print_sql:
        parser.error("You need at least one server if you're not using the "
                     "--sql option")
    elif options.server is not None and len(options.server) > 0 \
            and options.print_sql:
        parser.error("You should not include servers in the call if you are "
                     "using the --sql option")

    # If no option was supplied, we print the processes by default
    if len(options.actions) == 0:
        options.actions.append(PRINT_PROCESS)

    try:
        command = ProcessGrep(options.matches, options.actions,
                              options.use_regexp,
                              age=options.age)
        if options.print_sql:
            print(command.sql(options.sql_body).strip())
        else:
            ssl_opts = get_ssl_dict(options)
            command.execute(options.server, format=options.format,
                            charset=options.charset, ssl_opts=ssl_opts)
    except EmptyResultError:
        _, details, _ = sys.exc_info()
        sys.stderr.write("No matches\n")
        sys.exit(1)
    except:
        _, details, _ = sys.exc_info()
        sys.stderr.write('ERROR: {0}\n'.format(details))
        sys.exit(2)

    sys.exit()
