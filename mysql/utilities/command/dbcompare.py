#!/usr/bin/env python
#
# Copyright (c) 2011, Oracle and/or its affiliates. All rights reserved.
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#

"""
This file contains the commands for checking consistency of two databases.
"""

import sys

from mysql.utilities.common.options import parse_connection
from mysql.utilities.exception import UtilError, UtilDBError

_PRINT_WIDTH = 75
_ROW_FORMAT = "# {0:{1}} {2:{3}} {4:{5}} {6:{7}} {8:{9}}"
_RPT_FORMAT = "{0:{1}} {2:{3}}"

_ERROR_DB_DIFF = "The object definitions do not match."
_ERROR_DB_MISSING = "The database {0} does not exist."
_ERROR_OBJECT_LIST = "The list of objects differs among database {0} and {1}."
_ERROR_ROW_COUNT = "Row counts are not the same among {0} and {1}.\n#"

_DEFAULT_OPTIONS = {
    "quiet"           : False,
    "verbosity"       : 0,
    "difftype"        : "differ",
    "run_all_tests"   : False,
    "width"           : 75,
    "no_object_check" : False,
    "no_diff"         : False,
    "no_row_count"    : False,
    "no_data"         : False,
    "transform"       : False,
}

class _CompareDBReport:
    """Print compare database report
    """
    
    def __init__(self, options):
        """Constructor
        
        options[in]    options for class
            width[in]      Width of report
            quiet[in]      If true, do not print commentary
                           (default = False)
        """
        self.width = options.get('width', _PRINT_WIDTH) - 2 # for '# '
        self.quiet = options.get('quiet', False)
        self.type_width = 9
        self.oper_width = 7
        self.desc_width = self.width - self.type_width - (3 * self.oper_width) - 4

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


    def report_errors(self, errors):
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
    from mysql.utilities.common.dbcompare import diff_objects
        
    # Check database create for differences
    if not options['no_diff']:
        # temporarily make the diff quiet to retrieve errors
        new_opt = {}
        new_opt.update(options)
        new_opt['quiet'] = True          # do not print messages
        new_opt['suppress_sql'] = True   # do not print SQL statements either
        res = diff_objects(server1, server2, db1, db2, new_opt)
        if res is not None:
            for row in res:
                print row
            print
            if not options['run_all_tests']:
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
    from mysql.utilities.common.dbcompare import get_common_objects
    from mysql.utilities.common.dbcompare import print_missing_list

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
                    print_missing_list(in_db1, server1_str, server2_str)
                    print "#"
                if len(in_db2) > 0:
                    print_missing_list(in_db2, server2_str, server1_str)
                    print "#"
            else:
                raise UtilError(_ERROR_OBJECT_LIST.format(db1, db2))

    # If in verbose mode, show count of object types.
    if options['verbosity'] > 1:
        objects = {
                'TABLE' : 0,
                 'VIEW' : 0,
              'TRIGGER' : 0,
            'PROCEDURE' : 0,
             'FUNCTION' : 0,
                'EVENT' : 0,
        }
        for item in in_both:
            obj_type = db1_conn.get_object_type(item[1][0])
            objects[obj_type] += 1
        print "Looking for object types table, view, trigger, procedure," + \
              " function, and event."
        print "Object types found common to both databases:"
        for object in objects:
            print " {0:>12} : {1}".format(object, objects[object])

    return in_both


