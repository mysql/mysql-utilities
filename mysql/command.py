#!/usr/bin/python

import MySQLdb
import re

_factor = { "s": 1, "m": 60, "h": 3600, "d": 24*3600, "w": 7*24*3600 }
_row_format = "%4s %-10s %-10s %-10s %-6s %8s %-10s %s"

def _print_processes(conn, rows):
    print _row_format % ('ID', 'USER', 'HOST', 'DB','COMMAND','TIME','STATE','INFO')
    for row in rows:
        print _row_format % row

def _kill_queries(conn, rows):
    cursor = conn.cursor()
    for row in rows:
        cursor.execute("KILL QUERY %s", row[0])

def _kill_connections(conn, rows):
    cursor = conn.cursor()
    for row in rows:
        cursor.execute("KILL CONNECTION %s", row[0])

# Some handy constants
KILL_QUERY, KILL_CONNECTION, PRINT_PROCESS = range(3)

_action_map = [
    _kill_queries,              # KILL_QUERY
    _kill_connections,          # KILL_CONNECTION
    _print_processes,           # PRINT_PROCESS
]

class ProcessListProcessor(object):
    "Class for searching the PROCESSLIST table on a MySQL server. "

    def __string_matcher(self, opt, pos):
        """
        Add a string matcher for an option at a given position in the
        match list
        """
        if opt:
            mobj = re.compile(opt, re.IGNORECASE)
            self.__matches[pos] = lambda string: mobj.match(string)

    def __period_matcher(self, opt, pos):
        """
        Create a matcher for a period and add that to the given
        positon in the match list.

        The function accept periods of the form ``[+-]?<digits>[smhdw]``
        """
        if opt:
            mobj = re.match("([+-]?)(\d+)([smhdw]?)", opt)
            if mobj:
                sign, sec, per = mobj.groups()
                if per in _factor:
                    sec *= _factor[per]
                if sign == "+":
                    def match_func(val):
                        return int(val) >= int(sec)
                elif sign == "-":
                    def match_func(val):
                        return int(val) <= int(sec)
                else:           # !!! We need to think closer about this
                    def match_func(val):
                        return int(val) == int(sec)
                self.__matches[pos] = match_func

    def __init__(self, options):
        # PROCESSLIST files are: Id, User, Host, Db, Command, Time, State, Info
        self.__matches = 8 * [lambda x: True]
        self.__string_matcher(options.match_user, 1)
        self.__string_matcher(options.match_host, 2)
        self.__string_matcher(options.match_db,   3)
        self.__string_matcher(options.match_command, 4)
        self.__period_matcher(options.match_time, 5)
        self.__string_matcher(options.match_state, 6)
        self.__string_matcher(options.match_info, 7)

        self.__port = 3306
        self.__password = ""
        self.__socket = options.socket
        self.__user = options.user

        if options.port:
            self.__port = options.port
        if options.password:
            self.__password = options.password
        if options.host:
            self.__host = options.host

        # If there were no action option supplied, we print all
        # matching processes
        if options.action_list:
            self.__action_list = options.action_list
        else:
            self.__action_list = [PRINT_PROCESS]

    def __match_row(self, row):
        """Process a single row and see if it matches the stored patterns."""
        if not row:
            return False
        return True

    def __ask_one_server(self, conn):
        """Execute ``SHOW FULL PROCESSLIST`` on a server and return
        the rows that matched"""
        result = []
        cur = conn.cursor()
        cur.execute("SHOW FULL PROCESSLIST")
        for row in cur:
            for match, column in zip(self.__matches, row):
                # Here we should use MySQLdb.conversion instead of
                # converting (back) to a string
                if not match(str(column)):
                    break
            else:
                result.append(row)  # All matched
        return result
        
    def execute(self, args):
        if self.__socket:
            conn = MySQLdb.connect(unix_socket=self.__socket,
                                   user=self.__user, passwd=self.__password)
        else:
            conn = MySQLdb.connect(host=self.__host, port=self.__port,
                                   user=self.__user, passwd=self.__password)
            
        rows = self.__ask_one_server(conn)
        for action in self.__action_list:
            _action_map[action](conn, rows)
