#
# Copyright (c) 2011, 2013, Oracle and/or its affiliates. All rights reserved.
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
"""Module with parsers for General and Slow Query Log.
"""

import sys
import re
import decimal
import datetime

from mysql.utilities.exception import LogParserError

_DATE_PAT = r"\d{6}\s+\d{1,2}:\d{2}:\d{2}"

_HEADER_VERSION_CRE = re.compile(r"(.+), Version: (\d+)\.(\d+)\.(\d+)(?:-(\S+))?")
_HEADER_SERVER_CRE = re.compile(r"Tcp port:\s*(\d+)\s+Unix socket:\s+(.*)")

_SLOW_TIMESTAMP_CRE = re.compile(r"#\s+Time:\s+(" + _DATE_PAT + r")")
_SLOW_USERHOST_CRE = re.compile(r"#\s+User@Host:\s+"
                       r"(?:([\w\d]+))?\s*"
                       r"\[\s*([\w\d]+)\s*\]\s*"
                       r"@\s*"
                       r"([\w\d\.\-]*)\s*"
                       r"\[\s*([\d.]*)\s*\]")
_SLOW_STATS_CRE = re.compile(r"#\sQuery_time:\s(\d*\.\d{1,6})\s*"
            r"Lock_time:\s(\d*\.\d{1,6})\s*"
            r"Rows_sent:\s(\d*)\s*"
            r"Rows_examined:\s(\d*)")

_GENERAL_ENTRY_CRE = re.compile(
            r'(?:('+ _DATE_PAT +'))?\s*'
            r'(\d+)\s([\w ]+)\t*(?:(.+))?$')

class LogParserBase(object):
    """Base class for parsing MySQL log files
    
    LogParserBase should be inherited to create parsers for MySQL log files.
    This class has the following capabilities:

    - Take a stream and check whether it is a file type
    - Retrieve next line from stream
    - Parse header information from a log file (for General or Slow Query Log)
    - Implements the iterator protocol

    This class should not be used directly, but inhereted and extended to
    match the log file which needs to be parsed.
    """
    def __init__(self, stream):
        """Constructor

        stream[in]          A file type

        The stream argument must be a valid file type supporting for
        example the readline()-method. For example, the return of the buildin
        function open() can be used:
            LogParserBase(open("/path/to/mysql.log"))
        
        Raises LogParserError on errors.
        """
        self._stream = None
        self._version = None
        self._program = None
        self._port = None
        self._socket = None
        self._start_datetime = None
        self._last_seen_datetime = None

        # Check if we got a file type
        line = None
        try:
            self._stream = stream
            line = self._get_next_line()
        except AttributeError:
            raise LogParserError("Need a file type")
        
        # Not every log file starts with a header
        if line is not None and line.endswith('started with:'):
            self._parse_header(line)
        else:
            self._stream.seek(0)
    
    def _get_next_line(self):
        """Get next line from the log file

        This method reads the next line from the stream. Trailing
        newline (\n) and carraige return (\r) are removed.

        Returns next line as string or None
        """
        line = self._stream.readline()
        if not line:
            return None
        return line.rstrip('\r\n')
    
    def _parse_header(self, line):
        """Parse the header of a MySQL log file

        line[in]        A string, usually result of self._get_next_line()

        This method parses the header of a MySQL log file, that is the header
        found in the General and Slow Query log files. It sets attributes
        _version, _program, _port and _socket.
        Note that headers can repeat in a log file, for example, after a restart
        of the MySQL server.

        Example header:
        /usr/sbin/mysqld, Version: 5.5.17-log (Source distribution). started with:
        Tcp port: 0  Unix socket: /tmp/mysql.sock
        Time                 Id Command    Argument

        Raises LogParserError on errors.
        """
        if line is None:
            return
        # Header line containing executable and version, example:
        # /raid0/mysql/mysql/bin/mysqld, Version: 5.5.17-log (Source distribution). started with:
        info = _HEADER_VERSION_CRE.match(line)
        if not info:
            raise LogParserError("Could not read executable and version from header")
        program, major, minor, patch, extra = info.groups()

        # Header line with server information, example:
        # Tcp port: 3306  Unix socket: /tmp/mysql.sock
        line = self._get_next_line()
        info = _HEADER_SERVER_CRE.match(line)
        if not info:
            raise LogParserError("Malformed server header line: %s" % line)
        tcp_port, unix_socket = info.groups()

        # Throw away column header line, example:
        # Time                 Id Command    Argument
        self._get_next_line()

        self._version = (int(major), int(minor), int(patch), extra)
        self._program = program
        self._port = int(tcp_port)
        self._socket = unix_socket

    @property
    def version(self):
        """Returns the MySQL server version

        This property returns a tuple descriving the version of the 
        MySQL server producing the log file. The tuple looks like this:
            (major, minor, patch, extra)

        The extra part is optional and when not available will be None.
        Examples:
            (5,5,17,'log')
            (5,1,57,None)
        
        Note that the version can change in the same log file.

        Returns a tuple or None.
        """
        return self._version 

    @property
    def program(self):
        """Returns the executable which wrote the log file

        This property returns the full path to the executable which
        produced the log file.

        Note that the executable can change in the same log file.

        Returns a string or None.
        """
        return self._program
    
    @property
    def port(self):
        """Returns the MySQL server TCP/IP port

        This property returns the TCP/IP port on which the MySQL server
        was listening.

        Note that the TCP/IP port can change in the same log file.

        Returns an integer or None.
        """
        return self._port
    
    @property
    def socket(self):
        """Returns the MySQL server UNIX socket

        This property returns full path to UNIX socket used the MySQL server
        to accept incoming connections on UNIX-like servers.

        Note that the UNIX socket location can change in the same log file.

        Returns a string or None.
        """
        return self._socket
    
    @property
    def start_datetime(self):
        """Returns timestamp of first read log entry

        This property returns the timestamp of the first read log entry.

        Returns datetime.datetime-object or None.
        """
        return self._start_datetime
    
    @property
    def last_seen_datetime(self):
        """Returns timestamp of last read log entry

        This property returns the timestamp of the last read log entry.

        Returns datetime.datetime-object or None
        """
        return self._last_seen_datetime
    
    def __iter__(self):
        """Class is iterable
        
        Returns a LogParserBase-object.
        """
        return self
    
    def next(self):
        """Returns the next log entry

        Raises StopIteration when no more entries are available.

        Returns a LogEntryBase-object.
        """
        entry = self._parse_entry()
        if entry is None:
            raise StopIteration
        return entry

    def __str__(self):
        """String representation of LogParserBase
        """
        return "<%(clsname)s, MySQL v%(version)s>" % dict(
            clsname=self.__class__.__name__,
            version='.'.join([ str(v) for v in self._version[0:3]])+
                (self._version[3] or '')
            )

