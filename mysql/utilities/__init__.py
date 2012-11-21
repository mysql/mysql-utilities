# Major, Minor, Patch, Status
VERSION = (1, 2, 0, "a", 1)
WORKBENCH_VERSION = (5, 2, 44)

VERSION_STRING = '.'.join(map(str, VERSION[0:3]))
if VERSION[3] and VERSION[4]:
    VERSION_STRING += VERSION[3] + str(VERSION[4])

RELEASE_STRING = "{0} - MySQL Workbench Distribution {1}".format(
	VERSION_STRING, '.'.join(map(str, WORKBENCH_VERSION))) 

COPYRIGHT = "2010, 2012 Oracle and/or its affiliates. All rights reserved."
COPYRIGHT_FULL = "Copyright (c) " + COPYRIGHT + """
This is a release of dual licensed MySQL Utilities. For the avoidance of
doubt, this particular copy of the software is released
under the version 2 of the GNU General Public License.
MySQL Utilities is brought to you by Oracle.
"""
VERSION_FRM = ("MySQL Utilities {program} version " + RELEASE_STRING
               + "\n" + COPYRIGHT_FULL)
