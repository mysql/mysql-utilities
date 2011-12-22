#!/usr/bin/env python
#
# Copyright (c) 2011, Oracle and/or its affiliates. All rights reserved.
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
This files contains unit tests for the MySQL General and Slow Query Log
parsers.
"""

import sys
import os.path
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOTPATH = os.path.split(_HERE)[0]
sys.path.append(_ROOTPATH)

import tempfile
import inspect
import datetime
import decimal
import itertools
import unittest

from mysql.utilities.exception import (
    LogParserError,
    )

from mysql.utilities.parser import *

LOG_HEADERS = [
    ('/usr/sbin/mysqld, Version: 5.1.54-1ubuntu4-log'
        ' ((Ubuntu)). started with:',
     'Tcp port: 3309  Unix socket: /var/run/mysqld/mysqld3.sock',
     'Time                 Id Command    Argument',),
    ('/usr/local/mysql/bin/mysqld, Version: 5.5.17-log'
        ' (Source Distribution). started with:',
     'Tcp port: 3306  Unix socket: /tmp/mysql.sock',
     'Time                 Id Command    Argument',),
     ('/usr/local/mysql/bin/mysqld, Version: 5.5.17'
         ' (Source Distribution). started with:',
      'Tcp port: 3306  Unix socket: /tmp/mysql.sock',
      'Time                 Id Command    Argument',),
]
LOG_HEADERS_EXP = [
    {'_version': (5,1,54,"1ubuntu4-log"),
     '_program': '/usr/sbin/mysqld',
     '_port': 3309,
     '_socket': '/var/run/mysqld/mysqld3.sock',
     '_start_datetime': None,
     '_last_seen_datetime': None,},
    {'_version': (5,5,17,"log"),
     '_program': '/usr/local/mysql/bin/mysqld',
     '_port': 3306,
     '_socket': '/tmp/mysql.sock',
     '_start_datetime': None,
     '_last_seen_datetime': None,},
    {'_version': (5,5,17,None),
     '_program': '/usr/local/mysql/bin/mysqld',
     '_port': 3306,
     '_socket': '/tmp/mysql.sock',
     '_start_datetime': None,
     '_last_seen_datetime': None,},
]

GENERAL_LOG_ENTRIES = {
    'Connect': (
        "111102  9:48:46\t    3 Connect\troot@localhost on",
        "111102 16:48:46\t    4 Connect\troot@localhost on mysql",
        "\t\t    5 Connect\troot@localhost on mysql",
        ),
    'Query': (
        "111102 12:49:02\t    3 Query\tinsert into t1 values (3),(4)",
        "\t\t    3 Query\tinsert into t1 values (5),(6)",
        "111102 14:49:02\t    4 Query\tinsert into t1\nvalues (7),(8)",
        ),
    'Init DB': (
        "111102 12:49:02\t    3 Init DB\ttest",
        "\t\t    3 Init DB\ttest",
        "\t\t    4 Init DB\ttest",
        ),
    'Quit': (
        "111102 12:49:04\t    3 Quit\t",
        "\t\t    3 Quit\t",
        "\t\t    4 Quit\t",
        ),
    'Prepare': (
        "111206 18:12:23\t    35 Query\tPREPARE stmt1 FROM 'SELECT * FROM t1",
        "WHERE id = ?'",
        "\t\t    35 Prepare\tSELECT * FROM t1",
        "WHERE id = ?",
        ),
}

GENERAL_LOG_ENTRIES_EXP = {
    'Connect': (
        {'database': None,
         'argument': 'root@localhost on',
         'session_id': 3,
         'datetime': datetime.datetime(2011, 11, 2, 9, 48, 46),
         'host': 'localhost',
         'command': 'Connect',
         'user': 'root'},
        {'database': 'mysql',
         'argument': 'root@localhost on mysql',
         'session_id': 4, 
         'datetime': datetime.datetime(2011, 11, 2, 16, 48, 46),
         'host': 'localhost',
         'command': 'Connect',
         'user': 'root'},
        {'database': 'mysql',
         'argument': 'root@localhost on mysql',
         'session_id': 5,
         'datetime': None,
         'host': 'localhost',
         'command': 'Connect',
         'user': 'root'},
        ),
    'Query': (
        {'database': None,
         'argument': 'insert into t1 values (3),(4)',
         'session_id': 3,
         'datetime': datetime.datetime(2011, 11, 2, 12, 49, 2),
         'host': None,
         'command': 'Query',
         'user': None},
        {'host': None,
         'command': 'Query',
         'user': None,
         'database': None,
         'argument': 'insert into t1 values (5),(6)',
         'session_id': 3,
         'datetime': datetime.datetime(2011, 11, 2, 12, 49, 2)},
        {'host': None,
         'command': 'Query',
         'user': None,
         'database': None,
         'argument': 'insert into t1\nvalues (7),(8)',
         'session_id': 4,
         'datetime': datetime.datetime(2011, 11, 2, 14, 49, 2)},
    ),
    'Init DB': (
        {'host': None,
         'command': 'Init DB',
         'user': None,
         'database': 'test',
         'argument': 'test',
         'session_id': 3,
         'datetime': datetime.datetime(2011, 11, 2, 12, 49, 2)},
        {'host': None,
         'command': 'Init DB',
         'user': None,
         'database': 'test',
         'argument': 'test',
         'session_id': 3,
         'datetime': datetime.datetime(2011, 11, 2, 12, 49, 2)},
        {'host': None,
         'command': 'Init DB',
         'user': None,
         'database': 'test',
         'argument': 'test',
         'session_id': 4,
         'datetime': None},
    ),
    'Quit': (
        {'host': None,
         'command': 'Quit',
         'user': None,
         'database': None,
         'argument': None,
         'session_id': 3,
         'datetime': datetime.datetime(2011, 11, 2, 12, 49, 4)},
        {'host': None,
         'command': 'Quit',
         'user': None,
         'database': None,
         'argument': None,
         'session_id': 3,
         'datetime': None},
        {'host': None,
         'command': 'Quit',
         'user': None,
         'database': None,
         'argument': None,
         'session_id': 4,
         'datetime': None},
    ),
    'Prepare': (
        {'host': None,
         'command': 'Query',
         'user': None,
         'database': None,
         'argument': "PREPARE stmt1 FROM 'SELECT * FROM t1\nWHERE id = ?'",
         'session_id': 35,
         'datetime': datetime.datetime(2011, 12, 6, 18, 12, 23)},
        {'host': None,
         'command': 'Prepare',
         'user': None,
         'database': None,
         'argument': 'SELECT * FROM t1\nWHERE id = ?',
         'session_id': 35,
         'datetime': datetime.datetime(2011, 12, 6, 18, 12, 23)},
    ),
}

SLOW_LOG_ENTRIES = [
    ('# Time: 111102 12:48:46',
     '# User@Host: root[root] @ localhost []',
     '# Query_time: 0.000333  Lock_time: 0.000000'
        ' Rows_sent: 1  Rows_examined: 0',
     'SET timestamp=1320234526;',
     'select @@version_comment limit 1;'),
    ('# Time: 111125 11:56:45',
     '# User@Host: root[root] @ localhost []',
     '# Query_time: 12.000333  Lock_time: 34.000000'
        ' Rows_sent: 44345  Rows_examined: 3123423',
     'SET timestamp=1322218605;',
     'select c1',
     'from t1',
     'where c1 like "%a%";'),
    ('# User@Host: root[root] @ localhost []',
     '# Query_time: 2.000333  Lock_time: 2.000000'
        ' Rows_sent: 44342  Rows_examined: 3123428',
     'SET timestamp=1322218605;',
     'select c1',
     'from t1',
     'where c1 like "%a%";'),
]
SLOW_LOG_ENTRIES_EXP = [
    {'query_time': decimal.Decimal('0.000333'),
      'rows_examined': 0,
      'rows_sent': 1,
      'database': None,
      'lock_time': decimal.Decimal('0.000000'),
      'datetime': datetime.datetime.fromtimestamp(1320234526),
      'host': 'localhost',
      'user': 'root',
      'query': 'SET timestamp=1320234526;\nselect @@version_comment limit 1;'},
    {'query_time': decimal.Decimal('12.000333'),
     'rows_examined': 3123423, 
      'rows_sent': 44345,
      'database': None,
      'lock_time': decimal.Decimal('34.000000'),
      'datetime': datetime.datetime.fromtimestamp(1322218605),
      'host': 'localhost',
      'user': 'root',
      'query': ('SET timestamp=1322218605;\n'
                'select c1\nfrom t1\nwhere c1 like "%a%";')},
    {'query_time': decimal.Decimal('2.000333'),
     'rows_examined': 3123428, 
      'rows_sent': 44342,
      'database': None,
      'lock_time': decimal.Decimal('2.000000'),
      'datetime': datetime.datetime.fromtimestamp(1322218605),
      'host': 'localhost',
      'user': 'root',
      'query': ('SET timestamp=1322218605;\n'
                'select c1\nfrom t1\nwhere c1 like "%a%";')},
]

class BaseParserTestCase(unittest.TestCase):
    """Base class for all unittests testing parsers
    """
    def checkArguments(self, function, supported_arguments):
        argspec = inspect.getargspec(function)
        function_arguments = dict(zip(argspec[0][1:],argspec[3]))
        for argument, default in function_arguments.items():
            try:
                self.assertEqual(supported_arguments[argument],
                    default, msg ="Argument '%s' has wrong default" % argument)
            except KeyError:
                self.fail("Found unsupported or new argument '%s'" % argument)
        for argument, default in supported_arguments.items():
            if not function_arguments.has_key(argument):
                self.fail("Supported argument '%s' fails" % argument)
    
    def _fakelog_writelines(self, lines, empty=True, rewind=True):
        """Helper function writing to file object self.fakelog

        The attribute fakelog should be a temporary file. If it is available,
        this function will write all items in the lines-list to the file.
        When empty is true (default), the file will be truncated.

        After writing, the current possition will be rest to the first byte
        unless rewind is set to False.
        """
        try:
            if empty is True:
                self.fakelog.seek(0)
                self.fakelog.truncate()
            self.fakelog.write('\n'.join(lines)+'\n')
            if rewind is True:
                self.fakelog.seek(0)
        except AttributeError:
            pass
    
    def check_attributes(self, obj, expected):
        if isinstance(obj, dict):
            objdict = obj
        else:
            objdict = obj.__dict__
        for key,value in expected.items():
            self.assertTrue(key in objdict,
                msg="No attribute '%s' for instance of class %s" % (
                    key,obj.__class__.__name__))
            self.assertEqual(value, objdict[key])

class TestLogParserBase(BaseParserTestCase):
    """Test LogParserBase-class
    """
    def setUp(self):
        self.fakelog = tempfile.SpooledTemporaryFile(max_size=3*1024)
        self.log = LogParserBase(stream=self.fakelog)
    
    def tearDown(self):
        try:
            self.fakelog.close()
        except:
            pass # Does not matter if self.fakelog can't be closed
    
    def test_init(self):
        """Initialzing LogParserBase instance"""
        self.assertRaises(TypeError,LogParserBase)

        exp = {
            '_stream': self.fakelog,
            '_version': None,
            '_program': None,
            '_port': None,
            '_socket': None,
            '_start_datetime': None,
            '_last_seen_datetime': None,
        }
        self.check_attributes(self.log,exp)
        
        # Check logs not starting with headers
        self._fakelog_writelines(GENERAL_LOG_ENTRIES['Connect'])
        self.log = LogParserBase(self.fakelog)
        self.check_attributes(self.log,exp)
        self.assertEqual(GENERAL_LOG_ENTRIES['Connect'][0],
                         self.log._get_next_line())

        self._fakelog_writelines(LOG_HEADERS[0], empty=True)
        exp = {
            '_stream': self.fakelog,
            '_version': (5,1,54,"1ubuntu4-log"),
            '_program': '/usr/sbin/mysqld',
            '_port': 3309,
            '_socket': '/var/run/mysqld/mysqld3.sock',
            '_start_datetime': None,
            '_last_seen_datetime': None,
        }
        self.log = LogParserBase(self.fakelog)
        self.check_attributes(self.log,exp)

    def test_get_next_line(self):
        """Get the next line from the log file"""
        data = (
            '# Line 1',
            '# Line 2',
            )
        self._fakelog_writelines(data, empty=True)
        self.assertEqual(data[0],self.log._get_next_line())
        self.assertEqual(data[1],self.log._get_next_line())

        # Go to the end of the stream
        self.log._stream.seek(0, os.SEEK_END)
        self.assertEqual(None,self.log._get_next_line())

    def test_parse_header(self):
        """Parse the header of a MySQL log file"""
        # Tested with test___init__
        self.assertRaises(LogParserError,self.log._parse_header,"Ham Spam")
        self.assertEqual(None,self.log._parse_header(None))
    
    def test_version(self):
        """Get the version of the MySQL server"""
        exp = (5,5,17,'log')
        self.log._version = exp
        self.assertEqual(exp,self.log.version)
    
    def test_program(self):
        """Get the full path of the MySQL server executable"""
        exp = '/usr/sbin/mysqld'
        self.log._program = exp
        self.assertEqual(exp,self.log.program)

    def test_port(self):
        """Get the TCP/IP port of the MySQL server"""
        exp = 3309
        self.log._port = exp
        self.assertEqual(exp,self.log.port)
    
    def test_socket(self):
        """Get the Unix socket of the MySQL server"""
        exp = '/tmp/mysql.sock'
        self.log._socket = exp
        self.assertEqual(exp,self.log.socket)

    def test_start_datetime(self):
        """Get the timestamp of the first read log entry"""
        exp = datetime.datetime(2011,11,2,12,48,46)
        self.log._start_datetime = exp
        self.assertEqual(exp,self.log.start_datetime)

    def test_last_seen_datetime(self):
        """Get the timestamp of the last read log entry"""
        exp = datetime.datetime(2011,11,2,12,48,46)
        self.log._last_seen_datetime = exp
        self.assertEqual(exp,self.log.last_seen_datetime)
    
    def test_str(self):
        """String representation of LogParserBase"""
        version = (5,5,17,'-log')
        self.log._version = version
        exp = "<LogParserBase, MySQL v5.5.17-log>"
        self.assertEqual(exp,str(self.log))
        
        version = (5,5,17,None)
        self.log._version = version
        exp = "<LogParserBase, MySQL v5.5.17>"
        self.assertEqual(exp,str(self.log))
        

class TestGeneralQueryLog(BaseParserTestCase):
    def setUp(self):
        self.fakelog = tempfile.SpooledTemporaryFile(max_size=3*1024)
        self.log = GeneralQueryLog(stream=self.fakelog)
    
    def tearDown(self):
        try:
            self.fakelog.close()
        except:
            pass
    
    def test_init(self):
        """Initialzing GeneralQueryLog instance (empty log)"""
        self.assertRaises(TypeError,GeneralQueryLog)

        exp = {
            '_version': None,
            '_program': None,
            '_port': None,
            '_socket': None,
            '_start_datetime': None,
            '_last_seen_datetime': None,
            '_sessions': {},
            '_cached_logentry': None,
        }
        self.check_attributes(self.log,exp)

        self._fakelog_writelines(LOG_HEADERS[0], empty=True)
        exp = {
            '_stream': self.fakelog,
            '_version': (5,1,54,"1ubuntu4-log"),
            '_program': '/usr/sbin/mysqld',
            '_port': 3309,
            '_socket': '/var/run/mysqld/mysqld3.sock',
            '_start_datetime': None,
            '_last_seen_datetime': None,
        }
        self.log = GeneralQueryLog(self.fakelog)
        self.check_attributes(self.log,exp)
    
    def test__new_session(self):
        """Add a new session"""
        session_id = 1
        exp = dict(database=None,
                   user=None,
                   host=None,
                   time_last_action=None,
                   to_delete=False)
        self.log._new_session(session_id)
        self.assertEqual(exp,self.log._sessions[session_id])
    
    def test_parse_command(self):
        """Parse a line from General Query Log having a command"""
        self.assertEqual(None,self.log._parse_command(None,None))

    def test_handle_connect(self):
        """Parse General Query Log Connect entries: Connect-Command"""
        lines = []
        for line in GENERAL_LOG_ENTRIES['Connect']:
            lines += line.splitlines()
        self._fakelog_writelines(lines)

        i = 0
        logentry = self.fakelog. readline().strip()
        while logentry:
            exp = GENERAL_LOG_ENTRIES_EXP['Connect'][i]
            entry = GeneralQueryLogEntry()
            self.log._parse_command(logentry,entry)
            self.assertEqual(exp,dict(entry))
            result = self.log._sessions[entry['session_id']]['database']
            if entry['argument'].endswith('on'):
                self.assertEqual(None,result)
            else:
                self.assertEqual(entry['argument'].split(' ')[2],result)
            if self.log._cached_logentry is not None:
                logentry = self.log._cached_logentry
            else:
                logentry = self.fakelog. readline().strip()
            i += 1
    
    def _check_simple_commands(self, command):
        lines = []
        for line in GENERAL_LOG_ENTRIES[command]:
            lines += line.splitlines()
        self._fakelog_writelines(lines)

        i = 0
        logentry = self.fakelog.readline().strip()
        while logentry:
            exp = GENERAL_LOG_ENTRIES_EXP[command][i]
            entry = GeneralQueryLogEntry()
            self.log._parse_command(logentry,entry)
            self.assertEqual(exp,dict(entry))
            if self.log._cached_logentry is not None:
                logentry = self.log._cached_logentry
            else:
                logentry = self.fakelog.readline().strip()
            i += 1
    
    def test_handle_multi_line(self):
        """Parse General Query Log entries spanning multiple lines"""
        self._check_simple_commands("Query")
        self._check_simple_commands("Prepare")

    def test_handle_init_db(self):
        """Parse General Query Log Query entries: Init DB-command"""
        self._check_simple_commands("Init DB")
    
    def test_handle_quit(self):
        """Parse General Query Log Query entries: Quit-command"""
        self._check_simple_commands("Quit")

    def test_parse_entry(self):
        """"Parse a General Query Log entry"""
        self.assertEqual(None,self.log._parse_entry())

        # Parsing headers while getting entries
        self.log = GeneralQueryLog(stream=self.fakelog)
        for i,data in enumerate(LOG_HEADERS):
            self._fakelog_writelines(data, empty=True)
            self.log._parse_entry()
            self.check_attributes(self.log,LOG_HEADERS_EXP[i])

    def test_iter(self):
        """Iterate through the log, reading entries (iter()-method)"""
        try:
            iter(self.log)
        except TypeError:
            self.fail("GeneralQueryLog is not iterable")
        
        self._fakelog_writelines(GENERAL_LOG_ENTRIES['Query'],
                                 empty=True,rewind=True)

        log_iterator = self.log.__iter__()
        for i,exp in enumerate(GENERAL_LOG_ENTRIES_EXP['Query']):
            entry = log_iterator.next()
            self.assertTrue(isinstance(entry, GeneralQueryLogEntry))
            self.assertEqual(exp,entry,msg="Failed parsing entry #%d" % i)

    def test_next(self):
        """Iterate through the log, reading entries (.next()-method)"""
        self.assertRaises(StopIteration,self.log.next)

        data = GENERAL_LOG_ENTRIES['Query'][0]
        exp = GENERAL_LOG_ENTRIES_EXP['Query'][0]
        self._fakelog_writelines([data],empty=True,rewind=True)
        self.assertEqual(exp,self.log.next())
        self.assertRaises(StopIteration,self.log.next)

