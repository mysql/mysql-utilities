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
This file contains the metagrep utility which allows users to search metadata.
"""

import os.path
import re
import sys

from mysql.utilities.common.tools import check_python_version
from mysql.utilities.command.grep import ObjectGrep, OBJECT_TYPES
from mysql.utilities.common.tools import check_connector_python
from mysql.utilities.common.options import (add_regexp, setup_common_options,
                                            add_format_option,
                                            add_character_set_option,
                                            get_ssl_dict,
                                            check_password_security)
from mysql.utilities.exception import UtilError

# Check Python version compatibility
check_python_version()

# Check for connector/python
if not check_connector_python():
    sys.exit(1)

if __name__ == '__main__':
    # Setup the command parser and setup server, help
    parser = setup_common_options(os.path.basename(sys.argv[0]),
                                  "mysqlmetagrep - search metadata",
                                  "%prog --server=user:pass@host:port:socket "
                                  "[options] pattern", True)

    # Add character set option
    add_character_set_option(parser)

    # Setup utility-specific options:
    parser.add_option("-b", "--body",
                      dest="check_body", action="store_true", default=False,
                      help="search the body of routines, triggers, and "
                           "events as well")

    def quote(string):
        """Quote a string
        """
        return "'" + string + "'"

    # Add some more advanced parsing here to handle types better.
    parser.add_option(
        '--search-objects', '--object-types',
        dest="object_types", default=','.join(OBJECT_TYPES),
        help=("the object type to search in: a comma-separated list of one or "
              "more of: {0}".format(', '.join([quote(obj_type)
                                               for obj_type in OBJECT_TYPES])))
    )

    # Add regexp
    add_regexp(parser)

    parser.add_option(
        "-p", "--print-sql", "--sql",
        dest="print_sql", action="store_true", default=False,
        help="print the statement instead of sending it to the server")
    parser.add_option(
        "-e", "--pattern",
        dest="pattern",
        help="pattern to use when matching. Required if the pattern looks "
             "like a connection specification.")
    parser.add_option(
        "--database",
        dest="database_pattern", default=None,
        help="only look at objects in databases matching this pattern")

    # Output format
    add_format_option(parser, "display the output in either grid (default), "
                      "tab, csv, or vertical format", "grid")

    options, args = parser.parse_args()

    # Check security settings
    check_password_security(options, args)

    _LOOKS_LIKE_CONNECTION_MSG = """Pattern '{pattern}' looks like a
    connection specification. Use --pattern if this is really what you
    want"""

    _AT_LEAST_ONE_SERVER_MSG = """You need at least one server if you're
    not using the --sql option"""

    _NO_SERVERS_ALLOWED_MSG = """You should not include servers in the
    call if you are using the --sql option"""

    # A --pattern is required.
    if not options.pattern:
        parser.error("No pattern supplied.")

    # Check that --sql option is not used with --server, and --server are
    # supplied if --sql is not used.
    if options.print_sql:
        if options.server is not None and len(options.server) > 0:
            parser.error(_NO_SERVERS_ALLOWED_MSG)
    else:
        if options.server is None or len(options.server) == 0:
            parser.error(_AT_LEAST_ONE_SERVER_MSG)

    object_types = re.split(r"\s*,\s*", options.object_types)

    try:
        command = ObjectGrep(options.pattern, options.database_pattern,
                             object_types, options.check_body,
                             options.use_regexp)
        if options.print_sql:
            print(command.sql())
        else:
            ssl_opts = get_ssl_dict(options)
            command.execute(options.server, format=options.format,
                            charset=options.charset, ssl_opts=ssl_opts)
    except UtilError:
        _, err, _ = sys.exc_info()
        sys.stderr.write("ERROR: {0}\n".format(err.errmsg))
        sys.exit(1)
    except:
        _, details, _ = sys.exc_info()
        sys.stderr.write("ERROR: {0}\n".format(details))
        sys.exit(1)

    sys.exit()
