#
# Copyright (c) 2013 Oracle and/or its affiliates. All rights reserved.
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
This file contains output string messages used by MySQL Utilities.
"""


PARSE_ERR_DB_PAIR = ("Cannot parse the specified database(s): '{db_pair}'. "
                     "Please verify that the database(s) are specified in "
                     "a valid format (i.e., {db1_label}[:{db2_label}]) and "
                     "that backtick quotes are properly used when required.")

PARSE_ERR_DB_PAIR_EXT = ("%s The use of backticks is required if non "
                         "alphanumeric characters are used for database "
                         "names. Parsing the specified database results "
                         "in {db1_label} = '{db1_value}' and "
                         "{db2_label} = '{db2_value}'." % PARSE_ERR_DB_PAIR)

PARSE_ERR_DB_OBJ_PAIR = ("Cannot parse the specified database objects: "
                           "'{db_obj_pair}'. Please verify that the objects "
                           "are specified in a valid format (i.e., {db1_label}"
                           "[.{obj1_label}]:{db2_label}[.{obj2_label}]) and "
                           "that backtick quotes are properly used if "
                           "required.")

PARSE_ERR_DB_OBJ_PAIR_EXT = ("%s The use of backticks is required if non "
                             "alphanumeric characters are used for identifier "
                             "names. Parsing the specified objects results "
                             "in: {db1_label} = '{db1_value}', "
                             "{obj1_label} = '{obj1_value}', "
                             "{db2_label} = '{db2_value}' and "
                             "{obj2_label} = '{obj2_value}'."
                             % PARSE_ERR_DB_OBJ_PAIR)

PARSE_ERR_DB_OBJ_MISSING_MSG = ("Incorrect object compare argument, one "
                              "specific object is missing. Please verify that "
                              "both object are correctly specified. {detail} "
                              "Format should be: {db1_label}[.{obj1_label}]"
                              ":{db2_label}[.{obj2_label}].")

PARSE_ERR_DB_OBJ_MISSING = ("No object has been specified for "
                            "{db_no_obj_label} '{db_no_obj_value}', while "
                            "object '{only_obj_value}' was specified for "
                            "{db_obj_label} '{db_obj_value}'.")
