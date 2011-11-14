import glob
import os.path
import sys
import unittest

if __name__ == '__main__':
    suite = unittest.TestSuite()
    for fname in glob.glob("unit_tests/test*.py"):
        base, ext = os.path.splitext(fname)
        name = '.'.join(base.split('/'))
        suite.addTest(unittest.defaultTestLoader.loadTestsFromName(name))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)             # Results are printed above

