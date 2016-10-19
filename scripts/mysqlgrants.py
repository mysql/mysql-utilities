#!/usr/bin/env python
#
# Copyright (c) 2015, 2016, Oracle and/or its affiliates. All rights reserved.
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
This file contains the privilege display utility. It is used to show
the list of users and their privileges over the set of objects presented by
the user.
"""

import os
import sys

from mysql.utilities.command.grants import check_grants
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.options import (setup_common_options,
                                            add_verbosity,
                                            db_objects_list_to_dictionary)

from mysql.utilities.common.server import connect_servers
from mysql.utilities.common.tools import (check_python_version,
                                          check_connector_python,
                                          join_and_build_str)

# Check Python version compatibility
from mysql.utilities.exception import UtilError, FormatError

check_python_version()

# Check for connector/python
if not check_connector_python():
    sys.exit(1)

# Constants
_VALID_PRIVS = set(["CREATE", "DROP", "GRANT OPTION", "LOCK TABLES",
                    "REFERENCES", "EVENT", "ALTER", "DELETE", "INDEX",
                    "INSERT", "SELECT", "UPDATE", "TRIGGER", "CREATE VIEW",
                    "CREATE TEMPORARY TABLES", "SHOW VIEW", "ALTER ROUTINE",
                    "CREATE ROUTINE", "EXECUTE", "FILE", "CREATE TABLESPACE",
                    "CREATE USER", "PROCESS", "RELOAD", "REPLICATION CLIENT",
                    "REPLICATION SLAVE", "SHOW DATABASES", "SHUTDOWN",
                    "SUPER", "ALL", "ALL PRIVILEGES", "USAGE", "REFERENCES"])

NAME = "MySQL Utilities - mysqlgrants"
DESCRIPTION = "mysqlgrants - display grants per object"
USAGE = ("%prog --server=user:pass@host:port \\\n"
         "                    [<db_name>[.<obj_name>]]")
EXTENDED_HELP = """
Introduction
------------
The mysqlgrants utility is designed to display the users who have access to a
list of objects and/or databases. It can also display the privileges grouped
by user and the raw GRANT statements.

Furthermore, if the user specifies a list of privileges, the utility shall
display those users who have all of the privileges listed (they are AND
conditions).

In order to use the utility, you need to specify at least one object to check.
To specify several objects at once, you should list each object as a separate
argument for the utility, using full qualified names as shown by the following
examples:

  # Get the list of users with their respective privileges for the 'db1'
  # database and 'db1'.'table1' table.

  $ mysqlgrants --server=root:pass@host1:3306 \\
                --show=user_grants db1 db1.table1

  # Get the list of users with both SELECT and UPDATE privileges on the 'db1'
  # database and 'db1'.'table1' table.

  $ mysqlgrants --server=root:pass@host1:3306 \\
                --show=users --privileges=SELECT,UPDATE db1 db1.table1

  # Get the list of users that have at least the TRIGGER and DROP privileges
  # for database 'db1' and 'db1'.'table1' table and show the list of SQL GRANT
  # statements that grant them those privileges.

  $ mysqlgrants --server=root:pass@host1:3306 \\
                --show=raw --privileges=TRIGGER,DROP db1 db1.table1

  # Get the list of users with specific privileges at the object level, for
  # all the objects of the database 'db1'.

  $ mysqlgrants --server=root:pass@host1:3306 --inherit-level=object db1.*

Helpful Hints
-------------
  - To use the --show=users option you need to specify at least one privilege
    using the --privilege option.

  - You can list the users that have specific privileges using the option
    --privileges. The user must have all privileges listed in order to be
    included in the result.

  - If you specify some privileges on the --privileges option that are not
    valid for all the specified objects,  any that do not apply are not
    included in the list. For example, the SELECT privilege will be
    ignored for stored routines and the EXECUTE privilege will be ignored for
    tables but both will be taken into account for databases.

  - The --inherit-level option can be used for filtering out global users, and
    also users with the same database level privileges at the object level.

