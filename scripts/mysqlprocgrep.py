#!/usr/bin/python

import getpass
import optparse
import os.path
import sys

from mysql.utilities import VERSION_FRM
from mysql.utilities.command.proc import *
from mysql.utilities.exception import FormatError, EmptyResultError
from mysql.utilities.common.options import parse_connection, add_regexp
from mysql.utilities.common.options import setup_common_options
from mysql.utilities.common.options import add_verbosity
from mysql.utilities.common.options import add_format_option
from mysql.utilities.exception import UtilError

def add_pattern(option, opt, value, parser, field):
    entry = (field, value)
    try:
        getattr(parser.values, option.dest).append(entry)
    except AttributeError:
        setattr(parser.values, option.dest, [entry])

# Setup the command parser and setup server, help
parser = setup_common_options(os.path.basename(sys.argv[0]),
                              "mysqlprocgrep - search process information",
                              "%prog --server=user:pass@host:port:socket "
                              "[options]", True)
# Add regexp
add_regexp(parser)

parser.add_option(
    "-Q", "--print-sql", "--sql",
    dest="print_sql", action="store_true", default=False,
    help="print the statement instead of sending it to the server. If a kill option is submitted, a procedure will be generated containing the code for executing the kill.")
parser.add_option(
    "--sql-body",
    dest="sql_body", action="store_true", default=False,
    help="only print the body of the procedure.")
parser.add_option(
    "--kill-connection",
    action="append_const", const=KILL_CONNECTION,
    dest="actions", default=[],
    help="kill all matching connections.")
parser.add_option(
    "--kill-query",
    action="append_const", const=KILL_QUERY,
    dest="actions", default=[],
    help="kill query for all matching processes.")
parser.add_option(
    "--print",
    action="append_const", const=PRINT_PROCESS,
    dest="actions", default=[],
    help="print all matching processes.")

# Output format
add_format_option(parser, "display the output in either grid (default), "
                  "tab, csv, or vertical format", "grid")     

# Add verbosity mode
add_verbosity(parser, False)

# Adding the --match-* options
for col in USER, HOST, DB, COMMAND, INFO, STATE:
    parser.add_option(
        "--match-" + col.lower(),
        action="callback", callback=add_pattern, callback_args=(col,),
        dest="matches", type="string", metavar="PATTERN", default=[],
        help="match the '{0}' column of the PROCESSLIST table".format(col))

parser.add_option(
    "--age",
    dest="age", default=None,
    help="show only processes that have been in the current state more than "
         "a given time")

(options, args) = parser.parse_args()

# Print SQL if only --sql-body is given
if options.sql_body:
    options.print_sql = True

if (options.server is None or len(options.server) == 0) and not options.print_sql:
    parser.error("You need at least one server if you're not using the --sql option")
elif options.server is not None and len(options.server) > 0 and options.print_sql:
    parser.error("You should not include servers in the call if you are using the --sql option")

# If no option was supplied, we print the processes by default
if len(options.actions) == 0:
    options.actions.append(PRINT_PROCESS)

try:
    command = ProcessGrep(options.matches, options.actions, options.use_regexp,
                          age=options.age)
    if options.print_sql:
        print command.sql(options.sql_body).strip()
    else:
        command.execute(options.server, format=options.format)
except EmptyResultError as details:
    print >>sys.stderr, "No matches"
    exit(1)
except Exception as details:
    print >>sys.stderr, 'ERROR:', details
    exit(2)

exit()
