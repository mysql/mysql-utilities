#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
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
This file contains methods to test mysqluc.
"""

import logging
import optparse
import os
import sys

from mysql.utilities import VERSION_FRM
from mysql.utilities.exception import UtilError

# Constants
NAME = "mysqlfakeutility"
DESCRIPTION = "mysqlfakeutility - a mysqlutility mock to test mysqluc"
USAGE = ("%prog --return-code=<return_code> "
         "--message-error=<path>")

# Setup the command parser
parser = optparse.OptionParser(
    version=VERSION_FRM.format(program=os.path.basename(sys.argv[0])),
    description=DESCRIPTION,
    usage=USAGE,
    add_help_option=False)
parser.add_option("--help", action="help")

# Setup utility-specific options:

# Connection information for the source server
parser.add_option("-e", "--return-code", action="store", dest="return_code",
                  type="int", default="0",
                  help="the code to return at the program end.")

# Data directory for new instance
parser.add_option("-m", "--message-error", action="store", 
                  dest="message_error", type="string",
                  default="an anomaly occurred\n", help="an error "
                  "message to show in stderr, if it's required")

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# Do the stuff
if opt.return_code:
    sys.stderr.write(opt.message_error)
    sys.stderr.flush()
    sys.exit(opt.return_code)

print("# ...done.")
sys.exit()
