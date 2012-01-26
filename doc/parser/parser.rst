#############################################################
:mod:`mysql.utilities.parser` --- Parse MySQL Log Files
#############################################################

.. module:: mysql.utilities.parser

This module provides classes for parsing MySQL log files.
Currently, *Slow Query Log* and *General Query Log* are supported.

Classes
-------

.. class:: GeneralQueryLog(stream)
    
    This class parses the MySQL General Query Log. Instances are iterable,
    but the class does not provide multiple independent iterators.
    
    For example, to read the log and print the entries:
    
    >>> general_log = open("/var/lib/mysql/mysql.log")
    >>> log = GeneralQueryLog(general_log)
    >>> for entry in log:
    ...     print entry
    
    :type stream: file type
    :param stream: a valid file type; for example, the result of
                   the built-in Python function `open()`_
    
    .. attribute:: version
    
    :returns: Version of the MySQL server that produced the log
    :rtype: tuple
    
    .. attribute:: program
    
    :returns: Full path of the MySQL server executable
    :rtype: str
    
    .. attribute:: port
    
    :returns: TCP/IP port on which the MySQL server was listening
    :rtype: int
    
    .. attribute:: socket
    
    :returns: Full path of the MySQL server Unix socket
    :rtype: str
    
    .. attribute:: start_datetime
    
    :returns: Date and time of the first read log entry
    :rtype: datetime.datetime
    
    .. attribute:: lastseen_datetime
    
    :returns: Date and time of the last read log entry
    :rtype: datetime.datetime

.. class:: SlowQueryLog(stream)

    This class parses the MySQL Slow Query Log. Instances are iterable,
    but the class does not provide multiple independent iterators.
    
    For example, to read the log and print the entries:

    >>> slow_log = open("/var/lib/mysql/mysql-slow.log")
    >>> log = SlowQueryLog(slow_log)
    >>> for entry in log:
    ...     print entry

    :type stream: file type
    :param stream: a valid file type; for example, the result of
                   the built-in Python function `open()`_

    .. attribute:: version

    :returns: Version of the MySQL server that produced the log
    :rtype: tuple

    .. attribute:: program

    :returns: Full path of the MySQL server executable
    :rtype: str

    .. attribute:: port

    :returns: TCP/IP port on which the MySQL server was listening
    :rtype: int

    .. attribute:: socket

    :returns: Full path of the MySQL server Unix socket
    :rtype: str

    .. attribute:: start_datetime

    :returns: Date and time of the first read log entry
    :rtype: datetime.datetime

    .. attribute:: lastseen_datetime

    :returns: Date and time of the last read log entry
    :rtype: datetime.datetime

.. References
.. ----------
.. _`open()`: http://docs.python.org/library/functions.html#open
