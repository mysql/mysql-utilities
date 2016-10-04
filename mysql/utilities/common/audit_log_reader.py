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
This file contains the methods for reading the audit log.
"""

import os
import xml.etree.ElementTree as xml

from mysql.utilities.exception import UtilError

# Import appropriate XML exception to be compatible with python 2.6.
try:
    # Exception only available from python 2.7 (i.e., ElementTree 1.3)
    # pylint: disable=E0611,C0411
    from xml.etree.ElementTree import ParseError
except ImportError:
    # Instead use ExpatError for earlier python versions.
    # pylint: disable=C0411
    from xml.parsers.expat import ExpatError as ParseError


# Fields for the old format.
_MANDATORY_FIELDS = ['NAME', 'TIMESTAMP']
_OPTIONAL_FIELDS = ['CONNECTION_ID', 'DB', 'HOST', 'IP', 'MYSQL_VERSION',
                    'OS_LOGIN', 'OS_VERSION', 'PRIV_USER', 'PROXY_USER',
                    'SERVER_ID', 'SQLTEXT', 'STARTUP_OPTIONS', 'STATUS',
                    'USER', 'VERSION']

# Fields for the new format.
_NEW_MANDATORY_FIELDS = _MANDATORY_FIELDS + ['RECORD_ID']
_NEW_OPTIONAL_FIELDS = _OPTIONAL_FIELDS + ['COMMAND_CLASS', 'STATUS_CODE']


class AuditLogReader(object):
    """The AuditLogReader class is used to read the data stored in the audit
    log file. This class provide methods to open the audit log, get the next
    record, and close the file.
    """

    def __init__(self, options=None):
        """Constructor

        options[in]       dictionary of options (e.g. log_name and verbosity)
        """
        if options is None:
            options = {}
        self.verbosity = options.get('verbosity', 0)
        self.log_name = options.get('log_name', None)
        self.log = None
        self.tree = None
        self.root = None
        self.remote_file = False

    def __del__(self):
        """Destructor
        """
        if self.remote_file:
            os.unlink(self.log_name)

    def open_log(self):
        """Open the audit log file.
        """
        # Get the log from a remote server
        # TODO : check to see if the log is local. If not, attempt
        #        to log into the server via rsh and copy the file locally.
        self.remote_file = False
        if not self.log_name or not os.path.exists(self.log_name):
            raise UtilError("Cannot read log file '%s'." % self.log_name)
        self.log = open(self.log_name)

    def close_log(self):
        """Close the previously opened audit log.
        """
        self.log.close()

    @staticmethod
    def _validXML(line):
        """Check if line is a valid XML element, apart from audit records.
        """
        return (('<?xml ' in line) or
                ('<AUDIT>' in line) or ('</AUDIT>' in line))

    def get_next_record(self):
        """Get the next audit log record.

        Generator function that return the next audit log record.
        More precisely, it returns a tuple with a formatted record dict and
        the original record.
        """
        next_line = ""
        new_format = False
        multiline = False
        for line in self.log:
            if line.lstrip().startswith('<AUDIT_RECORD>'):
                # Found first record line in the new format.
                new_format = True
                multiline = True
                next_line = line
                continue
            elif (line.lstrip().startswith('<AUDIT_RECORD') and
                  not line.endswith('/>\n')):
                # Found (first) record line in the old format.
                next_line = "{0} ".format(line.strip('\n'))
                if not line.endswith('/>\n'):
                    multiline = True
                    continue
            elif multiline:
                if ((new_format and
                     line.strip().endswith('</AUDIT_RECORD>')) or
                        (not new_format and line.endswith('/>\n'))):
                    # Detect end of record in the old and new format and
                    # append last record line.
                    next_line += line
                else:
                    if not line.strip().startswith('<'):
                        # Handle SQL queries broke into multiple lines,
                        # removing newline characters.
                        next_line = '{0}{1}'.format(next_line.strip('\n'),
                                                    line.strip('\n'))
                    else:
                        next_line += line
                    continue
            else:
                next_line += line
            log_entry = next_line
            next_line = ""
            try:
                yield (
                    self._make_record(xml.fromstring(log_entry), new_format),
                    log_entry
                )
            except (ParseError, SyntaxError):
                # SyntaxError is also caught for compatibility reasons with
                # python 2.6. In case an ExpatError which does not inherits
                # from SyntaxError is used as a ParseError.
                if not self._validXML(log_entry):
                    raise UtilError("Malformed XML - Cannot parse log file: "
                                    "'{0}'\nInvalid XML element: "
                                    "{1!r}".format(self.log_name, log_entry))

    @staticmethod
    def _do_replacements(old_str):
        """Replace special masked characters.
        """
        new_str = old_str.replace("&lt;", "<")
        new_str = new_str.replace("&gt;", ">")
        new_str = new_str.replace("&quot;", '"')
        new_str = new_str.replace("&amp;", "&")
        return new_str

    def _make_record(self, node, new_format=False):
        """Make a dictionary record from the node element.

        The given node is converted to a dictionary record, reformatting
        as needed for the special characters.

        node[in]        XML node holding a single audit log record.
        new_format[in]  Flag indicating if the new XML format is used for the
                        audit log record. By default False (old format used).

        Return a dictionary with the data in the given audit log record.
        """
        if new_format:
            # Handle audit record in the new format.
            # Do mandatory fields.
            # Note: Use dict constructor for compatibility with Python 2.6.
            record = dict((field, node.find(field).text)
                          for field in _NEW_MANDATORY_FIELDS)
            # Do optional fields.
            for field in _NEW_OPTIONAL_FIELDS:
                field_node = node.find(field)
                if field_node is not None and field_node.text:
                    record[field] = self._do_replacements(field_node.text)
        else:
            # Handle audit record in the old format.
            # Do mandatory fields.
            # Note: Use dict constructor for compatibility with Python 2.6.
            record = dict((field, node.get(field))
                          for field in _MANDATORY_FIELDS)
            # Do optional fields.
            for field in _OPTIONAL_FIELDS:
                if node.get(field, None):
                    record[field] = self._do_replacements(node.get(field))
        return record
