if __name__ == '__main__':
    import sys
    import os.path
    here = os.path.dirname(os.path.abspath(__file__))
    rootpath = os.path.split(here)[0]
    sys.path[0:0] = [rootpath]

import unittest
import re
import copy

import tests.common       # Have to be before import of mysql.command

import mysql.command

_server = [dict(user="mats", host="localhost"),
           dict(user="chuck", host="remotehost")]

_resultset = [
    [(12, "mats", "localhost", "test", "Query", 0, None,
      "call malicious()"),
     (13, "mats", "localhost", "mysql", "Query", 100, None,
      "show full processlist")],
    [(2, "chuck", "localhost", "test", "Query", 100, None,
      "GRANT SUPERPOWER ON *.* TO chuck@localhost"),
     (3, "mats", "localhost", "mysql", "Query", 0, None,
      "REVOKE LICENSE ON *.* TO chuck@localhost")],
]


class Collector(object):
    def __init__(self):
        self.rows = []

    def __call__(self, conn, rows):
        self.rows.extend(rows)

    def reset(self):
        self.rows = []

class TestCommands(unittest.TestCase):
    """Test case to test commands"""

    def setUp(self):
        "Set up the test case with some mock database values"
        from tests.MySQLdb import create_connection, add_command_result
        self.__connection = [
            create_connection(user="mats", host="localhost"),
            create_connection(user="chuck", host="remotehost")
        ]

        for i in range(0, len(_resultset)):
            add_command_result(self.__connection[i],
                               "show full processlist",
                               _resultset[i])

    def tearDown(self):
        "Remove all connections from the mock database"
        for connection in self.__connection:
            tests.MySQLdb.remove_connection(connection)
        self.__connection = None

    def _checkHelper(self, options, resultset, func):
        """
        Helper function to check that the options and the function
        does the same job
        """
        cmd = mysql.command.ProcessListProcessor(options)
        collector = Collector()
        saved_print = mysql.command._action_map[mysql.command.PRINT_PROCESS]
        mysql.command._action_map[mysql.command.PRINT_PROCESS] = collector
        collector.reset()
        cmd.execute([])
        self.assertEqual(collector.rows, filter(func, resultset))
        mysql.command._action_map[mysql.command.PRINT_PROCESS] = saved_print

    def testNormalCall(self):
        for i in range(0, len(_server)):
            opts = dict()
            opts.update(_server[i])
            self._checkHelper(tests.common.Options(**opts), _resultset[i],
                              lambda row: True)

    def testUserMatch(self):
        for i in range(0, len(_server)):
            opts = dict(match_user="mats")
            opts.update(_server[i])
            self._checkHelper(tests.common.Options(**opts), _resultset[i], 
                              lambda row: row[1] == "mats")

    def testMatchHost(self):
        for i in range(0, len(_server)):
            opts = dict(match_host="localhost")
            opts.update(_server[i])
            self._checkHelper(tests.common.Options(**opts), _resultset[i],
                              lambda row: row[2] == "localhost")

    def testMatchTime(self):
        for i in range(0, len(_server)):
            opts = dict(match_time="+50")
            opts.update(_server[i])
            self._checkHelper(tests.common.Options(**opts), _resultset[i],
                              lambda row: row[5] >= 50)
        for i in range(0, len(_server)):
            opts = dict(match_time="-50")
            opts.update(_server[i])
            self._checkHelper(tests.common.Options(**opts), _resultset[i],
                              lambda row: row[5] <= 50)
 
    def testMatchInfo(self):
        for i in range(0, len(_server)):
            opts = dict(match_info="GRANT|REVOKE")
            opts.update(_server[i])
            self._checkHelper(tests.common.Options(**opts), _resultset[i],
                          lambda row: re.match("GRANT|REVOKE", row[7]))

def suite():
    return unittest.makeSuite(TestCommands, 'test')

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
