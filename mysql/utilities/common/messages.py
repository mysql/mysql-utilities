#
# Copyright (c) 2013, 2016 Oracle and/or its affiliates. All rights reserved.
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

EXTERNAL_SCRIPT_DOES_NOT_EXIST = ("'{path}' script cannot be found. Please "
                                  "check the path and filename for accuracy "
                                  "and try again.")

ERROR_ANSI_QUOTES_MIX_SQL_MODE = ("One or more servers have SQL mode set to "
                                  "ANSI_QUOTES, the {utility} requires to all "
                                  "or none of the servers to be set with the "
                                  "SQL mode set to ANSI_QUOTES.")

ERROR_USER_WITHOUT_PRIVILEGES = ("User '{user}' on '{host}@{port}' does not "
                                 "have sufficient privileges to "
                                 "{operation} (required: {req_privileges}).")

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
                                "specific object is missing. Please verify "
                                "that both object are correctly specified. "
                                "{detail} Format should be: "
                                "{db1_label}[.{obj1_label}]"
                                ":{db2_label}[.{obj2_label}].")

PARSE_ERR_DB_OBJ_MISSING = ("No object has been specified for "
                            "{db_no_obj_label} '{db_no_obj_value}', while "
                            "object '{only_obj_value}' was specified for "
                            "{db_obj_label} '{db_obj_value}'.")

PARSE_ERR_DB_MISSING_CMP = ("You must specify at least one database to "
                            "compare or use the --all option to compare all "
                            "databases.")

PARSE_ERR_OBJ_NAME_FORMAT = ("Cannot parse the specified qualified name "
                             "'{obj_name}' for {option}. Please verify that a "
                             "valid format is used (i.e., <db_name>"
                             "[.<tbl_name>]) and that backtick quotes are "
                             "properly used if required.")

PARSE_ERR_SPAN_KEY_SIZE_TOO_HIGH = (
    "The value {s_value} specified for option --span-key-size is too big. It "
    "must be smaller or equal than {max} (size of the key hash values for "
    "comparison).")

PARSE_ERR_SPAN_KEY_SIZE_TOO_LOW = (
    "The value {s_value} specified for option --span-key-size is too small "
    "and would cause inaccurate results, please retry with a bigger value "
    "or the default value of {default}.")

PARSE_ERR_OPT_INVALID_CMD = "Invalid {opt} option for '{cmd}'."

PARSE_ERR_OPT_INVALID_CMD_TIP = ("%s Use {opt_tip} instead."
                                 % PARSE_ERR_OPT_INVALID_CMD)

PARSE_ERR_OPT_INVALID_DATE = "Invalid {0} date format (yyyy-mm-dd): {1}"

PARSE_ERR_OPT_INVALID_DATE_TIME = ("Invalid {0} date/time format "
                                   "(yyyy-mm-ddThh:mm:ss): {1}")

PARSE_ERR_OPT_INVALID_NUM_DAYS = ("Invalid number of days (must be an integer "
                                  "greater than zero) for {0} date: {1}")

PARSE_ERR_OPT_INVALID_VALUE = ("The value for option {option} is not valid: "
                               "'{value}'.")

PARSE_ERR_OPT_REQ_NON_NEGATIVE_VALUE = ("Option '{opt}' requires a "
                                        "non-negative value.")

PARSE_ERR_OPT_REQ_GREATER_VALUE = ("Option '{opt}' requires a value greater "
                                   "than {val}.")

PARSE_ERR_OPT_REQ_VALUE = "Option '{opt}' requires a non-empty value."

PARSE_ERR_OPT_REQ_OPT = ("Option {opt} requires the following option(s): "
                         "{opts}.")

PARSE_ERR_OPTS_EXCLD = ("Options {opt1} and {opt2} cannot be used "
                        "together.")

PARSE_ERR_OPTS_REQ = "Option '{opt}' is required."

PARSE_ERR_OPTS_REQ_BY_CMD = ("'{cmd}' requires the following option(s): "
                             "{opts}.")

PARSE_ERR_SLAVE_DISCO_REQ = ("Option --discover-slaves-login or --slaves is "
                             "required.")

PARSE_ERR_OPTS_REQ_GREATER_OR_EQUAL = ("The {opt} option requires a value "
                                       "greater than or equal to {value}.")

WARN_OPT_NOT_REQUIRED = ("WARNING: The {opt} option is not required for "
                         "'{cmd}' (option ignored).")

WARN_OPT_NOT_REQUIRED_ONLY_FOR = ("%s Only used with the {only_cmd} command."
                                  % WARN_OPT_NOT_REQUIRED)

WARN_OPT_NOT_REQUIRED_FOR_TYPE = (
    "# WARNING: The {opt} option is not required for the {type} type "
    "(option ignored).")

WARN_OPT_ONLY_USED_WITH = ("# WARNING: The {opt} option is only used with "
                           "{used_with} (option ignored).")

WARN_OPT_USING_DEFAULT = ("WARNING: Using default value '{default}' for "
                          "option {opt}.")

ERROR_SAME_MASTER = ("The specified new master {n_master_host}:{n_master_port}"
                     " is the same as the "
                     "actual master {master_host}:{master_port}.")

SLAVES = "slaves"

CANDIDATES = "candidates"

ERROR_MASTER_IN_SLAVES = ("The master {master_host}:{master_port} "
                          "and one of the specified {slaves_candidates} "
                          "are the same {slave_host}:{slave_port}.")

SCRIPT_THRESHOLD_WARNING = ("WARNING: You have chosen to use external script "
                            "return code checking. Depending on which script "
                            "fails, this can leave the operation in an "
                            "undefined state. Please check your results "
                            "carefully if the operation aborts.")

HOST_IP_WARNING = ("You may be mixing host names and IP addresses. This may "
                   "result in negative status reporting if your DNS services "
                   "do not support reverse name lookup.")

ERROR_MIN_SERVER_VERSIONS = ("The {utility} requires server versions greater "
                             "or equal than {min_version}. Server version for "
                             "'{host}:{port}' is not supported.")

PARSE_ERR_SSL_REQ_SERVER = ("Options --ssl-ca, --ssl-cert and --ssl-key "
                            "requires use of --server.")

WARN_OPT_SKIP_INNODB = ("The use of InnoDB is mandatory since MySQL 5.7. The "
                        "former options like '--innodb=0/1/OFF/ON' or "
                        "'--skip-innodb' are ignored.")

FILE_DOES_NOT_EXIST = "The following path is invalid, '{path}'."

INSUFFICIENT_FILE_PERMISSIONS = ("You do not have permission to {permissions} "
                                 "file '{path}'.")

MSG_UTILITIES_VERSION = "MySQL Utilities {utility} version {version}."

MSG_MYSQL_VERSION = "Server '{server}' is using MySQL version {version}."

USER_PASSWORD_FORMAT = ("Format of {0} option is incorrect. Use userid:passwd "
                        "or userid.")
