#
# Copyright (c) 2010, 2011, Oracle and/or its affiliates. All rights reserved.
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
This file contains the exceptions used by MySQL Utilities and their libraries.
"""

class Error(Exception):
    pass

class UtilError(Exception):
    """General errors raised by command modules to user scripts.
    
    This exception class is used to report errors from MySQL utilities
    command modules and are used to communicate known errors to the user.
    """
    
    def __init__(self, message, errno=0):
        self.args = (message, errno)
        self.errmsg = message
        self.errno = errno


class UtilDBError(UtilError):
    """Database errors raised when the mysql database server operation fails.
    """
    
    def __init__(self, message, errno=0, db=None):
        UtilError.__init__(self, message, errno)
        self.db = db


class UtilRplError(UtilError):
    """Replication errors raised during replication operations.
    """
    
    def __init__(self, message, errno=0, master=None, slave=None):
        UtilError.__init__(self, message, errno)
        self.master = master
        self.slave = slave


class UtilBinlogError(UtilError):
    """Errors raised during binary log operations.
    """
    
    def __init__(self, message, errno=0, file=None, pos=0):
        UtilError.__init__(self.message, errno)
        self.file = file
        self.pos = pos


class UtilTestError(UtilError):
    """Errors during test execution of command or common module tests.
    
    This exception is used to raise and error and supply a return value for
    recording the test result.
    """
    def __init__(self, message, errno=0, result=None):
        UtilError.__init__(self, message, errno)
        self.result = result
    

class FormatError(Error):
    """An entity was supplied in the wrong format."""
    pass

class EmptyResultError(Error):
    """An entity was supplied in the wrong format."""
    pass

class MUTLibError(Exception):
    """MUT errors
    
    This exception class is used to report errors from the testing subsystem.
    """
    
    def __init__(self, message, options=None):
        self.args = (message, options)
        self.errmsg = message
        self.options = options
    
class LogParserError(UtilError):
    def __init__(self, message=''):
        super(LogParserError,self).__init__(message)
