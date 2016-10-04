#!/usr/bin/env python
#
# Copyright (c) 2012, 2016, Oracle and/or its affiliates. All rights reserved.
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
This file contains the audit log file search utility which allows user to
retrieve log entries according to the specified search criteria (i.e.,
from specific users, search patterns, date ranges, or query types).
"""

import os.path
import sys

from mysql.utilities.common.tools import check_python_version
from mysql.utilities import VERSION_FRM
from mysql.utilities.exception import UtilError
from mysql.utilities.command import audit_log
from mysql.utilities.command.audit_log import AuditLog
from mysql.utilities.common import pattern_matching
from mysql.utilities.common.tools import check_connector_python
from mysql.utilities.common.options import (add_verbosity, add_regexp,
                                            add_format_option_with_extras,
                                            CaseInsensitiveChoicesOption,
                                            check_date_time,
                                            get_value_intervals_list,
                                            license_callback,
                                            UtilitiesParser,
                                            check_password_security)

# Check Python version compatibility
check_python_version()


class MyParser(UtilitiesParser):
    """Custom class to set the epilog.
    """
    def format_epilog(self, formatter):
        return self.epilog

# Constants
NAME = "MySQL Utilities - mysqlauditgrep "
DESCRIPTION = "mysqlauditgrep - audit log search utility "
USAGE = "%prog [options] AUDIT_LOG_FILE "

# Check for connector/python
if not check_connector_python():
    sys.exit(1)

if __name__ == '__main__':
    # Setup the command parser
    program = os.path.basename(sys.argv[0]).replace(".py", "")
    parser = MyParser(
        version=VERSION_FRM.format(program=program),
        description=DESCRIPTION,
        usage=USAGE,
        add_help_option=False,
        option_class=CaseInsensitiveChoicesOption,
        epilog="",
        prog=program
    )

    # Default option to provide help information
    parser.add_option("--help", action="help",
                      help="display this help message and exit")

    # Add --License option
    parser.add_option("--license", action='callback',
                      callback=license_callback,
                      help="display program's license and exit")

    # Setup utility-specific options:

    # Output format, default is initially set to None to determine the correct
    # behavior when no search criteria is specified.
    add_format_option_with_extras(parser, "display the output in either GRID "
                                          "(default), TAB, CSV, VERTICAL and "
                                          "RAW format", None, ['raw'])

    # Search criteria to find entries for specified users
    parser.add_option("--users", "-u", action="store", dest="users",
                      type="string", default=None,
                      help="find log entries by user name. Accepts a comma-"
                           "separated list of user names, for example: "
                           "joe,sally,nick")

    # Show audit log file statistics
    parser.add_option("--file-stats", action="store_true", default=False,
                      dest="stats", help="display the audit log statistics.")

    # Search criteria to retrieve entries starting from a specific date/time
    parser.add_option("--start-date", action="store", dest="start_date",
                      type="string", default=None,
                      help="retrieve log entries starting from the specified "
                      "date/time. If not specified or the value is 0, all "
                      "entries from the start of the log are displayed. "
                      "Accepted formats: yyyy-mm-ddThh:mm:ss or yyyy-mm-dd.")

    # Search criteria to retrieve entries until the specific date/time
    parser.add_option("--end-date", action="store", dest="end_date",
                      type="string", default=None,
                      help="retrieve log entries until the specified "
                           "date/time. If not specified or the value is 0, "
                           "all entries to the end of the log are displayed. "
                           "Accepted formats: yyyy-mm-ddThh:mm:ss or "
                           "yyyy-mm-dd.")

    # Search pattern to retrieve matching entries
    parser.add_option("-e", "--pattern", action="store", dest="pattern",
                      type="string", default=None,
                      help="search pattern to retrieve matching entries.")

    # Search criteria to retrieve entries from the given SQL stmt/cmd types
    parser.add_option("--query-type", action="store", dest="query_type",
                      type="string", default=None,
                      help="search for all SQL statements/commands from the "
                           "given list of commands. Accepts a comma-separated "
                           "list of commands. Supported values: "
                           "{0}".format(", ".join(audit_log.QUERY_TYPES)))

    # Search criteria to retrieve entries from the given SQL stmt/cmd types
    parser.add_option("--event-type", action="store", dest="event_type",
                      type="string", default=None,
                      help="search for all recorded event types from the "
                           "given list of supported log events. Accepts a "
                           "comma-separated list of event types. "
                           "Supported values: "
                           "{0}".format(", ".join(audit_log.EVENT_TYPES)))

    # Search criteria to retrieve entries with the specified status.
    parser.add_option("--status", action="store", dest="status",
                      type="string", default=None,
                      help="search for all entries with the specified status "
                           "values. Accepts a comma-separated list of "
                           "non-negative integers (corresponding to MySQL "
                           "error codes) or intervals marked with a dash. "
                           "For example: 1051,1068-1075,1109,1146.")

    # Add regexp option
    add_regexp(parser)

    # Add verbosity mode
    add_verbosity(parser, False)

    def exist_search_criteria():
        """Return true if at least one search criteria is specified.
        """
        return (opt.users or opt.start_date or opt.end_date or opt.pattern or
                opt.query_type or opt.event_type or opt.status)

    # Parse the command line arguments.
    opt, args = parser.parse_args()

    # Check security settings
    check_password_security(opt, args)

    # Perform error checking

    # Only one positional argument is allowed: the audit log file
    num_args = len(args)
    if num_args < 1:
        parser.error("You must specify the audit log file to be processed.")
    elif num_args > 1:
        parser.error("You can only process one audit log file at a time.")

    # Check if the specified argument is a file
    if not os.path.isfile(args[0]):
        parser.error("The specified argument is not a file: %s" % args[0])

    # Check date/time ranges
    start_date = None
    if opt.start_date and opt.start_date != "0":
        start_date = check_date_time(parser, opt.start_date, 'start')
    end_date = None
    if opt.end_date and opt.end_date != "0":
        end_date = check_date_time(parser, opt.end_date, 'end')

    # Check if the value specified for the --users option is valid
    users = None
    if opt.users:
        users = opt.users.split(",")
        users = [user for user in users if user]
        if len(users) <= 0:
            parser.error("The value for the option --users is not valid: "
                         "'{0}'".format(opt.users))

    # Check if the value specified for the --query-type option is valid
    query_types = None
    if opt.query_type:
        query_types = opt.query_type.split(",")
        # filter empty values and convert all to lower cases
        query_types = [q_type.lower() for q_type in query_types if q_type]
        if len(query_types) <= 0:
            parser.error("The value for the option --query-type is not "
                         "valid: '{0}'".format(opt.query_type))
        else:
            valid_qts = [q_type.lower() for q_type in audit_log.QUERY_TYPES]
            for qt in query_types:
                if qt not in valid_qts:
                    parser.error("The specified QUERY_TYPE value is not "
                                 "valid: '{0}'\nSupported values: {1}"
                                 "".format(qt, ",".join(valid_qts)))

    # Check if the value specified for the --event-type option is valid
    event_types = None
    if opt.event_type:
        # filter empty values and convert all to lower cases
        event_types = opt.event_type.split(",")
        event_types = [e_type.lower() for e_type in event_types if e_type]

        if len(event_types) <= 0:
            parser.error("The value for the option --event-type is not "
                         "valid: '{0}'".format(opt.event_type))
        else:
            valid_ets = [e_type.lower() for e_type in audit_log.EVENT_TYPES]
            for et in event_types:
                if et not in valid_ets:
                    parser.error("The specified EVENT_TYPE value is not "
                                 "valid: '{0}'\nSupported values: {1}"
                                 "".format(et, ",".join(valid_ets)))

    # Check specified pattern
    if opt.use_regexp and not opt.pattern:
        parser.error("The --pattern option is required if REGEXP option is "
                     "set.")

    pattern = opt.pattern
    if opt.pattern and not opt.use_regexp:
        # Convert SQL LIKE pattern to Python REGEXP
        pattern = pattern_matching.convertSQL_LIKE2REGEXP(opt.pattern)

    # Check if the values specified for the --status option are valid
    status_list = []
    if opt.status:
        status_list = get_value_intervals_list(parser, opt.status, '--status',
                                               'status')

    # Create dictionary of options
    options = {
        'log_name': args[0],
        'verbosity': opt.verbosity,
        'format': opt.format,
        'users': users,
        'start_date': start_date,
        'end_date': end_date,
        'pattern': pattern,
        'use_regexp': opt.use_regexp,
        'query_type': query_types,
        'event_type': event_types,
        'status': status_list,
    }

    try:
        if not exist_search_criteria() and not (opt.format or opt.stats):
            print("#\n# No search criteria defined.\n#")
        else:
            # Create and init the AuditLog obj with the provided options
            log = AuditLog(options)

            # Open the audit log file
            log.open_log()

            # Parse the audit log file and apply filters
            log.parse_log()

            # Close the audit log
            log.close_log()

            if opt.stats:
                # Show audit log stats
                log.show_statistics()
            else:
                # Print the resulting data (to the sdtout) in the specified
                # format
                log.output_formatted_log()

    except UtilError:
        _, e, _ = sys.exc_info()
        print("ERROR: {0}".format(e.errmsg))
        sys.exit(1)

    sys.exit(0)