"""

if __name__ == '__main__':
    # Setup the command parser (with common options).
    parser = setup_common_options(os.path.basename(sys.argv[0]), DESCRIPTION,
                                  USAGE, append=False, server=True,
                                  server_default=None,
                                  extended_help=EXTENDED_HELP)

    # Add verbose option (no --quiet option).
    add_verbosity(parser, False)

    # Add show mode options
    parser.add_option("--show", action="store",
                      dest="show_mode", type="choice",
                      default="user_grants",
                      choices=["users", "user_grants", "raw"],
                      help="controls the content of the report. If the value "
                           "USERS is specified, the report shows only the "
                           "list of users with any kind of grant over the "
                           "object. If USER_GRANTS is specified the reports "
                           "shows each user along with her list of privileges "
                           "for each object. Finally, specifying RAW the "
                           "utility returns each user along with the list of "
                           "SQL grant statements that have influence over the "
                           "specific object. Default is USER_GRANTS.")

    parser.add_option("--privileges", action="store", dest="privileges",
                      type="string", default=None,
                      help="minimum set of privileges that a user must have "
                           "for any given object. Unless a user has all the "
                           "privileges listed for a specific object, "
                           "she will not appear in the list of users with "
                           "privileges for that specific object. To list "
                           "multiple privileges, use a comma-separated list.")

    parser.add_option("--inherit-level", dest="inherit_level",
                      type="choice", default='global',
                      choices=["global", "database", "object"],
                      help="specify the level of inheritance that should be "
                           "taken into account. If OBJECT is specified, "
                           "global level and database level grants are not "
                           "inherited by objects. If DATABASE level is "
                           "specified global level grants are not inherited "
                           "by databases and objects inside those databases. "
                           "Finally, if GLOBAL level is specified, normal "
                           "inheritance rules are applied, global grants "
                           "apply to both databases and objects and database "
                           "level grants apply to the objects.")

    # Now we process the rest of the arguments.
    opt, args = parser.parse_args()

    if not opt.server:
        parser.error("You need to specify a server using the --server option.")

    # Parse server connection
    server_val = None
    try:
        server_val = parse_connection(opt.server, None, opt)
    except FormatError:
        _, err, _ = sys.exc_info()
        parser.error("Server connection values invalid: "
                     "{0!s}.".format(err))
    except UtilError:
        _, err, _ = sys.exc_info()
        parser.error("Server connection values invalid: "
                     "{0!s}.".format(err.errmsg))

    # The --show=users can only be used together with the privilege option
    if opt.show_mode == 'users' and not opt.privileges:
        parser.error("The --show=users can only be used if you specify a "
                     "list of privileges with the --privileges option.")

    conn_opts = {
        'quiet': True,
        'version': "5.1.30",
    }
    try:
        servers = connect_servers(server_val, None, conn_opts)
        sql_mode = servers[0].select_variable("SQL_MODE")
    except:
        sql_mode = ''

    # Process list objects for which grants will be shown
    # (check format errors).
    objects_to_include = {}
    if args:
        objects_to_include = db_objects_list_to_dictionary(
            parser, args, 'list of objects to show the grants',
            db_over_tables=False,
            sql_mode=sql_mode
        )
    else:
        parser.error("You need to specify at least one object (database, table"
                     " or routine) in order to get the list of grantees.")

    # Validate list of privileges:
    priv_list = None
    if opt.privileges:
        priv_list = [priv.upper() for priv in opt.privileges.split(',')]
        if opt.verbosity and opt.verbosity > 2:
            print("The list of supported privileges is {0}".format(
                join_and_build_str(sorted(_VALID_PRIVS))))
        for priv in priv_list:
            if priv not in _VALID_PRIVS:
                if priv == "PROXY":
                    print("# WARNING: PROXY privilege is not supported ("
                          "privilege ignored).")
                else:
                    parser.error("Unknown privilege: '{0}'. For a list of "
                                 "valid privileges, please check: http://dev."
                                 "mysql.com/doc/en/privileges-provided."
                                 "html".format(priv))

    # Set options for database operations.
    options = {
        "verbosity": 0 if opt.verbosity is None else opt.verbosity,
        "privileges": priv_list,
        "show_mode": opt.show_mode,
        "inherit_level": opt.inherit_level,
    }
    try:
        check_grants(server_val, options, objects_to_include)
    except UtilError:
        _, e, _ = sys.exc_info()
        print("ERROR: {0}".format(e.errmsg))
        sys.exit(1)
    except:
        _, e, _ = sys.exc_info()
        print("ERROR: {0}".format(e))
        sys.exit(1)

    print("#...done.")

    sys.exit()