class TestSlowQueryLog(BaseParserTestCase):
    """Test SlowQueryLog class"""

    def setUp(self):
        self.fakelog = tempfile.SpooledTemporaryFile(max_size=3*1024)
        self.log = SlowQueryLog(stream=self.fakelog)
    
    def tearDown(self):
        try:
            self.fakelog.close()
        except:
            pass

    def test_init(self):
        """Initialzing SlowQueryLog instance (empty log)"""
        exp = {
            '_stream': self.fakelog,
            '_version': None,
            '_program': None,
            '_port': None,
            '_socket': None,
            '_start_datetime': None,
            '_last_seen_datetime': None,
            '_cached_line': None,
            '_current_database': None,
        }
        self.check_attributes(self.log,exp)

        self._fakelog_writelines(LOG_HEADERS[0], empty=True)
        exp = {
            '_stream': self.fakelog,
            '_version': (5,1,54,"1ubuntu4-log"),
            '_program': '/usr/sbin/mysqld',
            '_port': 3309,
            '_socket': '/var/run/mysqld/mysqld3.sock',
            '_start_datetime': None,
            '_last_seen_datetime': None,
        }
        self.log = SlowQueryLog(self.fakelog)
        self.check_attributes(self.log,exp)

    def test_parse_line(self):
        """Parse a log line using regular expression Match-object"""
        regex = re.compile("(\d{1}) (\d{2}) (\d{3}) (\w{3})")
        line = "1 12 123 ham"
        exp = ('1','12','123','ham')
        self.assertEqual(exp,self.log._parse_line(regex, line))

        line = "spam"
        self.assertRaises(LogParserError, self.log._parse_line, regex, line)
    
    def test_parse_connection_info(self):
        """Get connection info from a slow query log entry"""
        tests = [
            ('# User@Host: root[root] @ localhost []',
             dict(user='root',host='localhost')),
            ('# User@Host: root[root] @ localhost [127.0.0.1]',
             dict(user='root',host='localhost')),
            ('# User@Host: root[root] @ [127.0.0.1]',
             dict(user='root',host='127.0.0.1')),
            ('# User@Host: [ham] @ localhost []',
             dict(user='ham',host='localhost')),
            ('# User@Host: [ham] @ [127.0.0.1]',
             dict(user='ham',host='127.0.0.1')),
        ]
        for data,exp in tests:
            result = dict()
            try:
                self.log._parse_connection_info(data,result)
            except LogParserError:
                self.fail("Failed parsing (correct) line: '%s'" % data)
            self.assertEqual(exp,result)

        self.assertRaises(LogParserError,self.log._parse_connection_info,
            'ham spam ham spam',dict())
    
    def test_parse_timestamp(self):
        """Get the timestamp of the slow query log entry"""
        tests = [
            ('# Time: 111102 12:48:46',
             dict(datetime=datetime.datetime(2011,11,2,12,48,46))),
            ('# Time: 111102   9:48:46',
             dict(datetime=datetime.datetime(2011,11,2,9,48,46))),
        ]
        for data,exp in tests:
            result = dict()
            try:
                self.log._parse_timestamp(data,result)
            except LogParserError:
                self.fail("Failed parsing (correct) line: '%s'" % data)
            self.assertEqual(exp,result)

        self.assertRaises(LogParserError,self.log._parse_timestamp,
            'ham spam ham spam',dict())
    
    def test_parse_statistics(self):
        """Get statistics of the slow query log entry"""
        tests = [
            ('# Query_time: 0.000333  Lock_time: 0.000000'\
             ' Rows_sent: 1  Rows_examined: 0',
                dict(query_time=decimal.Decimal('0.000333'),
                     lock_time=decimal.Decimal('0.000000'),
                     rows_examined=0,rows_sent=1)),
            ('# Query_time: 123.000333  Lock_time: 323.000001'\
             ' Rows_sent: 12  Rows_examined: 34',
                dict(query_time=decimal.Decimal('123.000333'),
                     lock_time=decimal.Decimal('323.000001'),
                     rows_examined=34,rows_sent=12)),
        ]
        for data,exp in tests:
            result = dict()
            try:
                self.log._parse_statistics(data,result)
            except LogParserError:
                self.fail("Failed parsing (correct) line: '%s'" % data)
            self.assertEqual(exp,result)
        
        self.assertRaises(LogParserError,self.log._parse_statistics,
            'ham spam ham spam',dict())
    
    def test_parse_query(self):
        """Get the queries of a slow query log entry"""
        tests = [
            # First entry should have no 'use'-statement
            (   ('SET timestamp=1320234526;',
                 'select @@version_comment limit 1;'),
                dict(database=None,
                     datetime=datetime.datetime.fromtimestamp(1320234526),
                     query='SET timestamp=1320234526;\n'\
                        'select @@version_comment limit 1;')),
            
            (   ('SET timestamp=1320234526;',
                 'select c1',
                 'from t1',
                 'where c1 like "%a%";'),
                dict(database=None,
                     datetime=datetime.datetime.fromtimestamp(1320234526),
                     query='SET timestamp=1320234526;\n'\
                           'select c1\nfrom t1\nwhere c1 like "%a%";')),
            
            # Last entry should have 'use test'
            (   ('use test',
                 'SET timestamp=1320234526;',
                 'select @@version_comment limit 1;'),
                dict(database='test',
                     datetime=datetime.datetime.fromtimestamp(1320234526),
                     query='use test\nSET timestamp=1320234526;\n'\
                           'select @@version_comment limit 1;')),
        ]

        for data,exp in tests:
            self._fakelog_writelines(data, empty=True)
            result = dict(database=None, query=None)
            try:
                self.log._parse_query(self.log._get_next_line(),result)
            except LogParserError:
                self.fail("Failed parsing (correct) line: '%s'" % data)
            self.assertEqual(exp,result)
        
        # Database should be same as last item in the tests-list
        self._fakelog_writelines(tests[0][0], empty=True)
        result = dict(database=None, query=None)
        exp = dict(database='test',
                   datetime=datetime.datetime.fromtimestamp(1320234526),
                   query='SET timestamp=1320234526;\n'\
                         'select @@version_comment limit 1;')
        try:
            self.log._parse_query(self.log._get_next_line(),result)
        except LogParserError:
            self.fail("Failed parsing (correct) line: '%s'" % data)
        self.assertEqual(exp,result)
    
    def test_parse_entry(self):
        """Parse a Slow Query Log entry"""
        self.assertEqual(None,self.log._parse_entry())

        for i,data in enumerate(SLOW_LOG_ENTRIES):
            self._fakelog_writelines(data, empty=True)
            self.assertEqual(SLOW_LOG_ENTRIES_EXP[i],
                             self.log._parse_entry())
        
        # Parsing headers while getting entries
        self.log = SlowQueryLog(stream=self.fakelog)
        for i,data in enumerate(LOG_HEADERS):
            self._fakelog_writelines(data, empty=True)
            self.log._parse_entry()
            self.check_attributes(self.log,LOG_HEADERS_EXP[i])

    def test_iter(self):
        """Iterate through the log, reading entries (iter()-method)"""
        try:
            iter(self.log)
        except TypeError:
            self.fail("SlowQueryLog is not iterable")

        for i,data in enumerate(SLOW_LOG_ENTRIES):
            self._fakelog_writelines(data, empty=False,rewind=False)
        self.fakelog.seek(0)

        log_iterator = self.log.__iter__()
        for i,exp in enumerate(SLOW_LOG_ENTRIES_EXP):
            entry = log_iterator.next()
            self.assertTrue(isinstance(entry, SlowQueryLogEntry))
            self.assertEqual(exp,entry,msg="Failed parsing entry #%d" % i)
    
    def test_next(self):
        """Iterate through the log, reading entries (.next()-method)"""
        self.assertRaises(StopIteration,self.log.next)

        data = SLOW_LOG_ENTRIES[0]
        exp = SLOW_LOG_ENTRIES_EXP[0]
        self._fakelog_writelines(data,empty=True,rewind=True)
        self.assertEqual(exp,self.log.next())
        self.assertRaises(StopIteration,self.log.next)

