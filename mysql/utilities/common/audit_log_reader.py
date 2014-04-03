#
# Copyright (c) 2012, 2014, Oracle and/or its affiliates. All rights reserved.
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
    # pylint: disable=E0611
    from xml.etree.ElementTree import ParseError
except ImportError:
    # Instead use ExpatError for earlier python versions.
    from xml.parsers.expat import ExpatError as ParseError


_MANDATORY_FIELDS = ['NAME', 'TIMESTAMP']
_OPTIONAL_FIELDS = ['CONNECTION_ID', 'DB', 'HOST', 'IP', 'MYSQL_VERSION',
                    'OS_LOGIN', 'OS_VERSION', 'PRIV_USER', 'PROXY_USER',
                    'SERVER_ID', 'SQLTEXT', 'STARTUP_OPTIONS', 'STATUS',
                    'USER', 'VERSION']


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
        if ('<?xml ' in line) or ('<AUDIT>' in line) or ('</AUDIT>' in line):
            return True
        else:
            return False

    def get_next_record(self):
        """Get the next audit log record.

        Generator function that return the next audit log record.
        More precisely, it returns a tuple with a formatted record dict and
        the original record.
        """
        next_line = ""
        for line in self.log:
            if ((line.lstrip()).startswith('<AUDIT_RECORD') and
                    not line.endswith('/>\n')):
                next_line = "{0} ".format(line.strip('\n'))
                continue
            elif len(next_line) > 0 and not line.endswith('/>\n'):
                next_line = '{0}{1}'.format(next_line, line.strip('\n'))
                continue
            else:
                next_line += line
            log_entry = next_line
            next_line = ""
            try:
                yield (self._make_record(xml.fromstring(log_entry)), log_entry)
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

    def _make_record(self, node):
        """Make a dictionary record from the node element.

        The given node is converted to a dictionary record, reformatting
        as needed for the special characters.
        """
        # do mandatory fields
        record = {'NAME': node.get("NAME"), 'TIMESTAMP': node.get("TIMESTAMP")}
        # do optional fields
        for field in _OPTIONAL_FIELDS:
            if node.get(field, None):
                record[field] = self._do_replacements(node.get(field))
        return record