def _compare_objects(server1, server2, obj1, obj2, reporter, options):
    """Compare object definitions and produce difference
    
    server1[in]       first server Server instance
    server2[in]       second server Server instance
    obj1[in]          first object
    obj2[in]          second object
    reporter[in]      database compare reporter class instance
    options[in]       options dictionary
    
    Returns list of errors
    """
    from mysql.utilities.common.dbcompare import diff_objects

    errors = []
    if not options['no_diff']:
        # For each database, compare objects
        # temporarily make the diff quiet to retrieve errors
        new_opt = {}
        new_opt.update(options)
        new_opt['quiet'] = True          # do not print messages
        new_opt['suppress_sql'] = True   # do not print SQL statements either
        res = diff_objects(server1, server2, obj1, obj2, new_opt)
        if res is not None:
            reporter.report_state('FAIL')
            errors.extend(res)
            if not options['run_all_tests']:
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
            if not options['run_all_tests']:
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
    
    Returns list of errors
    """
    from mysql.utilities.common.dbcompare import check_consistency, \
                                                 build_diff_list

    direction = options.get('changes-for', 'server1')
    difftype = options.get('difftype', 'unified')
    reverse = options.get('reverse', False)
    
    errors = []
    diff_server1 = []
    diff_server2 = []
    diff_list = []
    # For each table, do row data consistency check
    if not options['no_data']:
        try:
            # Do the comparison based on direction
            if direction == 'server1' or reverse:
                diff_server1 = check_consistency(server1, server2,
                                                 obj1, obj2, options)
            if direction == 'server2' or reverse:
                diff_server2 = check_consistency(server2, server1,
                                                 obj2, obj1, options)
                
            # if no differences, return
            if (diff_server1 is None and diff_server2 is None) or \
               (not reverse and direction == 'server1' and \
                diff_server1 is None) or \
               (not reverse and direction == 'server2' and \
                diff_server2 is None):
                reporter.report_state('pass')
                return errors
                    
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
            if len(diff_list) == 0:
                reporter.report_state('pass')
            else:
                reporter.report_state('FAIL')
                errors = diff_list
        except UtilError, e:
            if e.errmsg == "No primary key found.":
                reporter.report_state('SKIP')
                errors.append(e.errmsg)
            else:
                reporter.report_state('FAIL')
                if not options['run_all_tests']:
                    print
                    raise e
                else:
                    errors.append(e.errmsg)
    else:
        reporter.report_state('SKIP')

    return errors


def _check_option_defaults(options):
    """Set the defaults for options if they are not set.
    
    This prevents users from calling the method and its subordinates
    with missing options.
    """
    
    for opt_name in _DEFAULT_OPTIONS:
        if not opt_name in options:
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
    
    from mysql.utilities.common.database import Database
    from mysql.utilities.common.dbcompare import server_connect, \
                                                 get_create_object
    
    _check_option_defaults(options)
    
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

    message = "# Checking databases {0} on server1 and {1} on server2\n#"
    print message.format(db1, db2)
    
    # Check for database existance and CREATE differences
    _check_databases(server1, server2, db1, db2, options)

    # Get common objects and report discrepencies
    in_both = _check_objects(server1, server2, db1, db2,
                             db1_conn, db2_conn, options)

    reporter = _CompareDBReport(options)
    reporter.print_heading()
    
    # Remaining operations can occur in a loop one for each object.        
    success = True if len(in_both) > 0 else False
    for item in in_both:
        error_list = []
        obj_type = db1_conn.get_object_type(item[1][0])
        
        obj1 = "{0}.{1}".format(db1, item[1][0])
        obj2 = "{0}.{1}".format(db2, item[1][0])

        reporter.report_object(obj_type, item[1][0])

        # Check for differences in CREATE
        errors = _compare_objects(server1, server2, obj1, obj2,
                                  reporter, options)
        error_list.extend(errors)
        
        # Check row counts
        if obj_type == 'TABLE':
            errors = _check_row_counts(server1, server2, obj1, obj2,
                                       reporter, options)
            if len(errors) != 0:
                success = False
                error_list.extend(errors)
        else:
            reporter.report_state("-")
            
        # Check data consistency for tables
        if obj_type == 'TABLE':
            errors = _check_data_consistency(server1, server2, obj1, obj2,
                                             reporter, options)
            if len(errors) != 0:
                success = False
                error_list.extend(errors)
        else:
            reporter.report_state("-")
                    
        if options['verbosity'] > 0:
            print
            object1_create = get_create_object(server1, obj1, options)
            object2_create = get_create_object(server2, obj2, options)
          
        reporter.report_errors(error_list)
        
    return success

