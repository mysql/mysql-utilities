#!/usr/bin/env python

import os
import mutlib
from mysql.utilities.exception import MUTLibError, UtilDBError
from mysql.utilities.common.tools import get_tool_path

_TRANSFORM_FILE = "diff_output.txt"

_CREATE_DB = "CREATE DATABASE `%s`"

_TEST_CASES = [
    # Direction a->b
    {
        'run_util'   : True,   # If true, run utility
        'options'    : " --quiet --difftype=sql --changes-for=server1 > %s" % _TRANSFORM_FILE,
        'comment'    : "Test case %d changes-for = server1 : %s",
        # If true, run startup commands, load data and create objects
        'load_data'  : True,
        'exp_result' : 1,
    },
    # Do consume test (specified in run() method below)
    {
        'run_util'   : False,   # If true, run utility
        'comment'    : "Test case %d consume transformation information : %s",
        'run_on'     : 'server1',
        'load_data'  : False,
        'exp_result' : 0,
    },
    # Check to ensure compliance of transformation
    {
        'run_util'   : True,   # If true, run utility
        'options'    : " --difftype=sql --changes-for=server1 ",
        'comment'    : "Test case %d changes-for = server1 post transform : %s",
        'load_data'  : False,
        'exp_result' : 0,
    },
    # Direction a<-b
    {
        'run_util'   : True,   # If true, run utility
        'options'    : " --quiet --difftype=sql --changes-for=server2 > %s" % \
                       _TRANSFORM_FILE,
        'comment'    : "Test case %d changes-for = server2 : %s",
        'load_data'  : True, # If true, load the data and create objects
        'exp_result' : 1,
    },
    # Do consume test (specified in run() method below)
    {
        'run_util'   : False,   # If true, run utility
        'comment'    : "Test case %d consume transformation information : %s",
        'run_on'     : 'server2',
        'load_data'  : False,
        'exp_result' : 0,
    },
    # Check to ensure compliance of transformation
    {
        'run_util'   : True,   # If true, run utility
        'options'    : " --difftype=sql --changes-for=server2 ",
        'comment'    : "Test case %d changes-for = server2 post transform : %s",
        'load_data'  : False,
        'exp_result' : 0,
    },
    # Direction a<->b with dir = a
    {
        'run_util'   : True,   # If true, run utility
        'options'    : " --quiet --difftype=sql --changes-for=server1 " + \
                       "--show-reverse ",
        'comment'    : "Test case %d changes-for = server1 with reverse : %s",
        'load_data'  : True, # If true, load the data and create objects
        'exp_result' : 1,
    },
    # Direction a<->b with dir = b
    {
        'run_util'   : True,   # If true, run utility
        'options'    : " --quiet --difftype=sql --changes-for=server2 " + \
                       "--show-reverse ",
        'comment'    : "Test case %d changes-for = server2 with reverse : %s",
        'load_data'  : True, # If true, load the data and create objects
        'exp_result' : 1,
    },
]

class test(mutlib.System_test):
    """Template for diff_<object>_sql tests
    This test executes a set of test cases for a given object definition pair.
    It is a value result test.
    
    The pair is stored as list of dictionary items in the following format:
  
        test_object = {
            'db1'             : <name of first database>,
            'db2'             : <name of second database>,
            'object_name'     : <name of object>,
            'server1_object'  : <create statement for first server>,
            'server2_object'  : <create statement for second server>,
            'comment'         : <comment to be appended to test case name>,
            'startup_cmds'    : <array of commands to execute before test case>,
            'shutdown_cmds'   : <array of commands to execute after test case>,
            # OPTIONAL - use for error code checking
            'error_codes'     : <array of 7 integers used for checking errors>,
                                # default = 1,0,0,1,0,0,1,1
            # OPTIONAL - use for loading data (e.g. INSERT INTO)
            'server1_data'    : <array of insert commands for server1>
            'server2_data'    : <array of insert commands for server2>
        }
        self.test_objects.append(test_object)
    
    For item in the dictionary of test objects, the following test cases are
    executed:
    
        - operation generated with --difftype=sql option, changes-for=server1
        - SQL consumed
        - operation rerun and check result against 'expected_result'
        - operation generated with --difftype=sql option, changes-for=server2
        - SQL consumed
        - operation rerun and check result against 'expected_result'
        - operation generated with --difftype=sql option,
          changes-for=server1 with show-reverse
        - operation generated with --difftype=sql option,
          changes-for=server2 with show-reverse
        
    To specify a new test object, do so in the setup method as described above
    and call the template setup method. You can add multiple object pairs to
    the list self.test_objects so that you can test different variants of the
    CREATE statement to check for the various mechanisms of how diff generates
    the SQL statements.
    
    Note: the expected result for all test cases is 1 (errors found). It
          shall be considered an error if this returns 0. Similarly, all
          consumption runs is expected to generate a result of 0 and any other
          value is considered an error.
          
    You must supply the utility name via self.utility. Set it to either
    'mysqldiff.py' for diff_sql* tests or 'mysqldbcompare.py' for
    db_compare_sql* tests. Set it in the setup *before* calling
    test_sql_template.test.setup().
          
    """

    def check_prerequisites(self):
