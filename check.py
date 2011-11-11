import glob
import os.path
import unittest

if __name__ == '__main__':
    suite = unittest.TestSuite()
    for fname in glob.glob("unit_tests/test*.py"):
        base, ext = os.path.splitext(fname)
        name = '.'.join(base.split('/'))
        suite.addTest(unittest.defaultTestLoader.loadTestsFromName(name))
    unittest.TextTestRunner().run(suite)
