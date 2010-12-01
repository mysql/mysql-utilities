#!/usr/bin/env python

import os
import mysql_test
from mysql.utilities.exception import MySQLUtilError, MUTException

class test(mysql_test.System_test):
    """Import Data
    This test executes the import utility on a single server.
    It uses the mysqldbexport utility to generate files for importing.
    """

    def check_prerequisites(self):
        # Need at least one server.
        self.server1 = None
        self.need_servers = False
        if not self.check_num_servers(3):
            self.need_servers = True
        return self.check_num_servers(1)

    def setup(self):
        self.export_import_file = "test_run.txt"
        num_servers = self.servers.num_servers()
        if self.need_servers:
            try:
                self.servers.spawn_new_servers(num_servers+2)
            except MySQLUtilError, e:
                raise MUTException("Cannot spawn needed servers: %s" % \
                                   e.errmsg)
        else:
            num_servers -= 2 # Get last 2 servers in list
        self.server1 = self.servers.get_server(num_servers)
        self.server2 = self.servers.get_server(num_servers+1)
        self.drop_all()
        data_file = os.path.normpath(self.testdir + "/data/basic_data.sql")
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
        except MySQLUtilError, e:
            raise MUTException("Failed to read commands from file %s: " % \
                               data_file + e.errmsg)
        return True
    
    def run_import_test(self, expected_res, from_conn, to_conn, format, type,
                        comment, export_options=None, import_options=None):
    
        export_cmd = "mysqldbexport.py %s util_test --export=" % from_conn
        export_cmd += type + " --format=%s " % format
        if export_options is not None:
            export_cmd += export_options
        export_cmd += " > %s" % self.export_import_file
        
        import_cmd = "mysqldbimport.py %s " % to_conn
        import_cmd += "%s --import=" % self.export_import_file
        import_cmd += type + " --format=%s " % format
        if import_options is not None:
            import_cmd += import_options
            
        self.results.append(comment + "\n")
        
        # Precheck: check db and save the results.
        self.results.append("BEFORE:\n")
        self.results.append(self.check_objects(self.server2, "util_test"))

        # First run the export to a file.
        res = self.run_test_case(0, export_cmd, "Running export...")
        if not res:
            raise MUTException("EXPORT: %s: failed" % comment)
        
        # Second, run the import from a file.
        res = self.run_test_case(expected_res, import_cmd, "Running import...")
        if not res:
            raise MUTException("IMPORT: %s: failed" % comment)
        
        # Now, check db and save the results.
        self.results.append("AFTER:\n")
        self.results.append(self.check_objects(self.server2, "util_test"))
            
    def run(self):
        self.res_fname = self.testdir + "result.txt"
        
        from_conn = "--server=%s" % self.build_connection_string(self.server1)
        to_conn = "--server=%s" % self.build_connection_string(self.server2)

        _FORMATS = ("SQL", "CSV", "TAB", "GRID", "VERTICAL")
        _DISPLAYS = ("BRIEF", "FULL") #  We will do "NAMES" in import_errors
        test_num = 1
        for display in _DISPLAYS:
            for format in _FORMATS:
                try:
                    comment = "Test Case %d : Testing import with " % test_num
                    comment += "%s format " % format
                    comment += "and %s display" % display
                    # We test DEFINITIONS and DATA only in other tests
                    self.run_import_test(0, from_conn, to_conn,
                                         format, "BOTH", comment,
                                         " --display=%s" % display)
                except MUTException, e:
                    raise e
                self.drop_db(self.server2, "util_test")
                test_num += 1
        return True
          
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        try:
            res = server.exec_query("SHOW DATABASES LIKE 'util_%%'")
        except:
            return True # Ok to exit here as there weren't any dbs to drop
        try:
            res = server.exec_query("DROP DATABASE %s" % db)
        except:
            return False
        return True
    
    def drop_all(self):
        try:
            self.drop_db(self.server1, "util_test")
        except:
            return False
        try:
            self.drop_db(self.server2, "util_test")
        except:
            pass # ok if this fails - it is a spawned server 
        return True

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except:
                pass
        if self.export_import_file:
            try:
                os.unlink(self.export_import_file)
            except:
                pass
        return self.drop_all()