class GeneralQueryLog(LogParserBase):
    """Class implementing a parser for the MySQL General Query Log

    The GeneralQueryLog-class implements a parse for the MySQL General Query
    Log and has the following capabilities:
    - Parse General Query Log entries
    - Possibility to handle special commands
    - Keep track of MySQL sessions and remove them
    - Process log headers found later in the log file
    """
    def __init__(self, stream):
        """Constructor

        stream[in]      file type
        
        Raises LogParserError on errors.
        """
        super(GeneralQueryLog, self).__init__(stream)
        self._sessions = {}
        self._cached_logentry = None

        self._commands = {
            #'Sleep': None, 
            'Quit': self._handle_quit,
            'Init DB': self._handle_init_db,
            'Query': self._handle_multi_line,
            #'Field List': None,
            #'Create DB': None,
            #'Drop DB': None,
            #'Refresh': None,
            #'Shutdown': None,
            #'Statistics': None,
            #'Processlist': None,
            'Connect': self._handle_connect,
            #'Kill': None,
            #'Debug': None,
            #'Ping': None,
            #'Time': None,
            #'Delayed insert': None,
            #'Change user': None,
            #'Binlog Dump': None,
            #'Table Dump': None,
            #'Connect Out': None,
            #'Register Slave': None,
            'Prepare': self._handle_multi_line,
            'Execute': self._handle_multi_line,
            #'Long Data': None,
            #'Close stmt': None,
            #'Reset stmt': None,
            #'Set option': None,
            'Fetch': self._handle_multi_line,
            #'Daemon': None,
            #'Error': None,
        }
    
    def _new_session(self, session_id):
        """Create a new session using the given session ID

        session_id[in]      integer presenting a MySQL session

        Returns a dictionary.
        """
        self._sessions[session_id] = dict(
                database=None,
                user=None,
                host=None,
                time_last_action=None,
                to_delete=False)
        return self._sessions[session_id]
    
    def _handle_connect(self, entry, session, argument):
        """Handle a 'Connect'-command

        entry[in]       a GeneralQueryLogEntry-instance
        session[in]     a dictionary with current session information,
                        element of self._sessions
        argument[in]    a string, last part of a log entry

        This method reads user and database information from the argument of
        a 'Connect'-command. It sets the user, host and database for the
        current session and also sets the argument for the entry.

        """
        # Argument can be as follows:
        # root@localhost on test
        # root@localhost on
        try:
            connection, garbage, database = argument.split(' ')
        except ValueError:
            connection = argument.replace(' on','')
            database = None    
        session['user'], session['host'] = connection.split('@')
        session['database'] = database
        entry['argument'] = argument

    def _handle_init_db(self, entry, session, argument):
        """Handle an 'Init DB'-command

        entry[in]       a GeneralQueryLogEntry-instance
        session[in]     a dictionary with current session information,
                        element of self._sessions
        argument[in]    a string, last part of a log entry

        The argument parameter is always the database name.
        """
        # Example (of full line):
        #           3 Init DB   mysql
        session['database'] = argument
        entry['argument'] = argument

    def _handle_multi_line(self, entry, session, argument):
        """Handle a command which can span multiple lines
    
        entry[in]       a GeneralQueryLogEntry-instance
        session[in]     a dictionary with current session information,
                        element of self._sessions
        argument[in]    a string, last part of a log entry

        The argument parameter passed to this function is the last part of a
        General Query Log entry and usually is already the full query.

        This function's main purpose is to read log entries which span multiple
        lines, such as the Query and Prepare-commands.
        """
        # Examples:
        # 111205 10:01:14       6 Query SELECT Name FROM time_zone_name WHERE Time_zone_id = 417
        # 111205 10:03:28       6 Query SELECT Name FROM time_zone_name
        # WHERE Time_zone_id = 417
        argument_parts = [argument,]
        line = self._get_next_line()
        while line:
            if line.endswith('started with:'):
                self._cached_logentry = line
                break
            info = _GENERAL_ENTRY_CRE.match(line)
            if info is not None:
                self._cached_logentry = info.groups()
                break
            argument_parts.append(line)
            line = self._get_next_line()
        
        entry['argument'] = '\n'.join(argument_parts)
    
    def _handle_quit(self, entry, session, argument):
        """Handle the 'Quit'-command

        entry[in]       a GeneralQueryLogEntry-instance
        session[in]     a dictionary with current session information,
                        element of self._sessions
        argument[in]    a string, last part of a log entry

        This function sets a flag that the session can be removed from the
        session list.
        """
        # Example (of full line):
        # 111205 10:06:53       6 Quit
        session['to_delete'] = True

    def _parse_command(self, logentry, entry):
        """Parse a log entry from the General Query Log

        logentry[in]    a string or tuple
        entry[in]       an instance of GeneralQueryLogEntry

        The logentry-parameter is either a line read from the log file or
        the result of a previous attempt to read a command.
        The entry argument should be an instance of GeneralQueryLogEntry.
        It returns the entry or None if nothing could be read.

        Raises LogParserError on errors.

        Returns the GeneralQueryLogEntry-instance or None
        """
        if logentry is None:
            return None
        if isinstance(logentry, tuple):
            dt, session_id, command, argument = logentry
        elif logentry.endswith('started with:'):
            while logentry.endswith('started with:'):
                # We got a header
                self._parse_header(logentry)
                logentry = self._get_next_line()
                if logentry is None:
                    return None
            return self._parse_command(logentry, entry)
        else:
            info = _GENERAL_ENTRY_CRE.match(logentry)
            if info is None:
                raise LogParserError("Failed parsing command line: %s"\
                                     % logentry)
            dt, session_id, command, argument = info.groups()
        self._cached_logentry = None

        session_id = int(session_id)
        entry['session_id'] = session_id
        try:
            session = self._sessions[session_id]
        except KeyError:
            session = self._new_session(session_id)

        entry['command'] = command
        if dt is not None:
            entry['datetime'] = datetime.datetime.strptime(dt,
                                                           "%y%m%d %H:%M:%S")
            session['time_last_action'] = entry['datetime']
        else:
            entry['datetime'] = session['time_last_action']
        
        try:
            self._commands[command](entry, session, argument)
        except KeyError:
            # Generic command
            entry['argument'] = argument
        
        for key in entry.keys():
            if key in session:
                entry[key] = session[key]
        
        if session['to_delete'] is True:
            del self._sessions[session_id]
            del session

        return entry
        
    def _parse_entry(self):
        """Returns a parsed log entry

        The method _parse_entry() uses _parse_command() to parse
        a General Query Log entry. It is used by the iterator protocol methods.

        Returns a GeneralQueryLogEntry-instance or None.
        """
        entry = GeneralQueryLogEntry()
        if self._cached_logentry is not None:
            self._parse_command(self._cached_logentry,entry)
            return entry
        else:
            line = self._get_next_line()
        if line is None:
            return None

        self._parse_command(line,entry)
        return entry