#        if self.servers.get_server(0).check_version_compat(5, 6, 5):
#            raise MUTLibError("Test requires server version prior to 5.6.5")
        self.test_objects = []
        
        # Need at least one server.
        self.server1 = None
        self.server2 = None
        self.need_server = False
        if not self.check_num_servers(2):
            self.need_server = True
        return self.check_num_servers(1)

    def setup(self):
        self.res_fname = "result.txt"
        self.server1 = self.servers.get_server(0)
        if self.need_server:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError, e:
                raise MUTLibError("Cannot spawn needed servers: %s" % \
                                   e.errmsg)
        self.server2 = self.servers.get_server(1)
        
        s1_conn = "--server1=" + self.build_connection_string(self.server1)
        s2_conn = "--server2=" + self.build_connection_string(self.server2)
       
        self.base_cmd = "%s %s %s " % (self.utility, s1_conn, s2_conn)

        rows = self.server1.exec_query("SHOW VARIABLES LIKE 'basedir'")
        if rows:
            basedir = rows[0][1]
        else:
            raise MUTLibError("Unable to determine basedir of running "
                                 "server.")

        self.mysql_path = get_tool_path(basedir, "mysql")
        
        return True
    
    def run(self):
        # Run the test cases for each object
        test_num = 1
        for obj in self.test_objects:
            obj['test_case_results'] = []
            for i in range(0,len(_TEST_CASES)):
                comment = _TEST_CASES[i]['comment'] % (test_num, obj['comment'])
                
                if _TEST_CASES[i]['load_data']:
                    self._drop_all(obj)  # It's Ok if this fails
                    self.server1.exec_query(_CREATE_DB % obj['db1'])
                    self.server2.exec_query(_CREATE_DB % obj['db2'])

                if _TEST_CASES[i]['run_util']:
                        
                    if _TEST_CASES[i]['load_data']:
                        # Run any startup commands listed
                        for cmd in obj['startup_cmds']:
                            self.server1.exec_query(cmd)
                            self.server2.exec_query(cmd)
                        # Create the objects
                        if obj['server1_object'] != '':
                            self.server1.exec_query(obj['server1_object'])
                        if obj['server2_object'] != '':
                            self.server2.exec_query(obj['server2_object'])

                        # Do data loads                 
                        for cmd in obj.get('server1_data', []):
                            self.server1.exec_query(cmd)
                        for cmd in obj.get('server2_data', []):
                            self.server2.exec_query(cmd)

                    if obj['object_name'] == "": # we're testing whole dbs
                        cmd_opts = "%s:%s %s" % (obj['db1'], obj['db2'],
                                                 _TEST_CASES[i]['options'])
                    else:
                        cmd_opts = "%s.%s:%s.%s %s" % \
                                   (obj['db1'], obj['object_name'], obj['db2'],
                                    obj['object_name'],
                                    _TEST_CASES[i]['options'])
                    res = self.run_test_case_result(self.base_cmd + cmd_opts,
                                                    comment)
                    
                    if _TEST_CASES[i]['load_data']:
                        # Run any shutdown commands listed
                        for cmd in obj['shutdown_cmds']:
                            self.server1.exec_query(cmd)
                            self.server2.exec_query(cmd)
                    
                else:
                    if self.debug:
                        print "\n%s" % comment
                        
                    if _TEST_CASES[i]['run_on'] == 'server1':
                        conn_val = self.get_connection_values(self.server1)
                    else:
                        conn_val = self.get_connection_values(self.server2)
                        
                    command = "%s -uroot " % self.mysql_path
                    if conn_val[1] is not None and len(conn_val[1]) > 0:
                        command += "-p%s " % conn_val[1]
                    if conn_val[2] is not None and len(conn_val[2]) > 0:
                        if conn_val[2] != "localhost":
                            command += "-h %s " % conn_val[2]
                        else:
                            command += "-h 127.0.0.1 " 
                    if conn_val[3] is not None:
                        command += "--port=%s " % conn_val[3]
                    if conn_val[4] is not None:
                        command += "--socket=%s " % conn_val[4]
                    command += " < %s" % _TRANSFORM_FILE
                    res = self.exec_util(command, self.res_fname, True)

                    if self.debug:
                        # display results of command in _TRANSFORM_FILE
                        print "\nContents of output file:"
                        t_file = open(_TRANSFORM_FILE, 'r+')
                        for line in t_file.readlines():
                            print line,
                        t_file.close()                        

                error_codes = obj.get('error_codes', None)
                if error_codes is not None and len(error_codes) >= i+1:
                    exp_res = error_codes[i]
                else:
                    exp_res = _TEST_CASES[i]['exp_result']
                obj['test_case_results'].append((res, exp_res, comment))
                test_num += 1

        return True
          
    def get_result(self):
        # Here we check the result from execution of each test object.
        # We check all and show a list of those that failed.
        failed_object_tests = []
        for obj in self.test_objects:
            try:
                for result in obj['test_case_results']:
                    if result[0] != result[1]:
                        failed_object_tests.append(result)
            except:
                return (False, "No test results found for object test "
                        "diff %s %s comment: %s" % (obj['db1'], obj['db2'],
                                                    obj['comment']))
        if len(failed_object_tests) > 0:
            msg = ""
            for result in failed_object_tests:
                msg += "\n%s\nExpected result = " % result[2] + \
                        "%s, actual result = %s.\n" % (result[1], result[0])
            return (False, msg)
            
        return (True, '')
    
    def record(self):
        return True # Not a comparative test
    
    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        try:
            res = server.exec_query("DROP DATABASE `%s`" % db)
        except:
            return False
        return True
    
    def _drop_all(self, test_object):
        self.drop_db(self.server1, test_object["db1"])
        self.drop_db(self.server2, test_object["db2"])
        return True

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        os.unlink(_TRANSFORM_FILE)
        # Make sure all databases have been dropped. It is Ok if this fails.
        for obj in self.test_objects:
            self._drop_all(obj)
        return True
