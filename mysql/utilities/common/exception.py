#!/usr/bin/env python
#
# Copyright (c) 2010, Oracle and/or its affiliates. All rights reserved.
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#

"""
This file contains the exceptions used by MySQL Utilities and their libraries.
"""

class Error(Exception):
    pass

class OptionError(Exception):
    """
    Exception thrown when there either an option is missing or incorrect.
    """

    def __init__(self, msg):
        self.msg = msg


class MySQLUtilError(Exception):
    """ General errors
    
    This exception class is used to report errors from MySQL utilities
    command and common code.
    """
    
    def __init__(self, message, options=None):
        self.args = (message, options)
        self.errmsg = message
        self.options = options

class FormatError(Error):
    """An entity was supplied in the wrong format."""
    pass

class EmptyResultError(Error):
    """An entity was supplied in the wrong format."""
    pass

class MUTException(Exception):
    """ MUT errors
    
    This exception class is used to report errors from the testing subsystem.
    """
    
    def __init__(self, message, options=None):
        self.args = (message, options)
        self.errmsg = message
        self.options = options
    

