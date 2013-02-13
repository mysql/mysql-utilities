#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
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
import os
import mutlib
from mysql.utilities.exception import MUTLibError, UtilDBError, UtilError

_WARNING = "WARNING: Lock in progress. You must call unlock() to unlock your tables."

_TABLES = [
    ("util_test.t1", 'READ'),
    ("util_test.t2", 'READ'),
    ("util_test.t3", 'READ'),
]

_BAD_TABLE = [
    ("util_test.t1", 'READ'),
    ("util_test.notthere", 'READ'),
]

_LOCKTESTS = [
    # lock_test, tables, Lock() fail?, Unlock() fail? : True = call expected to fail
    ('no-locks', _TABLES, False, False),
    ('lock-all', _TABLES, False, False),
    ('snapshot', _TABLES, False, False),
    ('UNKNOWN', _TABLES, True, True),
    ('', _TABLES, True, True),
    # sentinel value to trigger skipping unlock step
    ('SKIP_UNLOCK', _TABLES, False, True),
    ('lock-all', _BAD_TABLE, True, True),
]

class test(mutlib.System_test):
    """locking
    This test exercises the Locking class methods and errors.
    """

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        self.check_gtid_unsafe()
        self.options = {
            'skip_procs'  : False,
            'skip_funcs'  : False,
            'skip_events' : False,
            'locking'     : "",
            'silent'      : True,  # turn off prints in Lock() class
            'tables'      : [],
        }
        self.server1 = self.servers.get_server(0)
        data_file = os.path.normpath("./std_data/basic_data.sql")
        self.drop_all()
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
        except MUTLibError, e:
            raise MUTLibError("Failed to read commands from file %s: " % \
                               data_file + e.errmsg)
        return True
    
    def run(self):
        from mysql.utilities.common.lock import Lock
        
        self.server1 = self.servers.get_server(0)
        
        test_num = 1
        
        # Here we test the locking and unlocking of tables (if applicable)
        # for the locking types.
        comment = "Test case %s - test locking type '%s'"
        for lock_test in _LOCKTESTS:
            lock = None
            comment_str = comment % (test_num, lock_test[0])
            res_entry = {
                'test_case'   : comment_str,
                'lock_res'    : (0,""),
                'unlock_res'  : (0,""),
                'lock_fail'   : lock_test[2],
                'unlock_fail' : lock_test[3],
            }

            if lock_test[0] == 'SKIP_UNLOCK':
                self.options['locking'] = 'lock-all'
            else:
                self.options['locking'] = lock_test[0]
            try:
                lock = Lock(self.server1, lock_test[1], self.options)
            except UtilError, e:
                res_entry['lock_res'] = (1, e.errmsg)

            if lock is not None:
                if lock_test[0] != 'SKIP_UNLOCK':
                    try:
                        lock.unlock()
                    except UtilError, e:
                        res_entry['unlock_res'] = (1, e.errmsg)
                else:
                    res = lock.__del__()
                    if res[0:7] == 'WARNING':
                        res_entry['unlock_res'] = (1, res)
                    else:
                        res_entry['unlock_res'] = (1, "Wrong result: %s" % res)
            else:
                res_entry['unlock_res'] = (1, "Unlock() skipped.")
                    
            self.results.append(res_entry)
            if self.debug:
                print comment_str
                print "    expected to fail:", res_entry['lock_fail'], \
                      res_entry['unlock_fail']
                print "    locking step:", res_entry['lock_res'][0], \
                      res_entry['lock_res'][1]
                print "  unlocking step:", res_entry['unlock_res'][0], \
                      res_entry['unlock_res'][1]
            test_num += 1
                            
        return True
          
    def get_result(self):
        msg = None
        for result in self.results:

            if self.debug:
                print result['test_case']
                print "  expected results for locking step:", \
                      result['lock_res'][0], result['lock_res'][1]
                print "  expected results for unlocking step:", \
                      result['unlock_res'][0], result['unlock_res'][1]
                
            if type(result) != dict:
                return (False, "Invalid test result: '%s'.\n" % result)
            if not result['lock_fail'] and result['lock_res'][0] != 0:
                return (False, "Lock step failed for %s." %
                        result['lock_res'][1])
            elif result['lock_fail'] and result['lock_res'][0] != 1:
                return (False, "Lock step passed but should have failed.")
            if not result['unlock_fail'] and result['unlock_res'][0] != 0:
                return (False, "Unlock step failed for %s." %
                        result['unlock_res'][1])
            elif result['unlock_fail'] and result['unlock_res'][0] != 1:
                return (False, "Unlock step passed but should have failed.")

        return (True, None)
    
    def record(self):
        # Not a comparative test, returning True
        return True
    
    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        try:
            res = server.exec_query("SHOW DATABASES LIKE 'util_%'")
        except:
            return True # Ok to exit here as there weren't any dbs to drop
        try:
            res = server.exec_query("DROP DATABASE %s" % db)
        except:
            return False
        return True
    
    def drop_all(self):
        res1, res2 = True, True
        try:
            self.drop_db(self.server1, "util_test")
        except:
            res1 = False
        try:
            self.drop_db(self.server1, "util_db_clone")
        except:
            res2 = False
        try:
            self.server1.exec_query("DROP USER 'joe'@'user'")
        except:
            pass
        return res1 and res2

    def cleanup(self):
        return self.drop_all()




