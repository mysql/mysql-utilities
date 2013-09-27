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
import glob
import os.path
import sys
import unittest
import optparse

if __name__ == '__main__':
    parser = optparse.OptionParser()
    (options, args) = parser.parse_args()
    suite = unittest.TestSuite()

    if args:
        test_files = []
        for arg in args:
            file_name = arg if arg.endswith('.py') else '{0}*.py'.format(arg)
            test_files.extend(glob.glob(os.path.join('unit_tests', file_name)))
    else:
        test_files = glob.glob('unit_tests/test*.py')

    for fname in test_files:
        (base, ext) = os.path.splitext(fname)
        name = '.'.join(base.split(os.sep))
        suite.addTest(unittest.defaultTestLoader.loadTestsFromName(name))

    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)             # Results are printed above
