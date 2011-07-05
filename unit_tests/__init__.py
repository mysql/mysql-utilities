import unittest

import test_options

def test_all():
    suite = unittest.TestSuite()
    suite.addTest(test_options.test_suite())
    return suite

