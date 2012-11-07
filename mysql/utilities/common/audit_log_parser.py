#
# Copyright (c) 2012 Oracle and/or its affiliates. All rights reserved.
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

    def parse_log(self):
        """Parse audit log records, apply search criteria and store results.
        """

        # Compile regexp pattern
        regexp_obj = None
        if self.options['pattern']:
            try:
                regexp_obj = re.compile(self.options['pattern'])
            except:
                raise UtilError("Invalid Pattern: " + self.options['pattern'])

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
                #Check if record matches users search criteria
                if not self.match_users(record):
                    matching_record = False

            # Check if record matches event type criteria
            if (matching_record and self.options['event_type']
                and not self.match_event_type(record,
                                              self.options['event_type'])):
                matching_record = False

            # Check if record matches datetime range criteria
            if (matching_record
                and not self.match_datetime_range(record,
                                                  self.options['start_date'],
                                                  self.options['end_date'])):
                matching_record = False

            # Check if record matches query type criteria
            if (matching_record and self.options['query_type']
                and not self.match_query_type(record,
                                              self.options['query_type'])):
                matching_record = False

            # Search attributes values for matching pattern
            if (matching_record and regexp_obj
                and not self.match_pattern(record, regexp_obj)):
                matching_record = False

            # Store record into resulting rows (i.e., survived defined filters)
            if matching_record:
                if self.options['format'] == 'raw':
                    self.rows.append(line)
                else:
                    self.rows.append(record)

    def retrieve_rows(self):
        """ Retrieve the resulting entries from the log parsing process
        """
        return self.rows if self.rows != [] else None

    def _track_new_users_connection_id(self, record, name_upper):
        """ Track CONNECT records and store information of users and associated
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
        """ Match users.

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

    def match_datetime_range(self, record, start_date, end_date):
        """ Match date/time range.

        Check if the given record match the datetime range criteria.
        Returns True if the record matches one of the specified users.

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

    def match_pattern(self, record, regexp_obj):
        """ Match REGEXP pattern.

        Check if the given record matches the defined pattern.
        Returns True if one of the record values matches the pattern.

        record[in] audit log record to check;
        regexp_obj[in] compiled regular expression object;
        """
        for val in record.values():
            if val and regexp_obj.match(val):
                return True
        return False

    def match_query_type(self, record, query_types):
        """ Match query types.

        Check if the given record matches one of the given query types.
        Returns True if the record possesses a SQL statement/command that
        matches one of the query types from the given list of query types.

        record[in] audit log record to check;
        query_types[in] list of matching SQL statement/command types;
        """
        sqltext = record.get('SQLTEXT', None)
        if sqltext:
            sqltext = sqltext.lower()
            for qtype in query_types:
                if qtype in sqltext:
                    return True
        return False

    def match_event_type(self, record, event_types):
        """ Match audit log event/record type.

        Check if the given record matches one of the given event types.
        Returns True if the record type (i.e., logged event) matches one of the
        types from the given list of event types.

        record[in] audit log record to check;
        event_types[in] list of matching record/event types;
        """
        name = record.get('NAME').lower()
        if name in event_types:
            return True
        else:
            return False
