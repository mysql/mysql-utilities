# Major, Minor, Patch, Status
VERSION = (0, 1, 0, 'alpha')
VERSION_STRING = "{0}.{1}.{2}".format(*VERSION[0:3])
RELEASE_STRING = "{0}.{1}.{2}-{3}".format(*VERSION)
COPYRIGHT = "2010, Oracle and/or its affiliates. All rights reserved."
COPYRIGHT_FULL = "Copyright (c) " + COPYRIGHT + """
This program is free software; see the source for copying
conditions. There is NO warranty; not even for MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE, to the extent permitted by law."""
VERSION_FRM = ("MySQL Utilities {program} version " + RELEASE_STRING
               + "\n" + COPYRIGHT_FULL)
