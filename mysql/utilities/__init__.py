# Major, Minor, Patch, Status
VERSION = (1, 3, 1, 'a', 0)
WORKBENCH_VERSION = (5, 2, 47)

VERSION_STRING = "%s.%s.%s" % VERSION[0:3]
RELEASE_STRING = (
    VERSION_STRING +
    " (part of MySQL Workbench Distribution %s.%s.%s)" % WORKBENCH_VERSION)

COPYRIGHT = "2010, 2013 Oracle and/or its affiliates. All rights reserved."
COPYRIGHT_FULL = "Copyright (c) " + COPYRIGHT + """
This is a release of dual licensed MySQL Utilities. For the avoidance of
doubt, this particular copy of the software is released
under the version 2 of the GNU General Public License.
MySQL Utilities is brought to you by Oracle.
"""
VERSION_FRM = ("MySQL Utilities {program} version " + RELEASE_STRING
               + "\n" + COPYRIGHT_FULL)
PYTHON_MIN_VERSION = (2, 6, 0)
PYTHON_MAX_VERSION = (3, 0, 0)

# This list has to be updated whenever a utility is added
AVAILABLE_UTILITIES = (
    'mysqlauditadmin',
    'mysqlauditgrep',
    'mysqldbcompare',
    'mysqldbcopy',
    'mysqldbexport',
    'mysqldbimport',
    'mysqldiff',
    'mysqldiskusage',
    'mysqlfailover',
    'mysqlfrm',
    'mysqlindexcheck',
    'mysqlmetagrep',
    'mysqlprocgrep',
    'mysqlreplicate',
    'mysqlrpladmin',
    'mysqlrplcheck',
    'mysqlrplshow',
    'mysqlserverclone',
    'mysqlserverinfo',
    'mysqluc',
    'mysqluserclone',
    )