class SlowQueryLog(LogParserBase):
    """Class implementing a parser for the MySQL Slow Query Log

    The SlowQueryLog-class implements a parser for the MySQL Slow Query Log and
    has the following capabilities:
    - Parse Slow Query Log entries
    - Process log headers found later in the log file
    - Parse connection and temporal information
    - Get statistics of the slow query
    """
    def __init__(self, stream):
        """Constructor

        stream[in]      A file type

        The stream argument must be a valid file type supporting for
        example the readline()-method. For example, the return of the build-in
        function open() can be used:
            SlowQueryLog(open("/path/to/mysql-slow.log"))
        
        Raises LogParserError on errors.
        """
        super(SlowQueryLog, self).__init__(stream)
        self._cached_line = None
        self._current_database = None
    
    def _parse_line(self, regex, line):
        """Parses a log line using given regular expression

        regex[in]   a SRE_Match-object
        line[in]    a string

        This function takes a log line and matches the regular expresion given
        with the regex argument. It returns the result of
        re.MatchObject.groups(), which is a tuple.

        Raises LogParserError on errors.

        Returns a tuple.
        """
        info = regex.match(line)
        if info is None:
            raise LogParserError('Failed parsing Slow Query line: %s' %
                                 line[:30])
        return info.groups()
    
    def _parse_connection_info(self, line, entry):
        """Parses connection info

        line[in]    a string
        entry[in]   a SlowQueryLog-instance

        The line paramater should be a string, a line read from the Slow Query
        Log. The entry argument should be an instance of SlowQueryLogEntry.

        Raises LogParserError on failure.
        """
        # Example:
        # # User@Host: root[root] @ localhost [127.0.0.1]
        (priv_user,
         unpriv_user,
         host,
         ip) = self._parse_line(_SLOW_USERHOST_CRE, line)

        entry['user'] = priv_user if priv_user else unpriv_user
        entry['host'] = host if host else ip

    def _parse_timestamp(self, line, entry):
        """Parses a timestamp

        line[in]    a string
        entry[in]   a SlowQueryLog-instance

        The line paramater should be a string, a line read from the Slow Query
        Log. The entry argument should be an instance of SlowQueryLogEntry.
        
        Raises LogParserError on failure.
        """
        # Example:
        # # Time: 111206 11:55:54
        info = self._parse_line(_SLOW_TIMESTAMP_CRE, line)

        entry['datetime'] = datetime.datetime.strptime(info[0],
                                                       "%y%m%d %H:%M:%S")
        if self._start_datetime is None:
            self._start_datetime = entry['datetime']
            self._last_seen_datetime = entry['datetime']
    
    def _parse_statistics(self, line, entry):
        """Parses statistics information

        line[in]    a string
        entry[in]   a SlowQueryLog-instance

        The line paramater should be a string, a line read from the Slow Query
        Log. The entry argument should be an instance of SlowQueryLogEntry.
        
        Raises LogParserError on errors.
        """
        # Example statistic line:
        # # Query_time: 0.101194  Lock_time: 0.000331 Rows_sent: 24  Rows_examined: 11624
        result = self._parse_line(_SLOW_STATS_CRE, line)
        
        entry['query_time'] = decimal.Decimal(result[0])
        entry['lock_time'] = decimal.Decimal(result[1])
        entry['rows_sent'] = int(result[2])
        entry['rows_examined'] = int(result[3])
    
    def _parse_query(self, line, entry):
        """Parses the query

        line[in]    a string
        entry[in]   a SlowQueryLog-instance

        The line paramater should be a string, a line read from the Slow Query
        Log. The entry argument should be an instance of SlowQueryLogEntry.
        
        Query entries in the Slow Query Log could span several lines. They can
        optionally start with a USE-command and have session variables, such as
        'timestamp', set before the actual query.
        """
        # Example:
        # SET timestamp=1323169459;
        # SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA 
        #    WHERE SCHEMA_NAME = 'mysql';
        # # User@Host: root[root] @ localhost [127.0.0.1]
        query = []
        while True:
            if line is None:
                break
            if line.startswith('use'):
                entry['database'] = self._current_database = line.split(' ')[1]
            elif line.startswith('SET timestamp='):
                entry['datetime'] = datetime.datetime.fromtimestamp(
                    int(line[14:].strip(';')))
            elif (line.startswith('# Time:') or line.startswith("# User@Host")
                or line.endswith('started with:')):
                break
            query.append(line)
            line = self._get_next_line()

        if 'database' in entry:
            # This is not always correct: connections without current database
            # will get the database name of the previous query. However, it's
            # more likely current database is set. Fix would be that the server
            # includes a USE-statement for every entry.
            if entry['database'] is None and self._current_database is not None:
                entry['database'] = self._current_database
        entry['query'] = '\n'.join(query)
        self._cached_line = line

    def _parse_entry(self):
        """Parse and returns an entry of the Slow Query Log

        Each entry of the slow log consists of:
        1. An optional time line
        2. A connection information line with user, hostname and database
        3. A line containing statistics for the query
        4. An optional "use <database>" line
        5. A line setting the timestamp, insert_id, and last_insert_id
           session variables
        6. An optional administartor command line "# administator command"
        7. An optional SQL statement or the query

        Returns a SlowQueryLogEntry-instance or None
        """
        if self._cached_line is not None:
            line = self._cached_line
            self._cached_line = None
        else:
            line = self._get_next_line()
        if line is None:
            return None

        while line.endswith('started with:'):
            # We got a header
            header = self._parse_header(line)
            line = self._get_next_line()
            if line is None:
                return None

        entry = SlowQueryLogEntry()

        if line.startswith('# Time:'):
            self._parse_timestamp(line, entry)
            line = self._get_next_line()

        if line.startswith('# User@Host:'):
            self._parse_connection_info(line, entry)
            line = self._get_next_line()

        if line.startswith('# Query_time:'):
            self._parse_statistics(line, entry)
            line = self._get_next_line()

        self._parse_query(line, entry)
        
        return entry

