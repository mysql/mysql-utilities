#
# Copyright (c) 2011, 2016, Oracle and/or its affiliates. All rights reserved.
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
This file contains the commands for checking consistency of two databases.
"""

from mysql.utilities.exception import UtilDBError, UtilError
from mysql.utilities.common.database import Database
from mysql.utilities.common.sql_transform import quote_with_backticks
from mysql.utilities.common.dbcompare import (diff_objects, get_common_objects,
                                              get_create_object,
                                              print_missing_list,
                                              server_connect,
                                              check_consistency,
                                              build_diff_list,
                                              DEFAULT_SPAN_KEY_SIZE)
from mysql.utilities.common.server import connect_servers

_PRINT_WIDTH = 75
_ROW_FORMAT = "# {0:{1}} {2:{3}} {4:{5}} {6:{7}} {8:{9}}"
_RPT_FORMAT = "{0:{1}} {2:{3}}"

_ERROR_DB_DIFF = "The object definitions do not match."
_ERROR_DB_MISSING = "The database {0} does not exist."
_ERROR_OBJECT_LIST = "The list of objects differs among database {0} and {1}."
_ERROR_ROW_COUNT = "Row counts are not the same among {0} and {1}.\n#"
_ERROR_DB_MISSING_ON_SERVER = "The database {0} on {1} does not exist on {2}."

_DEFAULT_OPTIONS = {
    "quiet": False,
    "verbosity": 0,
    "difftype": "differ",
    "run_all_tests": False,
    "width": 75,
    "no_object_check": False,
    "no_diff": False,
    "no_row_count": False,
    "no_data": False,
    "transform": False,
    "span_key_size": DEFAULT_SPAN_KEY_SIZE
}


class _CompareDBReport(object):
    """Print compare database report
    """

    def __init__(self, options):
        """Constructor

        options[in]    options for class
            width[in]      Width of report
            quiet[in]      If true, do not print commentary
                           (default = False)
        """
        self.width = options.get('width', _PRINT_WIDTH) - 2  # for '# '
        self.quiet = options.get('quiet', False)
        self.type_width = 9
        self.oper_width = 7
        self.desc_width = self.width - self.type_width - \
            (3 * self.oper_width) - 4

    def print_heading(self):
        """Print heading for database consistency
        """
        # Skip if quiet
        if self.quiet:
            return
        # Set the variable width global parameters here
        print _ROW_FORMAT.format(' ', self.type_width,
                                 ' ', self.desc_width,
                                 "Defn", self.oper_width,
                                 "Row", self.oper_width,
                                 "Data", self.oper_width)
        print _ROW_FORMAT.format("Type", self.type_width,
                                 "Object Name", self.desc_width,
                                 "Diff", self.oper_width,
                                 "Count", self.oper_width,
                                 "Check", self.oper_width)
        print "# %s" % ('-' * self.width),

    def report_object(self, obj_type, description):
        """Print the object type and description field

        obj_type[in]      type of the object(s) described
        description[in]   description of object(s)
        """
        # Skip if quiet
        if self.quiet:
            return
        print "\n#", _RPT_FORMAT.format(obj_type, self.type_width,
                                        description, self.desc_width),

    def report_state(self, state):
        """Print the results of a test.

        state[in]         state of the test
        """
        # Skip if quiet
        if self.quiet:
            return
        print "{0:<{1}}".format(state, self.oper_width),

    @staticmethod
    def report_errors(errors):
        """Print any errors encountered.

        errors[in]        list of strings to print
        """
        if len(errors) > 0:
            print "\n#"
        for line in errors:
            print line


def _check_databases(server1, server2, db1, db2, options):
    """Check databases

    server1[in]       first server Server instance
    server2[in]       second server Server instance
    db1[in]           first database
    db2[in]           second database
    options[in]       options dictionary

    Returns tuple - Database class instances for databases
    """

    # Check database create for differences
    if not options['no_diff']:
        # temporarily make the diff quiet to retrieve errors
        new_opt = {}
        new_opt.update(options)
        new_opt['quiet'] = True          # do not print messages
        new_opt['suppress_sql'] = True   # do not print SQL statements either
        res = diff_objects(server1, server2, db1, db2, new_opt, 'DATABASE')
        if res is not None:
            for row in res:
                print row
            print
            if not options['run_all_tests'] and \
                    not options.get('quiet', False):
                raise UtilError(_ERROR_DB_DIFF)


def _check_objects(server1, server2, db1, db2,
                   db1_conn, db2_conn, options):
    """Check number of objects

    server1[in]       first server Server instance
    server2[in]       second server Server instance
    db1[in]           first database
    db2[in]           second database
    db1_conn[in]      first Database instance
    db2_conn[in]      second Database instance
    options[in]       options dictionary

    Returns list of objects in both databases
    """

    differs = False
    quiet = options.get("quiet", False)

    # Check for same number of objects
    in_both, in_db1, in_db2 = get_common_objects(server1, server2,
                                                 db1, db2, False, options)
    in_both.sort()
    if not options['no_object_check']:
        server1_str = "server1." + db1
        if server1 == server2:
            server2_str = "server1." + db2
        else:
            server2_str = "server2." + db2
        if len(in_db1) or len(in_db2):
            if options['run_all_tests']:
                if len(in_db1) > 0:
                    differs = True
                    if not quiet:
                        print_missing_list(in_db1, server1_str, server2_str)
                        print "#"
                if len(in_db2) > 0:
                    differs = True
                    if not quiet:
                        print_missing_list(in_db2, server2_str, server1_str)
                        print "#"
            else:
                differs = True
                if not quiet:
                    raise UtilError(_ERROR_OBJECT_LIST.format(db1, db2))

    # If in verbose mode, show count of object types.
    if options['verbosity'] > 1:
        objects = {
            'TABLE': 0,
            'VIEW': 0,
            'TRIGGER': 0,
            'PROCEDURE': 0,
            'FUNCTION': 0,
            'EVENT': 0,
        }
        for item in in_both:
            obj_type = item[0]
            objects[obj_type] += 1
        print "Looking for object types table, view, trigger, procedure," + \
              " function, and event."
        print "Object types found common to both databases:"
        for obj in objects:
            print " {0:>12} : {1}".format(obj, objects[obj])

    return (in_both, differs)


def _compare_objects(server1, server2, obj1, obj2, reporter, options,
                     object_type):
    """Compare object definitions and produce difference

    server1[in]       first server Server instance
    server2[in]       second server Server instance
    obj1[in]          first object
    obj2[in]          second object
    reporter[in]      database compare reporter class instance
    options[in]       options dictionary
    object_type[in]   type of the objects to be compared (e.g., TABLE,
                      PROCEDURE, etc.).

    Returns list of errors
    """

    errors = []
    if not options['no_diff']:
        # For each database, compare objects
        # temporarily make the diff quiet to retrieve errors
        new_opt = {}
        new_opt.update(options)
        new_opt['quiet'] = True          # do not print messages
        new_opt['suppress_sql'] = True   # do not print SQL statements either
        res = diff_objects(server1, server2, obj1, obj2, new_opt, object_type)
        if res is not None:
            reporter.report_state('FAIL')
            errors.extend(res)
            if not options['run_all_tests'] and \
                    not options.get('quiet', False):
                raise UtilError(_ERROR_DB_DIFF)
        else:
            reporter.report_state('pass')
    else:
        reporter.report_state('SKIP')

    return errors


def _check_row_counts(server1, server2, obj1, obj2, reporter, options):
    """Compare row counts for tables

    server1[in]       first server Server instance
    server2[in]       second server Server instance
    obj1[in]          first object
    obj2[in]          second object
    reporter[in]      database compare reporter class instance
    options[in]       options dictionary

    Returns list of errors
    """
    errors = []
    if not options['no_row_count']:
        rows1 = server1.exec_query("SELECT COUNT(*) FROM " + obj1)
        rows2 = server2.exec_query("SELECT COUNT(*) FROM " + obj2)
        if rows1 != rows2:
            reporter.report_state('FAIL')
            msg = _ERROR_ROW_COUNT.format(obj1, obj2)
            if not options['run_all_tests'] and \
                    not options.get('quiet', False):
                raise UtilError(msg)
            else:
                errors.append("# %s" % msg)
        else:
            reporter.report_state('pass')
    else:
        reporter.report_state('SKIP')

    return errors


def _check_data_consistency(server1, server2, obj1, obj2, reporter, options):
    """Check data consistency

    server1[in]       first server Server instance
    server2[in]       second server Server instance
    obj1[in]          first object
    obj2[in]          second object
    reporter[in]      database compare reporter class instance
    options[in]       options dictionary

    Returns list of errors debug_msgs
    """
    direction = options.get('changes-for', 'server1')
    reverse = options.get('reverse', False)
    quiet = options.get('quiet', False)

    errors = []
    debug_msgs = []
    # For each table, do row data consistency check
    if not options['no_data']:
        reporter.report_state('-')
        try:
            # Do the comparison considering the direction.
            diff_server1, diff_server2 = check_consistency(
                server1, server2, obj1, obj2, options, diag_msgs=debug_msgs,
                reporter=reporter)

            # if no differences, return
            if (diff_server1 is None and diff_server2 is None) or \
                    (not reverse and direction == 'server1' and
                     diff_server1 is None) or \
                    (not reverse and direction == 'server2' and
                     diff_server2 is None):
                return errors, debug_msgs

            # Build diff list
            new_opts = options.copy()
            new_opts['data_diff'] = True
            if direction == 'server1':
                diff_list = build_diff_list(diff_server1, diff_server2,
                                            diff_server1, diff_server2,
                                            'server1', 'server2', new_opts)
            else:
                diff_list = build_diff_list(diff_server2, diff_server1,
                                            diff_server2, diff_server1,
                                            'server2', 'server1', new_opts)
            if diff_list:
                errors = diff_list
        except UtilError, e:
            if e.errmsg.endswith("not have an usable Index or primary key."):
                reporter.report_state('SKIP')
                errors.append("# {0}".format(e.errmsg))
            else:
                reporter.report_state('FAIL')
                if not options['run_all_tests']:
                    if not quiet:
                        print
                    raise e
                else:
                    errors.append(e.errmsg)

    else:
        reporter.report_state('SKIP')

    return errors, debug_msgs


def _check_option_defaults(options):
    """Set the defaults for options if they are not set.

    This prevents users from calling the method and its subordinates
    with missing options.
    """

    for opt_name in _DEFAULT_OPTIONS:
        if opt_name not in options:
            options[opt_name] = _DEFAULT_OPTIONS[opt_name]


def database_compare(server1_val, server2_val, db1, db2, options):
    """Perform a consistency check among two databases

    This method performs a database consistency check among two databases which
    ensures the databases exist, the objects match in number and type, the row
    counts match for all tables, and the data for each matching tables is
    consistent.

    If any errors or differences are found, the operation stops and the
    difference is printed.

    The following steps are therefore performed:

    1) check to make sure the databases exist and are the same definition
    2) check to make sure the same objects exist in each database
    3) for each object, ensure the object definitions match among the databases
    4) for each table, ensure the row counts are the same
    5) for each table, ensure the data is the same

    By default, the operation stops on any failure of any test. The caller can
    override this behavior by specifying run_all_tests = True in the options
    dictionary.

    TODO:   allow the user to skip object types (e.g. --skip-triggers, et. al.)

    server1_val[in]    a dictionary containing connection information for the
                       first server including:
                       (user, password, host, port, socket)
    server2_val[in]    a dictionary containing connection information for the
                       second server including:
                       (user, password, host, port, socket)
    db1[in]            the first database in the compare
    db2[in]            the second database in the compare
    options[in]        a dictionary containing the options for the operation:
                       (quiet, verbosity, difftype, run_all_tests)

    Returns bool True if all object match, False if partial match
    """

    _check_option_defaults(options)
    quiet = options.get("quiet", False)

    # Connect to servers
    server1, server2 = server_connect(server1_val, server2_val,
                                      db1, db2, options)

    # Check to see if databases exist
    db1_conn = Database(server1, db1, options)
    if not db1_conn.exists():
        raise UtilDBError(_ERROR_DB_MISSING.format(db1))

    db2_conn = Database(server2, db2, options)
    if not db2_conn.exists():
        raise UtilDBError(_ERROR_DB_MISSING.format(db2))

    # Print a different message is server2 is not defined
    if not quiet:
        if not server2_val:
            message = "# Checking databases {0} and {1} on server1\n#"
        else:
            message = ("# Checking databases {0} on server1 and {1} on "
                       "server2\n#")
        print(message.format(db1_conn.db_name, db2_conn.db_name))

    # Check for database existence and CREATE differences
    _check_databases(server1, server2, db1_conn.q_db_name, db2_conn.q_db_name,
                     options)

    # Get common objects and report discrepancies
    (in_both, differs) = _check_objects(server1, server2, db1, db2,
                                        db1_conn, db2_conn, options)
    success = not differs

    reporter = _CompareDBReport(options)
    reporter.print_heading()

    # Get sql_mode value from servers
    server1_sql_mode = server1.select_variable("SQL_MODE")
    server2_sql_mode = server2.select_variable("SQL_MODE")

    # Remaining operations can occur in a loop one for each object.
    for item in in_both:
        error_list = []
        debug_msgs = []
        # Set the object type
        obj_type = item[0]

        q_obj1 = "{0}.{1}".format(quote_with_backticks(db1, server1_sql_mode),
                                  quote_with_backticks(item[1][0],
                                                       server1_sql_mode))
        q_obj2 = "{0}.{1}".format(quote_with_backticks(db2, server2_sql_mode),
                                  quote_with_backticks(item[1][0],
                                                       server2_sql_mode))

        reporter.report_object(obj_type, item[1][0])

        # Check for differences in CREATE
        errors = _compare_objects(server1, server2, q_obj1, q_obj2,
                                  reporter, options, obj_type)
        error_list.extend(errors)

        # Check row counts
        if obj_type == 'TABLE':
            errors = _check_row_counts(server1, server2, q_obj1, q_obj2,
                                       reporter, options)
            if len(errors) != 0:
                error_list.extend(errors)
        else:
            reporter.report_state("-")

        # Check data consistency for tables
        if obj_type == 'TABLE':
            errors, debug_msgs = _check_data_consistency(server1, server2,
                                                         q_obj1, q_obj2,
                                                         reporter, options)
            if len(errors) != 0:
                error_list.extend(errors)
        else:
            reporter.report_state("-")

        if options['verbosity'] > 0:
            if not quiet:
                print
            get_create_object(server1, q_obj1, options, obj_type)
            get_create_object(server2, q_obj2, options, obj_type)

        if debug_msgs and options['verbosity'] > 2:
            reporter.report_errors(debug_msgs)

        if not quiet:
            reporter.report_errors(error_list)

        # Fail if errors are found
        if error_list:
            success = False

    return success


def compare_all_databases(server1_val, server2_val, exclude_list, options):
    """Perform a consistency check among all common databases on the servers

    This method gets all databases from the servers, prints any missing
    databases and performs a consistency check among all common databases.

    If any errors or differences are found, the operation will print the
    difference and continue.

    This method will return None if no databases to compare.
    """

    success = True
    quiet = options.get("quiet", False)

    # Connect to servers
    conn_options = {
        "quiet": options.get("quiet", False),
        "src_name": "server1",
        "dest_name": "server2",

    }
    server1, server2 = connect_servers(server1_val, server2_val, conn_options)

    # Check if the specified servers are the same
    if server2 is None or server1.port == server2.port and \
            server1.is_alias(server2.host):
        raise UtilError(
            "Specified servers are the same (server1={host1}:{port1} and "
            "server2={host2}:{port2}). Cannot compare all databases on the "
            "same server.".format(host1=server1.host, port1=server1.port,
                                  host2=getattr(server2, "host", server1.host),
                                  port2=getattr(server2, "port", server1.port))
        )

    # Get all databases, except those used in --exclude
    get_dbs_query = """
        SELECT SCHEMA_NAME
        FROM INFORMATION_SCHEMA.SCHEMATA
        WHERE SCHEMA_NAME != 'INFORMATION_SCHEMA'
        AND SCHEMA_NAME != 'PERFORMANCE_SCHEMA'
        AND SCHEMA_NAME != 'mysql'
        AND SCHEMA_NAME != 'sys'
        {0}"""
    conditions = ""
    if exclude_list:
        # Add extra where to exclude databases in exclude_list
        operator = 'REGEXP' if options['use_regexp'] else 'LIKE'
        conditions = "AND {0}".format(" AND ".join(
            ["SCHEMA_NAME NOT {0} '{1}'".format(operator, db)
             for db in exclude_list]))

    server1_dbs = set(
        [db[0] for db in server1.exec_query(get_dbs_query.format(conditions))]
    )
    server2_dbs = set(
        [db[0] for db in server2.exec_query(get_dbs_query.format(conditions))]
    )

    # Check missing databases
    if options['changes-for'] == 'server1':
        diff_dbs = server1_dbs.difference(server2_dbs)
        for db in diff_dbs:
            msg = _ERROR_DB_MISSING_ON_SERVER.format(db, "server1", "server2")
            if not quiet:
                print("# {0}".format(msg))
    else:
        diff_dbs = server2_dbs.difference(server1_dbs)
        for db in diff_dbs:
            msg = _ERROR_DB_MISSING_ON_SERVER.format(db, "server2", "server1")
            if not quiet:
                print("# {0}".format(msg))

    # Compare databases in common
    common_dbs = server1_dbs.intersection(server2_dbs)
    if common_dbs:
        if not quiet:
            print("# Comparing databases: {0}".format(", ".join(common_dbs)))
    else:
        success = None
    for db in common_dbs:
        try:
            res = database_compare(server1_val, server2_val, db, db, options)
            if not res:
                success = False
            if not quiet:
                print("\n")
        except UtilError as err:
            print("ERROR: {0}\n".format(err.errmsg))
            success = False

    return success
