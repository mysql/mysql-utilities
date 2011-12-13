#!/usr/bin/env python

import os
import sys
import mutlib
from mysql.utilities.exception import MUTLibError, UtilDBError
from mysql.utilities.common.format import format_tabular_list

_DATA_SQL = [
    "CREATE DATABASE apostrophe",
    "CREATE TABLE apostrophe.t1 (a char(30), b blob)",
    "INSERT INTO apostrophe.t1 VALUES ('1', 'test single apostrophe''')",
    "INSERT INTO apostrophe.t1 VALUES ('2', 'test 2 '' apostrophes ''')",
    "INSERT INTO apostrophe.t1 VALUES ('3', 'test three'' apos''trophes''')",
    "INSERT INTO apostrophe.t1 VALUES ('4 '' ', 'test '' in 2 columns')",
]

class test(mutlib.System_test):
    """simple db clone
    This test executes a simple clone of a database on a single server that
    contains a table with apostrophes in the text.
    """

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        self.drop_all()
        try:
            for command in _DATA_SQL:
                res = self.server1.exec_query(command)
        except MUTLibError, e:
            raise MUTLibError("Failed to create test data %s: " % \
                               data_file + e.errmsg)
        return True
    
    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"
        
        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server1)
       
        # dump if debug run
        if self.debug:
            print "\n# Dump of data to be cloned:"
            rows = self.server1.exec_query("SELECT * FROM apostrophe.t1")
            format_tabular_list(sys.stdout, ['char_field', 'blob_field'], rows)
       
        # Test case 1 - clone a sample database
        cmd = "mysqldbcopy.py %s %s " % (from_conn, to_conn) + \
              " apostrophe:apostrophe_clone"
        try:
            res = self.exec_util(cmd, self.res_fname)
            self.results.append(res)
        except MUTLibError, e:
            raise MUTLibError(e.errmsg)
          
        # dump if debug run
        if self.debug:
            print "\n# Dump of data cloned:"
            rows = self.server1.exec_query("SELECT * FROM apostrophe_clone.t1")
            format_tabular_list(sys.stdout, ['char_field', 'blob_field'], rows)
            
        return True

    def get_result(self):
        msg = None
        if self.server1 and self.results[0] == 0:
            query = "SHOW DATABASES LIKE 'apostrophe_%'"
            try:
                res = self.server1.exec_query(query)
                if res and res[0][0] == 'apostrophe_clone':
                    return (True, None)
            except UtilDBError, e:
                raise MUTLibError(e.errmsg)
        return (False, ("Result failure.\n", "Database clone not found.\n"))
    
    def record(self):
        # Not a comparative test, returning True
        return True
    
    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        try:
            res = server.exec_query("SHOW DATABASES LIKE 'apostrophe%'")
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
            self.drop_db(self.server1, "apostrophe")
        except:
            res1 = False
        try:
            self.drop_db(self.server1, "apostrophe_clone")
        except:
            res2 = False
        return res1 and res2

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()




