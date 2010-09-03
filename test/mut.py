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
This file contains the MySQL Utilities Test facility for running system
tests on the MySQL Utilities.
"""

import datetime
import optparse
import os
import re
import sys
import time
import MySQLdb
from mysql.utilities.common import Server
from mysql.utilities.common import parse_connection

# Constants
NAME = "MySQL Utilities Test - mut "
VERSION = "1.0.0 alpha"
DESCRIPTION = "mut - run tests on the MySQL Utilities"
USAGE = "%prog --server=user:passwd@host:port:socket test1 test2"

# Default settings
TEST_PATH = "./test"
UTIL_PATH = "../scripts"
PRINT_WIDTH = 75
BOLD_ON = ''
BOLD_OFF = ''
if os.name == "posix":
    BOLD_ON = '\033[1m'
    BOLD_OFF = '\033[0m'
START_PORT = 3310

# Utility function
def print_elapsed_time(start_test):
    """ Print the elapsed time to stdout (screen)
    
    start_test[in]      The starting time of the test
    """
    stop_test = time.time()
    display_time = int((stop_test - start_test) * 100)
    if display_time == 0:
        display_time = 1
    sys.stdout.write(" %6d\n" % display_time)

# Utility function
def report_error(message, test, mode, start_test):
    """ Print an error message to stdout (screen)
    
    message[in]         Error message to print
    test[in]            The name of the current test
    mode[in]            Event mode (PASS, FAIL, WARN, etc)
    start_test[in]      The starting time of the test
    """
    linelen = opt.width - (len(test_name) + 13)
    sys.stdout.write(' ' * linelen)
    sys.stdout.write("[%s%s%s]" % (BOLD_ON, mode, BOLD_OFF))
    stop_test = time.time()
    print_elapsed_time(start_test)
    print "  ERROR: %s" % (message)
    failed_tests.append(test)

# Begin 'main' code
parser = optparse.OptionParser(version=VERSION, description=DESCRIPTION,
                               usage=USAGE, add_help_option=False)
parser.add_option("--help", action="help")

# Add server option
parser.add_option("--server", action="append", dest="servers",
                  help="connection information for a server to be used " \
                  "in the tests in the form: user:passwd@host:port:socket " \
                  "- list option multiple times for multiple servers to use")

# Add test wildcard option
parser.add_option("--do-test", action="store", dest="wildcard",
                  type = "string", help="execute all tests that begin " \
                         "with this string")

# Add suite list option
parser.add_option("--suite", action="append", dest="suites",
                  type = "string", help="test suite to execute - list "
                  "option multiple times for multiple suites")

# Add skip-test list option
parser.add_option("--skip-test", action="append", dest="skip_tests",
                  type = "string", help="exclude test - list "
                  "option multiple times for multiple suites")

# Add skip-suite list option
parser.add_option("--skip-suite", action="append", dest="skip_suites",
                  type = "string", help="exclude suite - list "
                  "option multiple times for multiple suites")

# Add test directory option
parser.add_option("--testdir", action="store", dest="testdir",
                  type = "string", help="path to test directory",
                  default=TEST_PATH)

# Add starting port
parser.add_option("--start-port", action="store", dest="start_port",
                  type = "string", help="starting port for spawned servers",
                  default=START_PORT)

# Add record option
parser.add_option("--record", action="store_true", dest="record",
                  help="record output of specified test if successful")

# Add record option
parser.add_option("--sorted", action="store_true", dest="sorted",
                  default=True, help="execute tests sorted by suite.name")

# Add utility directory option
parser.add_option("--utildir", action="store", dest="utildir",
                  type = "string", help="path to utility directory",
                  default=UTIL_PATH)

# Add display width option
parser.add_option("--width", action="store", dest="width",
                  type = "int", help="display width",
                  default=PRINT_WIDTH)

# Verbose mode
parser.add_option("--verbose", "-v", action="store_true", dest="verbose",
                  help="display additional information during operation")

# Force mode
parser.add_option("--force", action="store_true", dest="force",
                  help="do not abort when a test fails")

# Now we process the rest of the arguments.
opt, args = parser.parse_args()

# Cannot use --do-test= with listing tests.
if opt.wildcard and len(args) > 0:
    print "ERROR: Cannot mix --do-test= and list of tests."
    exit(1)

# Must use --record with a specific test
if opt.record and len(args) != 1:
    print "ERROR: Must specify a single test when using record."
    exit(1)
    
# Append default paths if options not specified
sys.path.append(opt.testdir)
sys.path.append(opt.utildir)
    
# Process the server connections

# Print preamble
print "\nMySQL Utilities Testing - MUT\n"
print "Parameters used: "
print "  Display Width       = %d" % (opt.width)
print "  Sorted              = %s" % (opt.sorted is not None)
print "  Force               = %s" % (opt.force is not None)
print "  Test directory      = '%s'" % (opt.testdir)
print "  Utilities directory = '%s'" % (opt.utildir)
print "  Starting port       = %d" % int(opt.start_port)

# Check for suite list
if opt.suites:
    sys.stdout.write("  Include only suites = ")
    for suite in opt.suites:
        sys.stdout.write("%s " % (suite))
    print 

# Check to see if we're skipping suites
if opt.skip_suites:
    sys.stdout.write("  Exclude suites      = ")
    for suite in opt.skip_suites:
        sys.stdout.write("%s " % (suite))
    print 
    
# Is there a --do-test?
if opt.wildcard:
    print "  Test wildcard       = '%s%%'" % (opt.wildcard)

# Check to see if we're skipping tests
if opt.skip_tests:
    sys.stdout.write("  Skipping tests      = ")
    for test in opt.skip_tests:
        sys.stdout.write("%s " % (test))
    print
     
server_list = []

# Print status of connections
print "\nServers:"
if not opt.servers:
    print "  None"
else:
    i = 0
    for server in opt.servers:
        conn_val = parse_connection(server)
        if conn_val:
            i += 1   
            # Fail if port and socket are both None
            if conn_val["port"] is None and conn_val["socket"] is None:
                print "ERROR: You must specify either a port or a socket " \
                      "in the server string: \n       %s" % server 
                exit(1)

            sys.stdout.write("  Connecting to %s as user %s on port %s: " % 
                             (conn_val["host"], conn_val["user"],
                              conn_val["port"]))

            if conn_val["port"] is not None:
                conn_val["port"] = int(conn_val["port"])
            else:
                conn_val["port"] = 0
                
            conn = Server(conn_val, "server%d" % i)
            try:
                conn.connect()
                server_list.append(conn)
                print "CONNECTED"
            except:
                print "%sFAILED%s" % (BOLD_ON, BOLD_OFF)
                if conn.connect_error is not None:
                    print conn.connect_error
        else:
            print "ERROR: Problem parsing server connection '%s'" % (server)
            exit(1)
    if len(server_list) == 0:
        print "ERROR: Failed to connect to any servers listed."
        exit(1)

# Print header
print "\n" + "-" * opt.width
print "TEST NAME", ' ' * (opt.width - 24), "STATUS   TIME" 
print "=" * opt.width

test_files = []
failed_tests = []

# Build the list of tests to execute
for root, dirs, files in os.walk(opt.testdir):
    for f in files:
        # Check --suites list. Skip if we have suites and dir is in list
        directory = root[len(opt.testdir)+1:]
        if opt.suites:
            if directory == "":
                if "main" not in opt.suites:
                    continue
            elif directory not in opt.suites:
                continue
        if directory == "":
            directory = "main"
            
        # Get file and extension
        fname, ext = os.path.splitext(f)
        
        # Check for suite.test as well as simply test
        if args and fname not in args and directory + "." + fname not in args:
            continue
        
        # See if test is to be skipped
        if opt.skip_tests:
            if fname in opt.skip_tests or \
               directory + "." + fname in opt.skip_tests:
                continue
            
        # See if suite is to be skipped
        if opt.skip_suites:
            if directory in opt.skip_suites:
                continue
            
        # Include only tests that are .py files and ignore mut library files
        if ext == ".py" and fname != "__init__" and fname != "mutlib":
            test_ref = (directory, root, fname)
            # Do selective tests based on matches for --do-test=
            if opt.wildcard:
                if opt.wildcard == fname[0:len(opt.wildcard)]:
                    test_files.append(test_ref)
            # Add test if no wildcard and suite (dir) is included
            else:
                test_ref = (directory, root, fname)
                test_files.append(test_ref)

# If no tests, there's nothing to do!
if len(test_files) == 0:
    print "No tests match criteria specified."
            
# Sort test cases if option turned on
if opt.sorted:
    test_files.sort()

# Run the tests selected
num_tests_run = 0
for test_tuple in test_files:

    # Get test parts - directory not used
    test = test_tuple[2]
    test_name = ""
    test_suite = test_tuple[1][len(opt.testdir)+1:]

    # Add path to suite
    if len(test_suite) > 0:
        sys.path.append(opt.testdir + "/" + test_suite)
        test_name = test_suite
    else:
        test_name = "main"
    test_name += "." + test
    
    # record start time
    start_test = time.time()
    
    # Create a reference to the test class
    test_class = __import__(test)
    test_case = test_class.test(server_list,
                                opt.testdir + "/" + test_suite,
                                opt.utildir, opt.start_port)
    
    # Print name of the test
    sys.stdout.write(test_name)
    sys.stdout.flush()
    
    # Check prerequisites for number of servers. Skip test is there are not
    # enough servers to connect.
    if not test_case.check_prerequisites():
        report_error("Not enough resources (e.g. servers) to run test.",
                     test_name, "SKIP", start_test)
        continue

    # Set the preconditions for the test
    if not test_case.setup():
        report_error("Cannot establish setup conditions to run test.",
                     test_name, "SKIP", start_test)
        # We call cleanup() to make sure partial setup conditions are
        # removed. Allows for resetting of problems.
        test_case.cleanup()
        continue        
    
    # Run the test
    run_ok = True
    results = None
    if test_case.run():
        # Calculate number of spaces based on test name
        linelen = opt.width - (len(test_name) + 13)
        sys.stdout.write(' ' * linelen)
        
        # Record results of test
        if opt.record:
            sys.stdout.write("RECORD")
            res = test_case.record()
            # Write time here since we're done
            stop_test = time.time()
            print_elapsed_time(start_test)
            if not res:
                sys.stdout.write("  %sWARNING%s: Test record failed." % \
                      (BOLD_ON, BOLD_OFF))

        # Display status of test
        else:
            results = test_case.get_result()
            if results[0]:
                sys.stdout.write("[pass]")
                num_tests_run += 1
            else:
                sys.stdout.write("[%sFAIL%s]" % (BOLD_ON, BOLD_OFF))
                run_ok = False
                failed_tests.append(test)
        if opt.verbose:
            print test_case.__doc__
    else:
        report_error("Test execution failed.", test_name, "FAIL", start_test)
        run_ok = False
                            
    # Cleanup the database settings if needed
    test_cleanup_ok = test_case.cleanup()

    # Display the time if not recording
    if not opt.record and run_ok:
        print_elapsed_time(start_test)

    # Display warning about cleanup
    if not test_cleanup_ok:
        print "  %sWARNING%s: Test cleanup failed." % (BOLD_ON, BOLD_OFF)

    if results is not None and results[1]:
        sys.stdout.write("\n")    
        for str in results[1]:
            sys.stdout.write(str)
        sys.stdout.write("\n")    
    
    # Check force option
    if not run_ok and not opt.force:
        break
        
# Print postamble
print "-" * opt.width
print datetime.datetime.now().strftime("Testing completed: "
                                       "%A %d %B %Y %H:%M:%S\n")
num_fail = len(failed_tests)
num_tests = len(test_files)
if num_fail == 0:
    if num_tests > 0:
        print "All %d tests passed." % (num_tests)
else:
    print "%d of %d tests completed out of %d selected." % \
          (num_tests_run-num_fail, num_tests_run, num_tests)
    print "The following tests failed or were skipped:",
    for test in failed_tests:
        print test,
print "\n"

# Shut down connections here
for server in server_list:
    del server
    
exit(0)