class LogEntryBase(dict):
    """Class inherited by GeneralQueryEntryLog and SlowQueryEntryLog
    
    This class has the following capabilities:
    - Inherits from dict
    - Dictionary elements can be accessed using attributes. For example,
      logentry['database'] is accessible like logentry.database

    Should not be used directly.
    """
    def __init__(self):
        self['datetime'] = None
        self['database'] = None
        self['user'] = None
        self['host'] = None
    
    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError("%s has no attribute '%s'" % (
                                 self.__class__.__name__,name))

class GeneralQueryLogEntry(LogEntryBase):
    """Class representing an entry of the General Query Log

    """
    def __init__(self):
        """Constructor

        GeneralQueryLogEntry inherits from LogEntryBase, which inherits from
        dict. Instances of GeneralQueryLogEntry can be used just like
        dictionaries.
        """
        super(GeneralQueryLogEntry,self).__init__()
        self['session_id'] = None
        self['command'] = None
        self['argument'] = None

    def __str__(self):
        """String representation of GeneralQueryLogEntry
        """
        param = self.copy()
        param['clsname'] = self.__class__.__name__
        try:
            if len(param['argument']) > 30:
                param['argument'] = param['argument'][:28] + '..'
        except TypeError:
            pass # Nevermind when param['argument'] was not a string.
        try:
            param['datetime'] = param['datetime'].strftime("%Y-%m-%d %H:%M:%S")
        except AttributeError:
            param['datetime'] = ''
        return ("<%(clsname)s %(datetime)s [%(session_id)s]"
                " %(command)s: %(argument)s>" % param)

class SlowQueryLogEntry(LogEntryBase):
    """Class representing an entry of the Slow Query Log

    SlowQueryLogEntry inherits from LogEntryBase, which inherits from dict.
    Instances of SlowQueryLogEntry can be used just like dictionaries.
    """
    def __init__(self):
        """Constructor
        """
        super(SlowQueryLogEntry,self).__init__()
        self['query'] = None
        self['query_time'] = None
        self['lock_time'] = None
        self['rows_examined'] = None
        self['rows_sent'] = None

    def __str__(self):
        """String representation of SlowQueryLogEntry
        """
        param = self.copy()
        param['clsname'] = self.__class__.__name__
        try:
            param['datetime'] = param['datetime'].strftime("%Y-%m-%d %H:%M:%S")
        except AttributeError:
            param['datetime'] = ''
        return ("<%(clsname)s %(datetime)s [%(user)s@%(host)s] "
                "%(query_time)s/%(lock_time)s/%(rows_examined)s/%(rows_sent)s>"
               ) % param
