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

"""mysql.utilities"""

# Major, Minor, Patch, Status
VERSION = (1, 6, 5, 'GA', 0)
# Future versions will have to include only the X, Y (no Z).

VERSION_STRING = "%s.%s.%s" % VERSION[0:3]

COPYRIGHT = "2010, 2017 Oracle and/or its affiliates. All rights reserved."

COPYRIGHT_FULL = "Copyright (c) " + COPYRIGHT + """
This is a release of dual licensed MySQL Utilities. For the avoidance of
doubt, this particular copy of the software is released
under the version 2 of the GNU General Public License.
MySQL Utilities is brought to you by Oracle.
"""

LICENSE = "GPLv2"

VERSION_FRM = ("MySQL Utilities {program} version %s \n"
               "License type: %s" % (VERSION_STRING, LICENSE))

LICENSE_FRM = (VERSION_FRM + "\n" + COPYRIGHT_FULL)
PYTHON_MIN_VERSION = (2, 6, 0)
PYTHON_MAX_VERSION = (3, 0, 0)
CONNECTOR_MIN_VERSION = (1, 2, 1)

# This dictionary has to be updated whenever a utility is added.
# the format to use is:
# '<utility_name>': (<PYTHON_MIN_VERSION>, <PYTHON_MAX_VERSION>)
AVAILABLE_UTILITIES = {
    'mysqlauditadmin': (),
    'mysqlauditgrep': (),
    'mysqlbinlogmove': (),
    'mysqlbinlogpurge': (),
    'mysqlbinlogrotate': (),
    'mysqldbcompare': (),
    'mysqldbcopy': (),
    'mysqldbexport': (),
    'mysqldbimport': (),
    'mysqldiff': (),
    'mysqldiskusage': (),
    'mysqlfailover': (),
    'mysqlfrm': (),
    'mysqlgrants': (),
    'mysqlindexcheck': (),
    'mysqlmetagrep': (),
    'mysqlprocgrep': (),
    'mysqlreplicate': (),
    'mysqlrpladmin': (),
    'mysqlrplcheck': (),
    'mysqlrplms': (),
    'mysqlrplshow': (),
    'mysqlrplsync': (),
    'mysqlserverclone': (),
    'mysqlserverinfo': (),
    'mysqlslavetrx': (),
    'mysqluc': (),
    'mysqluserclone': (),
}