class TestLogEntryBase(BaseParserTestCase):
    entry_init_attributes =  {
        'datetime': None,
        'database': None,
        'user': None,
        'host': None,
    }

    def setUp(self):
        self.entry = LogEntryBase()

    def test_init(self):
        """Initialize LogEntryBase"""
        self.check_attributes(self.entry,self.entry_init_attributes)

class TestGeneralQueryLogEntry(BaseParserTestCase):
    entry_init_attributes =  {
        'datetime': None,
        'database': None,
        'user': None,
        'host': None,
        'session_id': None,
        'command': None,
        'argument': None,
    }

    def setUp(self):
        self.entry = GeneralQueryLogEntry()

    def test_init(self):
        """Initialize LogEntryBase"""
        self.check_attributes(self.entry,self.entry_init_attributes)
    
    def test___str__(self):
        """String representation of LogParserBase"""
        exp = "<GeneralQueryLogEntry  [None] None: None>"
        self.assertEqual(exp,str(self.entry))

class TestSlowQueryLogEntry(BaseParserTestCase):
    entry_init_attributes =  {
        'datetime': None,
        'database': None,
        'query': None,
        'user': None,
        'host': None,
        'query_time': None,
        'lock_time': None,
        'rows_examined': None,
        'rows_sent': None,
    }

    def setUp(self):
        self.entry = SlowQueryLogEntry()

    def test_init(self):
        """Initialize LogEntryBase"""
        self.check_attributes(self.entry,self.entry_init_attributes)
    
    def test_str(self):
        """String representation of LogParserBase"""
        exp = "<SlowQueryLogEntry  [None@None] None/None/None/None>"
        self.assertEqual(exp,str(self.entry))

if __name__ == '__main__':
    unittest.main()
