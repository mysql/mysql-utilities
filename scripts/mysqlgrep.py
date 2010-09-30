#!/usr/bin/python

import MySQLdb
import optparse
import re

from mysql.utilities.command import ObjectGrep

parser = optparse.OptionParser(version="0.1",
                               usage="usage: %prog [options] server ...")

parser.add_option("-b", "--body",
                  dest="check_body", action="store_true", default=False,
                  help="Search the body of routines, triggers, and events as well")

# Add some more advanced parsing here to handle types better.
parser.add_option('--type',
                  dest="types", default="routine,event,trigger,table,database",
                  help="""Types to search: a comma-separated list of 'routine', 'event', 'trigger', 'table', and/or 'database'""")
parser.add_option("-G", "--basic-regexp", "--regexp",
                  dest="use_regexp", action="store_true", default=False,
                  help="Use 'REGEXP' operator to match pattern. Default is to use 'LIKE'.")

parser.add_option("-p", "--print-sql", "--sql",
                  dest="print_stmt", action="store_true", default=False,
                  help="Print the statement instead of sending it to the server")
                  
options, args = parser.parse_args()

try:
    pattern = args.pop(0)
except IndexError:
    parser.error("No pattern supplied")

types = re.split(r"\s*,\s*", options.types)
command = ObjectGrep(pattern, types, options.check_body, options.use_regexp)
if options.print_stmt:
    print command.sql()
else:
    command.execute(args)
