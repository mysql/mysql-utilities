#!/usr/bin/env python
#
# Copyright (c) 2011, 2012 Oracle and/or its affiliates. All rights reserved.
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
This file contains the methods for checking consistency among two databases.
"""

from mysql.utilities.exception import UtilError, UtilDBError

# The following are the queries needed to perform table locking.

LOCK_TYPES = ['READ', 'WRITE']

_SESSION_ISOLATION_LEVEL = \
  "SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ"

_START_TRANSACTION = "START TRANSACTION WITH CONSISTENT SNAPSHOT"

_LOCK_WARNING = "WARNING: Lock in progress. You must call unlock() " + \
                "to unlock your tables."

_FLUSH_TABLES_READ_LOCK = "FLUSH TABLES WITH READ LOCK"

class Lock(object):
    
    def __init__(self, server, table_list, options={}):
        """Constructor
        
        Lock a list of tables based on locking type. Locking types and their
        behavior is as follows:
        
           - (default) use consistent read with a single transaction
           - lock all tables without consistent read and no transaction
           - no locks, no transaction, no consistent read
           - flush (replication only) - issue a FTWRL command

        server[in]         Server instance of server to run locks
        table_list[in]     list of tuples (table_name, lock_type)
        options[in]        dictionary of options
                           locking = [snapshot|lock-all|no-locks|flush],
                           verbosity int
                           silent bool
                           rpl_mode string
        """
        self.locked = False
        self.silent = options.get('silent', False)
        # Determine locking type
        self.locking = options.get('locking', 'snapshot')
        self.verbosity = options.get('verbosity', 0)
        if self.verbosity is None:
            self.verbosity = 0
        else:
            self.verbosity = int(self.verbosity)
        
        self.server = server
        self.table_list = table_list
  
        # If no locking, we're done
        if self.locking == 'no-locks':
            return
        
        elif self.locking == 'lock-all':
            # Check lock requests for validity
            table_locks = []
            for tablename, locktype in table_list:
                if locktype.upper() not in LOCK_TYPES:
                    raise UtilDBError("Invalid lock type '%s' for table '%s'."
                                      % (locktype, tablename))
                # Build LOCK TABLE command
                table_locks.append("%s %s" % (tablename, locktype))
            lock_str = "LOCK TABLE "
            lock_str += ', '.join(table_locks)

            if self.verbosity >= 3 and not self.silent:
                print '# LOCK STRING:', lock_str
    
            # Execute the lock
            self.server.exec_query(lock_str)
    
            self.locked = True

        elif self.locking == 'snapshot':
            self.server.exec_query(_SESSION_ISOLATION_LEVEL)
            self.server.exec_query(_START_TRANSACTION)
            
        # Execute a FLUSH TABLES WITH READ LOCK for replication uses only
        elif self.locking == 'flush' and options.get("rpl_mode", None):
            if self.verbosity >= 3 and not self.silent:
                print "# LOCK STRING: %s" % _FLUSH_TABLES_READ_LOCK
            self.server.exec_query(_FLUSH_TABLES_READ_LOCK)
            self.locked = True
        else:
            raise UtilError("Invalid locking type: '%s'." % self.locking)

    
    def __del__(self):
        """Destructor
        
        Returns string - warning if the lock has not been disengaged.
        """
        if self.locked:
            return _LOCK_WARNING

        return None
    
    
    def unlock(self, abort=False):
        """Release the table lock.
        """
        if not self.locked:
            return

        if self.verbosity >= 3 and not self.silent and \
           self.locking != 'no-locks':
            print "# UNLOCK STRING:",
        # Call unlock:
        if self.locking in ['lock-all', 'flush']:
            if self.verbosity >= 3 and not self.silent:
                print "UNLOCK TABLES"
            self.server.exec_query("UNLOCK TABLES")
            self.locked = False
        
        # Stop transaction if locking == 0
        elif self.locking == 'snapshot':
            if not abort:
                if self.verbosity >= 3 and not self.silent:
                    print "COMMIT"
                self.server.exec_query("COMMIT")
            else:
                self.server.exec_queery("ROLLBACK")
                if self.verbosity >= 3 and not self.silent:
                    print "ROLLBACK"
                
