"""
Common unit test utilities.

This module also installs the Mock MySQLdb when being imported, so it
has to be imported before the test subject in the test.
"""

import tests.MySQLdb
if __name__ == '__main__':
    sys.modules['MySQLdb'] = tests.MySQLdb

class Options:
    "Fake options class to pass options"
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getattr__(self, name):
        return None
