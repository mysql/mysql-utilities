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
This file contains features to parse an audit log file, including
searching and displaying the results.
"""

import re

from mysql.utilities.common.audit_log_reader import AuditLogReader
from mysql.utilities.exception import UtilError


class AuditLogParser(AuditLogReader):
    """The AuditLogParser class is used to parse the audit log file, applying
    search criterion and filtering the logged data.
    """

    def __init__(self, options):
        """Constructor

        options[in]       dictionary of options (e.g. log_name and verbosity)
        """
        self.options = options
        AuditLogReader.__init__(self, options)
        self.header_rows = []
        self.connects = []
        self.rows = []
        self.connection_ids = []

        # Compile regexp pattern
        self.regexp_pattern = None
        if self.options['pattern']:
            try:
                self.regexp_pattern = re.compile(self.options['pattern'])
            except:
                raise UtilError("Invalid Pattern: " + self.options['pattern'])

        # Add a space after the query type to reduce false positives.
        # Note: Although not perfect, this simple trick considerably reduce
        # false positives, avoiding the use of complex regex (with lower
        # performance).
        self.match_qtypes = []  # list of matching SQL statement/command types.
        self.regexp_comment = None
        self.regexp_quoted = None
        self.regexp_backtick = None
        if self.options['query_type']:
            # Generate strings to match query types
            for qt in self.options['query_type']:
                if qt == "commit":
                    # COMMIT is an exception (can appear alone without spaces)
                    self.match_qtypes.append(qt)
                else:
                    self.match_qtypes.append("{0} ".format(qt))
            # Compile regexp to match comments (/*...*/) to be ignored/removed.
            self.regexp_comment = re.compile(r'/\*.*?\*/', re.DOTALL)
            # Compile regexp to match single quoted text ('...') to be ignored.
            self.regexp_quoted = re.compile(r"'.*?'", re.DOTALL)
            # Compile regexp to match text between backticks (`) to be ignored.
            self.regexp_backtick = re.compile(r'`.*?`', re.DOTALL)

    def parse_log(self):
        """Parse audit log records, apply search criteria and store results.
        """
        # Find and store records matching search criteria
        for record, line in self.get_next_record():
            name = record.get("NAME")
            name_case = name.upper()
            # The variable matching_record is used to avoid unnecessary
            # executions the match_* function of the remaining search criteria
            # to check, as it suffice that one match fails to not store the
            # records in the results. This implementation technique was applied
            # to avoid the use of too deep nested if-else statements that will
            # make the code more complex and difficult to read and understand,
            # trying to optimize the execution performance.
            matching_record = True
            if name_case == 'AUDIT':
                # Store audit start record
                self.header_rows.append(record)

            # Apply filters and search criteria
            if self.options['users']:
                self._track_new_users_connection_id(record, name_case)
                # Check if record matches users search criteria
                if not self.match_users(record):
                    matching_record = False

            # Check if record matches event type criteria
            if (matching_record and self.options['event_type'] and
                    not self.match_event_type(record,
                                              self.options['event_type'])):
                matching_record = False

            # Check if record matches status criteria
            if (matching_record and self.options['status'] and
                    not self.match_status(record, self.options['status'])):
                matching_record = False

            # Check if record matches datetime range criteria
            if (matching_record and
                    not self.match_datetime_range(record,
                                                  self.options['start_date'],
                                                  self.options['end_date'])):
                matching_record = False

            # Check if record matches query type criteria
            if (matching_record and self.options['query_type'] and
                    not self.match_query_type(record)):
                matching_record = False

            # Search attributes values for matching pattern
            if (matching_record and self.regexp_pattern and
                    not self.match_pattern(record)):
                matching_record = False

            # Store record into resulting rows (i.e., survived defined filters)
            if matching_record:
                if self.options['format'] == 'raw':
                    self.rows.append(line)
                else:
                    self.rows.append(record)

    def retrieve_rows(self):
        """Retrieve the resulting entries from the log parsing process
        """
        return self.rows if self.rows != [] else None

    def _track_new_users_connection_id(self, record, name_upper):
        """Track CONNECT records and store information of users and associated
        connection IDs.
        """
        user = record.get("USER", None)
        priv_user = record.get("PRIV_USER", None)

        # Register new connection_id (and corresponding user)
        if (name_upper.upper() == "CONNECT" and
                (user and (user in self.options['users'])) or
                (priv_user and (priv_user in self.options['users']))):
            self.connection_ids.append((user, priv_user,
                                        record.get("CONNECTION_ID")))

    def match_users(self, record):
        """Match users.

        Check if the given record match the user search criteria.
        Returns True if the record matches one of the specified users.

        record[in] audit log record to check
        """
        for con_id in self.connection_ids:
            if record.get('CONNECTION_ID', None) == con_id[2]:
                # Add user columns
                record['USER'] = con_id[0]
                record['PRIV_USER'] = con_id[1]
                # Add server_id column
                if self.header_rows:
                    record['SERVER_ID'] = self.header_rows[0]['SERVER_ID']
                return True
        return False

    @staticmethod
    def match_datetime_range(record, start_date, end_date):
        """Match date/time range.

        Check if the given record match the datetime range criteria.
        Returns True if the record matches the specified date range.

        record[in] audit log record to check;
        start_date[in] start date/time of the record (inclusive);
        end_date[in] end date/time of the record (inclusive);
        """
        if (start_date and (record.get('TIMESTAMP', None) < start_date)) or \
           (end_date and (end_date < record.get('TIMESTAMP', None))):
            # Not within datetime range
            return False
        else:
            return True

    def match_pattern(self, record):
        """Match REGEXP pattern.

        Check if the given record matches the defined pattern.
        Returns True if one of the record values matches the pattern.

        record[in] audit log record to check;
        """
        for val in record.values():
            if val and self.regexp_pattern.match(val):
                return True
        return False

    def match_query_type(self, record):
        """Match query types.

        Check if the given record matches one of the given query types.
        Returns True if the record possesses a SQL statement/command that
        matches one of the query types from the given list of query types.

        record[in]          audit log record to check;
        """
        sqltext = record.get('SQLTEXT', None)
        if sqltext:
            # Ignore (i.e., remove) comments in query.
            if self.regexp_comment:
                sqltext = re.sub(self.regexp_comment, '', sqltext)
            # Ignore (i.e., remove) quoted text in query.
            if self.regexp_quoted:
                sqltext = re.sub(self.regexp_quoted, '', sqltext)
            # Ignore (i.e., remove) names quoted with backticks in query.
            if self.regexp_backtick:
                sqltext = re.sub(self.regexp_backtick, '', sqltext)
            # Search query types strings inside text.
            sqltext = sqltext.lower()
            for qtype in self.match_qtypes:
                # Handle specific query-types to avoid false positives.
                if (qtype.startswith('set') and
                        ('insert ' in sqltext or 'update ' in sqltext)):
                    # Do not match SET in INSERT or UPDATE queries.
                    continue
                if (qtype.startswith('prepare') and
                        ('drop ' in sqltext or 'deallocate ' in sqltext)):
                    # Do not match PREPARE in DROP or DEALLOCATE queries.
                    continue
                # Check if query type is found.
                if qtype in sqltext:
                    return True
        return False

    @staticmethod
    def match_event_type(record, event_types):
        """Match audit log event/record type.

        Check if the given record matches one of the given event types.
        Returns True if the record type (i.e., logged event) matches one of the
        types from the given list of event types.

        record[in] audit log record to check;
        event_types[in] list of matching record/event types;
        """
        name = record.get('NAME').lower()
        return(name in event_types)

    @staticmethod
    def match_status(record, status_list):
        """Match the record status.

        Check if the given record match the specified status criteria.

        record[in]          audit log record to check;
        status_list[in]     list of status values or intervals (representing
                            MySQL error codes) to match;

        Returns True if the record status matches one of the specified values
        or intervals in the list.
        """
        rec_status = record.get('STATUS', None)
        if rec_status:
            rec_status = int(rec_status)
            for status_val in status_list:
                # Check if the status value is an interval (tuple) or int
                if isinstance(status_val, tuple):
                    # It is an interval; Check if it contains the record
                    # status.
                    if status_val[0] <= rec_status <= status_val[1]:
                        return True
                else:
                    # Directly check if the status match (is equal).
                    if rec_status == status_val:
                        return True
        return False
