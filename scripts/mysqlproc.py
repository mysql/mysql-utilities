#!/usr/bin/python

import optparse
import getpass

import mysql.command

# The structure of all the scripts are such that the main processing
# is done in the commands class, while the "view" part, representing
# the external interface to the world, is handled in the script.
#
# - Parsing options
# - Formatting output

# Parse options
parser = optparse.OptionParser(version="0.1", add_help_option=False)

parser.add_option("-h", "--host", dest="host", default="localhost",
                  help="Connect to the MySQL server on the given host.")
parser.add_option("-u", "--user", dest="user", default=getpass.getuser(),
                  help="The MySQL user name to use when connecting to the server.")
parser.add_option("-S", "--socket", dest="socket",
                  help="For connections to localhost, the Unix socket file to use.")
parser.add_option("-p", "--password", dest="password", default="",
                  help="The password to use when connecting to the server.")
parser.add_option("-P", "--port", dest="port", type="int", default=3306,
                  help="The TCP/IP port number to use for the connection.")
parser.add_option("--help", action="help")
# We could probably switch to use a callback and append the compiled
# regexps instead, but we leave this for later.
parser.add_option("--match-user", dest="match_user", metavar="PATTERN",
                  help="Match the User column of the PROCESSLIST table")
parser.add_option("--match-host", dest="match_host", metavar="PATTERN",
                  help="Match the Host column of the PROCESSLIST table")
parser.add_option("--match-db", dest="match_db", metavar="PATTERN",
                  help="Match the Db column of the PROCESSLIST table")
parser.add_option("--match-command", dest="match_command", metavar="PATTERN",
                  help="Match the Command column of the PROCESSLIST table")
parser.add_option("--match-info", dest="match_info", metavar="PATTERN",
                  help="Match the Info column of the PROCESSLIST table")
parser.add_option("--match-state", dest="match_state", metavar="PATTERN",
                  help="Match the State column of the PROCESSLIST table")
parser.add_option("--match-time", dest="match_time", metavar="PERIOD",
                  help="Match the Time column of the PROCESSLIST table")
parser.add_option("-v", "--verbose", action="count", dest="verbosity",
                  default=0,
                  help="Print debugging messages about progress to STDOUT. Multiple -v options increase the verbosity.")
parser.add_option("--kill", action="append_const",
                  const=mysql.command.KILL_CONNECTION,
                  dest="action_list",
                  help="Kill all matching connections.")
parser.add_option("--kill-query", action="append_const",
                  const=mysql.command.KILL_QUERY,
                  dest="action_list",
                  help="Kill query for all matching processes.")
parser.add_option("--print", action="append_const",
                  const=mysql.command.PRINT_PROCESS,
                  dest="action_list",
                  help="Print all matching processes.")
(options, args) = parser.parse_args()

# Construct execution object
command = mysql.command.ProcessListProcessor(options)
# Execute command
command.execute(args)

