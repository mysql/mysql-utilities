# Major, Minor, Patch, Status
VERSION = (1, 0, 3, 'rc1')
VERSION_STRING = "%s.%s.%s" % VERSION[0:3]
RELEASE_STRING = "%s.%s.%s%s" % VERSION
COPYRIGHT = "2010, Oracle and/or its affiliates. All rights reserved."
COPYRIGHT_FULL = "Copyright (c) " + COPYRIGHT + """
This program is free software; see the source for copying
conditions. There is NO warranty; not even for MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE, to the extent permitted by law."""
VERSION_FRM = ("MySQL Utilities {program} version " + RELEASE_STRING
               + "\n" + COPYRIGHT_FULL)
