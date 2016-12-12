#
# Copyright (c) 2013, 2016, Oracle and/or its affiliates. All rights reserved.
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
This file contains a module to read .frm files and attempt to create a
facsimile of the CREATE TABLE command.
"""

import bisect
import os
import stat
import struct
import time

from pprint import pprint
from mysql.utilities.common.charsets import CharsetInfo
from mysql.utilities.exception import UtilError


#
# Definitions and types for interpreting the .frm file values.
#

# Misc. constants
_PORTABLE_SIZEOF_CHAR_PTR = 8
_MY_CHARSET_BIN_NUM = 63
_HA_NOSAME = 1
_DIG2BYTES = [0, 1, 1, 2, 2, 3, 3, 4, 4, 4]
_DIG_PER_DEC1 = 9
_HEADER_LEN = 64
_TABLE_TYPE = 0x01fe   # Magic number for table .frm files
_VIEW_TYPE = 0x5954    # Magic number for view .frm files
_FIELD_NR_MASK = 16383
_HA_USES_COMMENT = 4096

# MySQL data type definitions
_MYSQL_TYPE_DECIMAL = 0
_MYSQL_TYPE_TINY = 1
_MYSQL_TYPE_SHORT = 2
_MYSQL_TYPE_LONG = 3
_MYSQL_TYPE_FLOAT = 4
_MYSQL_TYPE_DOUBLE = 5
_MYSQL_TYPE_NULL = 6
_MYSQL_TYPE_TIMESTAMP = 7
_MYSQL_TYPE_LONGLONG = 8
_MYSQL_TYPE_INT24 = 9
_MYSQL_TYPE_DATE = 10
_MYSQL_TYPE_TIME = 11
_MYSQL_TYPE_DATETIME = 12
_MYSQL_TYPE_YEAR = 13
_MYSQL_TYPE_NEWDATE = 14
_MYSQL_TYPE_VARCHAR = 15
_MYSQL_TYPE_BIT = 16
_MYSQL_TYPE_TIMESTAMP2 = 17
_MYSQL_TYPE_DATETIME2 = 18
_MYSQL_TYPE_TIME2 = 19
_MYSQL_TYPE_NEWDECIMAL = 246
_MYSQL_TYPE_ENUM = 247
_MYSQL_TYPE_SET = 248
_MYSQL_TYPE_TINY_BLOB = 249
_MYSQL_TYPE_MEDIUM_BLOB = 250
_MYSQL_TYPE_LONG_BLOB = 251
_MYSQL_TYPE_BLOB = 252
_MYSQL_TYPE_VAR_STRING = 253
_MYSQL_TYPE_STRING = 254
_MYSQL_TYPE_GEOMETRY = 255

# Mapping of field data types to data type names
_col_types = [
    {'value': _MYSQL_TYPE_DECIMAL, 'text': 'decimal', 'size': None},
    {'value': _MYSQL_TYPE_TINY, 'text': 'tinyint', 'size': 1},
    {'value': _MYSQL_TYPE_SHORT, 'text': 'smallint', 'size': 2},
    {'value': _MYSQL_TYPE_LONG, 'text': 'int', 'size': 4},
    {'value': _MYSQL_TYPE_FLOAT, 'text': 'float', 'size': 4},
    {'value': _MYSQL_TYPE_DOUBLE, 'text': 'double', 'size': 8},
    {'value': _MYSQL_TYPE_NULL, 'text': 'NULL', 'size': 0},
    {'value': _MYSQL_TYPE_TIMESTAMP, 'text': 'timestamp', 'size': 4},
    {'value': _MYSQL_TYPE_LONGLONG, 'text': 'bigint', 'size': 8},
    {'value': _MYSQL_TYPE_INT24, 'text': 'mediumint', 'size': 3},
    {'value': _MYSQL_TYPE_DATE, 'text': 'date', 'size': 4},
    {'value': _MYSQL_TYPE_TIME, 'text': 'time', 'size': 3},
    {'value': _MYSQL_TYPE_DATETIME, 'text': 'datetime', 'size': 8},
    {'value': _MYSQL_TYPE_YEAR, 'text': 'year', 'size': 1},
    {'value': _MYSQL_TYPE_NEWDATE, 'text': 'date', 'size': 3},
    # Size must be calculated
    {'value': _MYSQL_TYPE_VARCHAR, 'text': 'varchar', 'size': -1},
    # Size must be calculated
    {'value': _MYSQL_TYPE_BIT, 'text': 'bit', 'size': -2},
    {'value': _MYSQL_TYPE_TIMESTAMP2, 'text': 'timestamp', 'size': 4},
    {'value': _MYSQL_TYPE_DATETIME2, 'text': 'datetime', 'size': 8},
    {'value': _MYSQL_TYPE_TIME2, 'text': 'time', 'size': 3},
    {'value': _MYSQL_TYPE_NEWDECIMAL, 'text': 'decimal', 'size': None},
    {'value': _MYSQL_TYPE_ENUM, 'text': 'enum', 'size': 0},
    {'value': _MYSQL_TYPE_SET, 'text': 'set', 'size': 0},
    {'value': _MYSQL_TYPE_TINY_BLOB, 'text': 'tinyblob',
     'size': 1 + _PORTABLE_SIZEOF_CHAR_PTR},
    {'value': _MYSQL_TYPE_MEDIUM_BLOB, 'text': 'mediumblob',
     'size': 3 + _PORTABLE_SIZEOF_CHAR_PTR},
    {'value': _MYSQL_TYPE_LONG_BLOB, 'text': 'longblob',
     'size': 4 + _PORTABLE_SIZEOF_CHAR_PTR},
    {'value': _MYSQL_TYPE_BLOB, 'text': 'blob',
     'size': 2 + _PORTABLE_SIZEOF_CHAR_PTR},
    # Size must be calculated
    {'value': _MYSQL_TYPE_VAR_STRING, 'text': 'varchar', 'size': -1},
    {'value': _MYSQL_TYPE_STRING, 'text': 'char', 'size': None},
    {'value': _MYSQL_TYPE_GEOMETRY, 'text': 'geometry',
     'size': 4 + _PORTABLE_SIZEOF_CHAR_PTR},
]

_col_keys = [item['value'] for item in _col_types]

# Database/engine type definitions
_DB_TYPE_UNKNOWN = 0
_DB_TYPE_DIAB_ISAM = 1
_DB_TYPE_HASH = 2
_DB_TYPE_MISAM = 3
_DB_TYPE_PISAM = 4
_DB_TYPE_RMS_ISAM = 5
_DB_TYPE_HEAP = 6
_DB_TYPE_ISAM = 7
_DB_TYPE_MRG_ISAM = 8
_DB_TYPE_MYISAM = 9
_DB_TYPE_MRG_MYISAM = 10
_DB_TYPE_BERKELEY_DB = 11
_DB_TYPE_INNODB = 12
_DB_TYPE_GEMINI = 13
_DB_TYPE_NDBCLUSTER = 14
_DB_TYPE_EXAMPLE_DB = 15
_DB_TYPE_ARCHIVE_DB = 16
_DB_TYPE_CSV_DB = 17
_DB_TYPE_FEDERATED_DB = 18
_DB_TYPE_BLACKHOLE_DB = 19
_DB_TYPE_PARTITION_DB = 20
_DB_TYPE_BINLOG = 21
_DB_TYPE_SOLID = 22
_DB_TYPE_PBXT = 23
_DB_TYPE_TABLE_FUNCTION = 24
_DB_TYPE_MEMCACHE = 25
_DB_TYPE_FALCON = 26
_DB_TYPE_MARIA = 27
_DB_TYPE_PERFORMANCE_SCHEMA = 28
_DB_TYPE_FIRST_DYNAMIC = 42
_DB_TYPE_DEFAULT = 127

# Mapping of engine types to engine names
_engine_types = [
    {'value': _DB_TYPE_UNKNOWN, 'text': 'UNKNOWN'},
    {'value': _DB_TYPE_DIAB_ISAM, 'text': 'ISAM'},
    {'value': _DB_TYPE_HASH, 'text': 'HASH'},
    {'value': _DB_TYPE_MISAM, 'text': 'MISAM'},
    {'value': _DB_TYPE_PISAM, 'text': 'PISAM'},
    {'value': _DB_TYPE_RMS_ISAM, 'text': 'RMS_ISAM'},
    {'value': _DB_TYPE_HEAP, 'text': 'HEAP'},
    {'value': _DB_TYPE_ISAM, 'text': 'ISAM'},
    {'value': _DB_TYPE_MRG_ISAM, 'text': 'MERGE'},
    {'value': _DB_TYPE_MYISAM, 'text': 'MYISAM'},
    {'value': _DB_TYPE_MRG_MYISAM, 'text': 'MERGE'},
    {'value': _DB_TYPE_BERKELEY_DB, 'text': 'BDB'},
    {'value': _DB_TYPE_INNODB, 'text': 'INNODB'},
    {'value': _DB_TYPE_GEMINI, 'text': 'GEMINI'},
    {'value': _DB_TYPE_NDBCLUSTER, 'text': 'NDBCLUSTER'},
    {'value': _DB_TYPE_EXAMPLE_DB, 'text': 'EXAMPLE'},
    {'value': _DB_TYPE_ARCHIVE_DB, 'text': 'ARCHIVE'},
    {'value': _DB_TYPE_CSV_DB, 'text': 'CSV'},
    {'value': _DB_TYPE_FEDERATED_DB, 'text': 'FEDERATED'},
    {'value': _DB_TYPE_BLACKHOLE_DB, 'text': 'BLACKHOLE'},
    {'value': _DB_TYPE_PARTITION_DB, 'text': 'PARTITION'},
    {'value': _DB_TYPE_BINLOG, 'text': 'BINLOG'},
    {'value': _DB_TYPE_SOLID, 'text': 'SOLID'},
    {'value': _DB_TYPE_PBXT, 'text': 'PBXT'},
    {'value': _DB_TYPE_TABLE_FUNCTION, 'text': 'FUNCTION'},
    {'value': _DB_TYPE_MEMCACHE, 'text': 'MEMCACHE'},
    {'value': _DB_TYPE_FALCON, 'text': 'FALCON'},
    {'value': _DB_TYPE_MARIA, 'text': 'MARIA'},
    {'value': _DB_TYPE_PERFORMANCE_SCHEMA, 'text': 'PERFORMANCE_SCHEMA'},
    {'value': _DB_TYPE_FIRST_DYNAMIC, 'text': 'DYNAMIC'},
    {'value': _DB_TYPE_DEFAULT, 'text': 'DEFAULT'},
]
_engine_keys = [item['value'] for item in _engine_types]

# Key algorithms
_KEY_ALG = ['UNDEFINED', 'BTREE', 'RTREE', 'HASH', 'FULLTEXT']

# Format definitions
#                            1         2         3
#                  01234567890123456789012345678901
_HEADER_FORMAT = "<BBBBHHIHHIHHHHHBBIBBBBBIIIIBBBHH"
#                        11122222333333444445556666
#                  12346824602468023489012371590124
#                 ***   111111
#             0123456789012345
_COL_DATA = "<BBBBBBBBBBBBBBBH"
#             0123456789111111
#                       012345

# Various flags copied from server source code - some may not be used but
# may find a use as more esoteric table configurations are tested. These
# are derived from fields.h and all may not apply but are included for
# future expansion/features.
_FIELDFLAG_DECIMAL = 1
_FIELDFLAG_BINARY = 1
_FIELDFLAG_NUMBER = 2
_FIELDFLAG_ZEROFILL = 4
_FIELDFLAG_PACK = 120	              # Bits used for packing
_FIELDFLAG_INTERVAL = 256             # mangled with decimals!
_FIELDFLAG_BITFIELD = 512	          # mangled with decimals!
_FIELDFLAG_BLOB = 1024	              # mangled with decimals!
_FIELDFLAG_GEOM = 2048                # mangled with decimals!
_FIELDFLAG_TREAT_BIT_AS_CHAR = 4096   # use Field_bit_as_char
_FIELDFLAG_LEFT_FULLSCREEN = 8192
_FIELDFLAG_RIGHT_FULLSCREEN = 16384
_FIELDFLAG_FORMAT_NUMBER = 16384      # predit: ###,,## in output
_FIELDFLAG_NO_DEFAULT = 16384         # sql
_FIELDFLAG_SUM = 32768                # predit: +#fieldflag
_FIELDFLAG_MAYBE_NULL = 32768         # sql
_FIELDFLAG_HEX_ESCAPE = 0x10000
_FIELDFLAG_PACK_SHIFT = 3
_FIELDFLAG_DEC_SHIFT = 8
_FIELDFLAG_MAX_DEC = 31
_FIELDFLAG_NUM_SCREEN_TYPE = 0x7F01
_FIELDFLAG_ALFA_SCREEN_TYPE = 0x7800

# Additional flags
_NOT_NULL_FLAG = 1             # Field can't be NULL
_PRI_KEY_FLAG = 2              # Field is part of a primary key
_UNIQUE_KEY_FLAG = 4           # Field is part of a unique key
_MULTIPLE_KEY_FLAG = 8         # Field is part of a key
_BLOB_FLAG = 16                # Field is a blob
_UNSIGNED_FLAG = 32            # Field is unsigned
_HA_PACK_RECORD = 1            # Pack record?
_HA_FULLTEXT = 128             # For full-text search
_HA_SPATIAL = 1024             # For spatial search

# Row type definitions
_ROW_TYPE_DEFAULT, _ROW_TYPE_FIXED, _ROW_TYPE_DYNAMIC, _ROW_TYPE_COMPRESSED, \
    _ROW_TYPE_REDUNDANT, _ROW_TYPE_COMPACT, _ROW_TYPE_PAGE = range(0, 7)

# enum utypes from field.h
_NONE, _DATE, _SHIELD, _NOEMPTY, _CASEUP, _PNR, _BGNR, _PGNR, _YES, _NO, \
    _REL, _CHECK, _EMPTY, _UNKNOWN_FIELD, _CASEDN, _NEXT_NUMBER, \
    _INTERVAL_FIELD, _BIT_FIELD, _TIMESTAMP_OLD_FIELD, _CAPITALIZE, \
    _BLOB_FIELD, _TIMESTAMP_DN_FIELD, _TIMESTAMP_UN_FIELD, \
    _TIMESTAMP_DNUN_FIELD = range(0, 24)

# Array of field data types that can be unsigned
_UNSIGNED_FIELDS = ['TINYINT', 'SMALLINT', 'MEDIUMINT', 'INT', 'INTEGER',
                    'BIGINT', 'REAL', 'DOUBLE', 'FLOAT', 'DECIMAL', 'NUMERIC']

# Array of field data types that can have character set options
_CS_ENABLED = ['CHAR', 'VARCHAR', 'TINYBLOB', 'BLOB', 'MEDIUMBLOB', 'LONGBLOB',
               'ENUM', 'SET']

# Array of index (key) types
_KEY_TYPES = ['PRIMARY', 'UNIQUE', 'MULTIPLE', 'FULLTEXT', 'SPATIAL',
              'FOREIGN_KEY']

# Array of field data types that do not require parens for size
_NO_PARENS = ['TIMESTAMP', 'DATETIME', 'DATE', 'TIME',
              'TINYBLOB', 'BLOB', 'MEDIUMBLOB', 'LONGBLOB',
              'TINYTEXT', 'TEXT', 'MEDIUMTEXT', 'LONGTEXT']

# Array of field data types that are real data
_REAL_TYPES = ['REAL', 'DOUBLE', 'FLOAT', 'DECIMAL', 'NUMERIC']

# Array of blob data types
_BLOB_TYPES = [_MYSQL_TYPE_TINY_BLOB, _MYSQL_TYPE_MEDIUM_BLOB,
               _MYSQL_TYPE_LONG_BLOB, _MYSQL_TYPE_BLOB,
               _MYSQL_TYPE_GEOMETRY]

# Array of data types that do not use keysize for indexes
_NO_KEYSIZE = ['BIT', 'ENUM', 'SET', 'DECIMAL', 'NUMERIC',
               'TIMESTAMP', 'TIME', 'DATETIME']


def _is_decimal(col):
    """Check for decimal data types
    Returns bool - True if column is decimal or numeric.
    """
    return col['field_type_name'].upper() in ['DECIMAL', 'NUMERIC']


def _is_cs_enabled(col):
    """Check for data types that accept character set option
    Returns bool - True if column supports character set option.
    """
    return col['field_type_name'].upper() in _CS_ENABLED


def _is_unsigned(col):
    """Check for unsigned data types
    Returns bool - True if column is an unsigned type.
    """
    return col['field_type_name'].upper() in _UNSIGNED_FIELDS


def _is_real(col):
    """Check for real data types
    Returns bool - True if column is a real type.
    """
    return col['field_type_name'].upper() in _REAL_TYPES


def _is_blob(col):
    """Check for blob data types
    Returns bool - True if column is a blob.
    """
    return col['field_type'] in _BLOB_TYPES


def _is_geometry(flags):
    """Check for geometry field types
    Returns bool - True if geometry type.
    """
    print "flags: %0x" % flags
    return (flags & _FIELDFLAG_GEOM) == _FIELDFLAG_GEOM


def _no_keysize(col):
    """Check for data types that do not use keysize
    Returns bool - True if column is to be exluded from keysize.
    """
    return col['field_type_name'].upper() in _NO_KEYSIZE


def _print_default_values(values):
    """Print default values

    The method prints the default values 2 bytes at a time in hexidecimal
    and ASCII representation (similar to hexdump).

    values[in]         Array of default values
    """
    num_bytes = len(values)
    print "# Default values raw data:"
    i = 0
    while (i < num_bytes):
        def_str = ""
        j = 0
        print "#",
        while (j < 8) and (i < num_bytes):
            print "%02x" % ord(values[i]),
            def_str += values[i]
            i += 1
            j += 1
        print "",
        j = 0
        while (j < 8) and (i < num_bytes):
            print "%02x" % ord(values[i]),
            def_str += values[i]
            i += 1
            j += 1
        print " |",
        print def_str


def _get_pack_length(col):
    """Find the pack length for the field

    col[in]        Column data read for the column to operate

    Returns tuple - (pack_length, field_size)
    """
    size = _col_types[bisect.bisect_left(_col_keys,
                                         col['field_type'])]['size']
    if size == -1:
        col_len = col['bytes_in_col']
        return (1 if int(col_len) < 256 else 2), col_len
    if size == -2:
        col_len = col['bytes_in_col']
        return col_len / 8, col_len
    if size is None:
        return size, col['bytes_in_col']  # It's a string of some sort
    return 0, size


def _get_blob_text(col):
    """Form the correct field name string for blobs and text fields

    col[in]        Column data read for the column to operate

    Returns string - field name string
    """
    type_str = ""
    if col['field_type'] == _MYSQL_TYPE_TINY_BLOB:
        type_str = "tiny"
    elif col['field_type'] == _MYSQL_TYPE_MEDIUM_BLOB:
        type_str = "medium"
    elif col['field_type'] == _MYSQL_TYPE_LONG_BLOB:
        type_str = "long"
    if col['charset'] == _MY_CHARSET_BIN_NUM:
        type_str = "".join([type_str, "blob"])
    else:
        type_str = "".join([type_str, "text"])

    return type_str


def _format_default(col, col_flags, length, decimals):
    """Format a defaut value for printing

    col[in]        Column data dictionary
    col_flags[in]  Flags for column
    length[in]     Length of default value or integer part for floats
    decimals[in]   Number of decimal positions for floats

    Returns string - default clause for CREATE statement.
    """
    default = col['default']
    if isinstance(default, str):
        fmt_str = "'%s'"
    # Check for zerofill:
    elif col_flags & _FIELDFLAG_ZEROFILL:
        if _is_real(col):
            if decimals > 0 and decimals < length:
                if col['field_type_name'].upper() == "DECIMAL":
                    length += 1
                fmt_str = "'" + '%0' + "%s" % length + '.' + \
                          "%s" % decimals + 'f' + "'"
            else:
                fmt_str = "'" + '%0' + "%s" % length + '.' + 'f' + "'"
            if float(default) == 0.0:
                fmt_str = "%s"
                default = "NULL"
        else:
            fmt_str = "'" + '%0' + "%s" % length + 'd' + "'"
    else:
        if _is_real(col):
            if decimals > 0 and decimals < length:
                fmt_str = "'" + '%' + "%s" % (length - 1) + '.' + \
                          "%s" % decimals + 'f' + "'"
            elif decimals == 0:
                fmt_str = "'%d'"
                default = divmod(default, 1)[0]
            else:
                i, decm = divmod(default, 1)
                if decm == 0:
                    fmt_str = "'%d'"
                    default = i
                else:
                    fmt_str = "'%f'"
            if float(default) == 0.0:
                fmt_str = "%s"
                default = "NULL"
        else:
            fmt_str = "'%d'"

    return " DEFAULT " + fmt_str % default


class FrmReader(object):
    """
    This class implements an abstract of the .frm file format. It can be used
    to produce a likeness of the CREATE TABLE command. It is not a 100% match
    because some of the components are missing from the .frm file. For
    example, there are no character set or collation definitions stored so
    unless one has access to the server definitions, these cannot be
    determined.

    The class permits the following operations:

    - show_create_table_statement() - read a .frm file and print its CREATE
      statement. Optionally displays statistics for the .frm file.

    """

    def __init__(self, db_name, table, frm_path, options):
        """Constructor

        db[in]             the database (if known)
        table[in]          table name
        frm_path[in]       full path to .frm file
        options[in]        options for controlling behavior:
            verbosity      print extra data during operations (optional)
                           default value = 0
            quiet          suppress output except CREATE statement
                           default False
            server        path to server for server install
                           default None
            new_engine     substitute engine
                           default None
        """
        self.general_data = None
        self.key_data = None
        self.comment_str = None
        self.engine_str = None
        self.partition_str = None
        self.col_metadata = None
        self.column_data = None
        self.num_cols = 0
        self.default_values = None
        self.frm_file = None
        self.verbosity = options.get('verbosity', 0)
        self.quiet = options.get('quiet', False)
        self.server = options.get('server', None)
        self.new_engine = options.get('new_engine', None)
        self.show_stats = options.get("show_stats", False)
        self.db_name = db_name
        self.table = table
        self.frm_path = frm_path
        self.options = options

        if self.server is None:
            self.csi = None
        else:
            self.csi = CharsetInfo(options)

    def _read_header(self):
        """Read the header information from the file
        """
        try:
            # Skip to header position
            if self.verbosity > 1:
                print "# Skipping to header at : %0000x" % 2
            self.frm_file.seek(2, 0)
            data = self.frm_file.read(_HEADER_LEN)
        except Exception, error:
            if self.verbosity > 1:
                print "EXCEPTION:", error
            raise UtilError("Cannot read header.")

        # Read header
        header = struct.unpack(_HEADER_FORMAT, data)
        engine_name = _engine_types[bisect.bisect_left(_engine_keys,
                                                       header[1])]['text']
        self.general_data = {
            'frm_version': header[0],
            'legacy_db_type': engine_name,
            'IO_SIZE': header[4],
            'length': header[6],
            'tmp_key_length': header[7],
            'rec_length': header[8],
            'max_rows': header[10],
            'min_rows': header[11],
            'db_create_pack': header[12] >> 8,  # only want 1 byte
            'key_info_length': header[13],
            'create_options': header[14],
            'frm_file_ver': header[16],
            'avg_row_length': header[17],
            'default_charset': header[18],
            'row_type': header[20],
            'charset_low': header[21],
            'table_charset': (header[21] << 8) + header[18],
            'key_length': header[24],
            'MYSQL_VERSION_ID': header[25],
            'extra_size': header[26],
            'default_part_eng': header[29],
            'key_block_size': header[30],
        }
        # Fix storage engine string if partitioning engine specified
        if self.general_data['default_part_eng'] > 0 and \
           self.new_engine is None:
            self.engine_str = _engine_types[bisect.bisect_left(
                _engine_keys, header[29])]['text']

        return True

    def _read_keys(self):
        """Read key fields from the file
        """
        offset = self.general_data['IO_SIZE']
        try:
            # Skip ahead to key section
            if self.verbosity > 1:
                print "# Skipping to key data at : %0000x" % int(offset)
            self.frm_file.seek(offset, 0)
        except Exception, error:
            if self.verbosity > 1:
                print "EXCEPTION:", error
            raise UtilError("Cannot locate keys.")

        # Decipher key parts
        num_keys = struct.unpack("<B", self.frm_file.read(1))[0]
        if num_keys & 0x80:
            next_byte = struct.unpack("<B", self.frm_file.read(1))[0]
            num_keys = (next_byte << 7) | (num_keys & 0x7f)
            low = struct.unpack("<B", self.frm_file.read(1))[0]
            high = struct.unpack("<B", self.frm_file.read(1))[0]
            num_key_parts = low + (high << 8)
            self.frm_file.read(2)
        else:
            num_key_parts = struct.unpack("<B", self.frm_file.read(1))[0],
            self.frm_file.read(4)

        self.key_data = {
            'num_keys': num_keys,
            'num_key_parts': num_key_parts,
            'key_names': [],
            'keys': [],
        }

        for i in range(0, self.key_data['num_keys']):
            key_info = {
                'flags': struct.unpack("<H", self.frm_file.read(2))[0],
                'key_length': struct.unpack("<H", self.frm_file.read(2))[0],
                'num_parts': struct.unpack("<B", self.frm_file.read(1))[0],
                'algorithm': struct.unpack("<B", self.frm_file.read(1))[0],
                'block_size': struct.unpack("<H", self.frm_file.read(2))[0],
                'key_parts': [],
                'comment': "",
            }
            for j in range(0, key_info['num_parts']):
                if self.verbosity > 1:
                    print "# Reading key part %s." % j
                key_part_info = {
                    'field_num': struct.unpack(
                        "<H", self.frm_file.read(2))[0] & _FIELD_NR_MASK,
                    'offset': struct.unpack("<H",
                                            self.frm_file.read(2))[0] - 1,
                    'key_type': struct.unpack("<H",
                                              self.frm_file.read(2))[0],
                    'key_part_flag': struct.unpack("<B",
                                                   self.frm_file.read(1))[0],
                    'length': struct.unpack("<H",
                                            self.frm_file.read(2))[0],
                }
                key_info['key_parts'].append(key_part_info)
            self.key_data['keys'].append(key_info)

        terminator = struct.unpack("c", self.frm_file.read(1))[0]
        for i in range(0, self.key_data['num_keys']):
            key_name = ""
            # Read until the next 0xff
            char_read = ""
            while char_read != terminator:
                char_read = struct.unpack("c", self.frm_file.read(1))[0]
                if char_read != terminator:
                    key_name += str(char_read)
            self.key_data['key_names'].append(key_name)

        # Now find the key comments!
        self.frm_file.read(1)
        for i in range(0, self.key_data['num_keys']):
            if (self.key_data['keys'][i]['flags'] & _HA_USES_COMMENT) == \
               _HA_USES_COMMENT:
                k_len = struct.unpack("<H", self.frm_file.read(2))[0]
                com_str = struct.unpack("c" * k_len, self.frm_file.read(k_len))
                self.key_data['keys'][i]['comment'] = "".join(com_str)

        return True

    def _read_comment(self):
        """Read the table comments.
        """
        # Fields can be found 1 IO_SIZE more than what has been read to date
        # plus 46 bytes.
        io_size = self.general_data['IO_SIZE']
        record_offset = io_size + self.general_data['tmp_key_length'] + \
            self.general_data['rec_length']
        offset = (((record_offset / io_size) + 1) * io_size) + 46
        try:
            # Skip to column position
            if self.verbosity > 1:
                print "# Skipping to table comments at : %0000x" % int(offset)
            self.frm_file.seek(offset, 0)
            data = self.frm_file.read(1)
        except Exception, error:
            if self.verbosity > 1:
                print "EXCEPTION:", error
            raise UtilError("Cannot read table comment.")

        comment_len = struct.unpack("<B", data)[0]
        com_chars = struct.unpack("c" * comment_len,
                                  self.frm_file.read(comment_len))
        self.comment_str = "".join(com_chars)
        return True

    def _read_default_values(self):
        """Read the default values for all columns
        """
        offset = self.general_data['IO_SIZE'] + \
            self.general_data['tmp_key_length']
        try:
            # Skip ahead to key section
            if self.verbosity > 1:
                print "# Skipping to default data at : %0000x" % \
                    int(offset + 1)
            self.frm_file.seek(offset + 1, 0)
        except Exception, error:
            if self.verbosity > 1:
                print "EXCEPTION:", error
            raise UtilError("Cannot find default data.")

        num_bytes = self.general_data['rec_length']
        # allow overflow
        self.default_values = self.frm_file.read(num_bytes + 100)

    def _read_engine_data(self):
        """Read the storage engine data.
        """
        # We must calculate the location of the partition information by
        # locating the storage engine name and if it is 'partition' then read
        # the partition string following that.

        offset = self.general_data['IO_SIZE'] + \
            self.general_data['tmp_key_length'] + \
            self.general_data['rec_length']
        try:
            # Skip ahead to key section
            if self.verbosity > 1:
                print "# Skipping to keys at : %0000x" % int(offset + 2)
            self.frm_file.seek(offset + 2, 0)
        except Exception, error:
            if self.verbosity > 1:
                print "EXCEPTION:", error
            raise UtilError("Cannot find engine data.")

        engine_len = struct.unpack("<H", self.frm_file.read(2))[0]

        engine_str = "".join(struct.unpack("c" * engine_len,
                                           self.frm_file.read(engine_len)))

        # Save engine name unless user specified a new engine to use
        if self.engine_str is None:
            if self.new_engine is None:
                self.engine_str = engine_str
            else:
                self.engine_str = self.new_engine

        part_len = struct.unpack("<I", self.frm_file.read(4))[0]
        part_str = "".join(struct.unpack("c" * part_len,
                                         self.frm_file.read(part_len)))
        self.partition_str = " ".join(part_str.split('\n'))

        return True

    def _read_column_names(self, fields_per_screen):
        """Read the table column names.
        """
        # Column names start in 00002152.
        screens_read = 1

        cols = []
        col_in_screen = 0
        for i in range(0, self.num_cols):
            if (col_in_screen == fields_per_screen):
                screens_read += 1
                col_in_screen = 1
                # Do the skips
                self.frm_file.read(8)  # read ahead 8 bytes
                val = '\x20'
                while val == '\x20':  # skip the spaces
                    val = self.frm_file.read(1)
                self.frm_file.read(2)  # read past 2 more bytes
            else:
                col_in_screen += 1
            # get length byte
            col_len = struct.unpack("<B", self.frm_file.read(1))[0]
            col_str = ""
            # Don't copy trailing \x00
            j = 0
            while j < col_len - 1:
                char_found = struct.unpack("c", self.frm_file.read(1))[0]
                col_str += char_found
                j += 1
            # skip trailing \x00 and extra bits except for last col read
            if (i < self.num_cols - 1):
                self.frm_file.read(3)
            cols.append(col_str)
        return (screens_read, cols)

    def _get_decimal_value(self, recpos, col):
        """Get a decimal value from the default column data

        recpos[in]     Position in default row to find data
        col[in]        Column dictionary for the column data

        Returns float - default value retrieved
        """
        # Guard
        if not _is_decimal(col):
            return None
        col_flags = (int(col['flags_extra'] << 8) + col['flags'])
        length = col['bytes_in_col']
        decimals = (col_flags >> _FIELDFLAG_DEC_SHIFT) & _FIELDFLAG_MAX_DEC
        length = length - (1 if decimals else 0) - \
            (1 if (col_flags & _FIELDFLAG_DECIMAL) or (length == 0) else 0)

        # algorithm from bin2decimal()
        # int intg=precision-scale,
        #    intg0=intg/DIG_PER_DEC1, frac0=scale/DIG_PER_DEC1,
        #    intg0x=intg-intg0*DIG_PER_DEC1, frac0x=scale-frac0*DIG_PER_DEC1;
        #
        # return intg0*sizeof(dec1)+dig2bytes[intg0x]+
        #       frac0*sizeof(dec1)+dig2bytes[frac0x];

        intg = length - decimals
        intg0 = intg / _DIG_PER_DEC1
        frac0 = decimals / _DIG_PER_DEC1
        intg0x = intg - (intg0 * _DIG_PER_DEC1)
        frac0x = decimals - (frac0 * _DIG_PER_DEC1)
        int_len = (intg0 * 4 + _DIG2BYTES[intg0x]) - 1  # len of integer part
        frac_len = (frac0 * 4 + _DIG2BYTES[frac0x])   # len of fractional part
        int_val = 0
        shift_num = int_len - 1
        for i in range(0, int_len):
            int_val += ord(self.default_values[recpos + i + 1]) << \
                (shift_num * 8)
            shift_num -= 1
        frac_val = 0
        shift_num = frac_len - 1
        for i in range(0, frac_len):
            frac_val += ord(self.default_values[recpos + int_len + i + 1]) << \
                (shift_num * 8)
            shift_num -= 1
        return float("%s.%s" % (int_val, frac_val))

    def _get_field_defaults(self):
        """Retrieve the default values for the columns.
        """
        max_len = len(self.default_values)
        if self.verbosity > 2:
            _print_default_values(self.default_values)
        for i in range(0, len(self.column_data)):
            col = self.column_data[i]
            recpos = self.column_data[i]['recpos']
            recpos -= 2
            if recpos < 0:
                recpos = 0
            if recpos > max_len:  # safety net
                continue

            # Read default for decimal types
            if _is_decimal(col):
                col['default'] = self._get_decimal_value(recpos, col)
                continue
            len_pos, size = _get_pack_length(col)
            field_cs_num = (col['charset_low'] << 8) + col['charset']
            # Adjust size based on character set maximum length per char
            if _is_cs_enabled(col):
                if self.csi:
                    maxlen = self.csi.get_maxlen(field_cs_num)
                else:
                    maxlen = 1
                size = size / maxlen
            if len_pos is None:
                value = self.default_values[recpos:recpos + size]
            else:
                value = self.default_values[recpos:recpos + len_pos + size]

            # Read default for double type
            if col['field_type'] == _MYSQL_TYPE_DOUBLE:
                col['default'] = struct.unpack('d', value)[0]
                continue

            # Read default for float type
            if col['field_type'] == _MYSQL_TYPE_FLOAT:
                col['default'] = struct.unpack('f', value)[0]
                continue

            # Need to check for column type. Some are binary!
            if len_pos is None:  # Some form of string
                col_str = ""
                for col_def in range(0, len(value)):
                    if value[col_def] != '\x20':
                        col_str += value[col_def]
                col['default'] = '' if len(col_str) == 0 else col_str
            elif len_pos == 0:   # packed numeric
                len_pos = size
            if len_pos == 1:
                col['default'] = struct.unpack("<B", value[0:1])[0]
            elif len_pos == 2:
                col['default'] = struct.unpack("<H", value[0:2])[0]
            elif len_pos == 3:
                col['default'] = struct.unpack("<HB", value[0:3])[0]
            elif len_pos == 4:
                col['default'] = struct.unpack("<I", value[0:4])[0]
            elif len_pos == 8:
                col['default'] = struct.unpack("<Q", value[0:8])[0]

    def _read_column_metadata(self):
        """Read the column metadata (size, flags, etc.).

        Returns dictionary - column definition data
        """
        column_data = []
        # Skip ahead
        try:
            for i in range(0, self.num_cols):
                if self.verbosity > 1:
                    print "# Reading column metadata #%s" % i
                data = struct.unpack(_COL_DATA, self.frm_file.read(17))
                data_type = _col_types[bisect.bisect_left(_col_keys,
                                                          data[13])]
                col_def = {
                    'field_length': data[2],  # 1, +3
                    'bytes_in_col': int(data[3]) + (int(data[4]) << 8),
                    'recpos': (int(data[6]) << 8) +
                              (int(data[5])) + (int(data[4]) << 16),
                    'unireg': data[7],  # 1, +8
                    'flags': data[8],  # 1, +9
                    'flags_extra': data[9],  # 1, +10
                    'unireg_type': data[10],  # 1, +11
                    'charset_low': data[11],  # 1, +12
                    'interval_nr': data[12],  # 1, +13
                    'field_type': data[13],  # 1, +14
                    'field_type_name': data_type['text'],
                    'charset': data[14],  # 1, +15
                    'comment_length': data[15],  # 2, +17
                    'enums': [],
                    'comment': "",
                    'default': None,
                }
                column_data.append(col_def)
        except Exception, error:
            if self.verbosity > 1:
                print "EXCEPTION:", error
            raise UtilError("Cannot locate column data")
        return column_data

    def _read_column_data(self):
        """Read the column information from the file.

        This method builds the list of columns including defaults,
        data type, and determines enum and set values.
        """
        # Fields can be found 1 IO_SIZE more than what has been read to date
        # plus 258 bytes.
        io_size = self.general_data['IO_SIZE']
        record_offset = io_size + self.general_data['tmp_key_length'] + \
            self.general_data['rec_length']
        offset = ((((record_offset + self.general_data['key_info_length']) /
                    io_size) + 1) * io_size) + 258
        try:
            # Skip to column position
            if self.verbosity > 1:
                print "# Skipping to column data at : %0000x" % int(offset)
            self.frm_file.seek(offset, 0)
            data = struct.unpack("<HHHHHHHHHHHHH", self.frm_file.read(26))
        except Exception, error:
            if self.verbosity > 1:
                print "EXCEPTION:", error
            raise UtilError("Cannot read column header.")
        self.num_cols = data[0]
        self.col_metadata = {
            'num_cols': data[0],
            'pos': data[1],
            'unknown': data[2],
            'n_length': data[3],
            'interval_count': data[4],
            'interval_parts': data[5],
            'int_length': data[6],
            'com_length': data[8],
            'null_fields': data[12],
        }
        if self.verbosity > 1:
            pprint(self.col_metadata)

        # Skip ahead
        try:
            self.frm_file.read(7)
            fields_per_screen = struct.unpack("<B", self.frm_file.read(1))[0]
            if self.verbosity > 1:
                print "# Fields per screen =", fields_per_screen
            self.frm_file.read(46)
            col_names = self._read_column_names(fields_per_screen)[1]
            self.frm_file.read(1)  # skip 1 byte
            self.column_data = self._read_column_metadata()
        except Exception, error:
            if self.verbosity > 1:
                print "EXCEPTION:", error
            raise UtilError("Cannot read column data.")

        # TODO: Add ability to read defaults by modifying _get_field_defaults
        #       method to correctly read the default values. Currently, it
        #       does not read some non-character values correctly. When fixed,
        #       remove this comment and uncomment the following line.
        # self._get_field_defaults()

        # Skip column names
        col_len = 0
        for colname in col_names:
            col_len += len(colname)
        # Skip to enum section
        self.frm_file.read(len(col_names) + col_len + 2)
        intervals = []
        interval_num = 0
        # pylint: disable=R0101
        for i in range(0, len(col_names)):
            self.column_data[i]['name'] = col_names[i]
            # Here we read enums and match them to interval_nr.
            i_num = self.column_data[i]['interval_nr']
            if int(i_num) > 0:
                if interval_num < i_num:
                    interval_num += 1
                    cols = []
                    char_found = 99
                    col_str = ''
                    while char_found != 0:
                        char_found = struct.unpack("B",
                                                   self.frm_file.read(1))[0]
                        if char_found == 255:
                            if len(col_str):
                                cols.append(col_str)
                                col_str = ''
                        else:
                            col_str += chr(char_found)
                    intervals.append(cols)
                self.column_data[i]['enums'].extend(
                    intervals[interval_num - 1])

        # Now read column comments
        for i in range(0, len(col_names)):
            if self.verbosity > 1:
                print "# Column comment:", \
                    self.column_data[i]['comment_length']
            if self.column_data[i]['comment_length'] > 0:
                col_str = ''
                for j in range(0, self.column_data[i]['comment_length']):
                    if self.verbosity > 3:
                        print "# Reading column data %s." % j
                    char_found = struct.unpack("B", self.frm_file.read(1))[0]
                    col_str += chr(char_found)
                self.column_data[i]['comment'] = col_str

        return True

    def _get_charset_collation(self, col):
        """Get the character set and collation for column

        col[in]        Column data dictionary

        Returns list - option strings for charset and collation if needed
        """
        parts = []
        field_cs_num = (col['charset_low'] << 8) + col['charset']
        table_cs_num = self.general_data['table_charset']
        # If no character set information, add unknown tag to prompt user
        if self.csi is None:
            if field_cs_num is not None and table_cs_num is not None and \
               field_cs_num != 'binary' and table_cs_num != field_cs_num:
                parts.append(" CHARACTER SET <UNKNOWN>")
            return parts
        field_cs_name = self.csi.get_name(field_cs_num)
        table_cs_name = self.csi.get_name(table_cs_num)
        if field_cs_name is not None and table_cs_name is not None and \
           field_cs_name != 'binary' and table_cs_name != field_cs_name:
            parts.append(" CHARACTER SET `%s`" % field_cs_name)

        elif (field_cs_name is None or table_cs_name is None) and \
                not self.quiet:
            print "C",
            print "# WARNING: Cannot get character set name for id =", id
            parts.append(" CHARACTER SET <UNKNOWN>")
        else:
            parts.append("")

        # Get collation
        def_field_col = self.csi.get_default_collation(field_cs_num)
        field_col = self.csi.get_collation(field_cs_num)
        if def_field_col is not None and field_col is not None and \
           def_field_col[1] != field_col:
            parts.append(" COLLATE `%s`" % field_col)
        elif def_field_col is None and not self.quiet:
            print "# WARNING: Cannot get default collation for id =", id
        elif field_col is None and not self.quiet:
            print "# WARNING: Cannot get collation for id =", id
        else:
            parts.append("")

        return parts

    def _get_column_definitions(self):
        """Build the column definitions

        This method constructs the column definitions from the column data
        read from the file.

        Returns list of strings - column definitions
        """

        def _is_no_parens(col):
            """Check for column uses parens for size
            Returns bool - True if column needs parens for size.
            """
            # If the server version is 5.7.5 or before, we add YEAR to the
            # no parenthesis list. Otherwise, we print the length: YEAR(4)
            ver_str = str(self.general_data['MYSQL_VERSION_ID'])
            vers = (int(ver_str[0]), int(ver_str[1:3]), int(ver_str[3:]))
            # Check to see if it is in the list
            try:
                index_year = _NO_PARENS.index('YEAR')
            except ValueError:
                index_year = None
            if not ((vers[0] >= 5) and (vers[1] >= 7) and (vers[2] >= 5)):
                if not index_year:
                    _NO_PARENS.append("YEAR")
            elif index_year:
                _NO_PARENS.pop(_NO_PARENS.index('YEAR'))
            return col['field_type_name'].upper() in _NO_PARENS

        columns = []
        stop = len(self.column_data)
        for i in range(0, stop):
            col = self.column_data[i]
            col_flags = (int(col['flags_extra'] << 8) + col['flags'])
            length = int(col['bytes_in_col'])
            # Here we need to check for charset maxlen and adjust accordingly
            field_cs_num = (col['charset_low'] << 8) + col['charset']
            if self.csi:
                maxlen = self.csi.get_maxlen(field_cs_num)
            else:
                maxlen = 1
            # Only convert the length for character type fields
            if _is_cs_enabled(col):
                length = length / maxlen
            decimals = int((col_flags >> _FIELDFLAG_DEC_SHIFT) &
                           _FIELDFLAG_MAX_DEC)
            col_parts = []
            # name, data type, length
            # If enum or set values, put those in definition
            if col['enums']:
                col_str = "  `%s` %s(" % (col['name'], col['field_type_name'])
                col_str += ",".join(["'%s'" % i for i in col['enums']])
                col_str += ")"
                col_parts.append(col_str)
            elif _is_no_parens(col) and not _is_blob(col):
                col_parts.append("  `%s` %s" %
                                 (col['name'],
                                  col['field_type_name'].lower()))
            # for blobs
            elif _is_blob(col):
                col_parts.append("  `%s` %s" % (col['name'],
                                                _get_blob_text(col)))
            # for real types:
            elif _is_real(col):
                length_str = ""
                if _is_decimal(col):
                    length = length - (1 if decimals else 0) - \
                        (1 if (col_flags & _FIELDFLAG_DECIMAL) or
                         (length == 0) else 0)
                if decimals == _FIELDFLAG_MAX_DEC:
                    if col['field_type_name'].upper() not in \
                       ["FLOAT", "DOUBLE"]:
                        length_str = "(%s)" % length
                else:
                    length_str = "(%s,%s)" % (length, decimals)
                col_parts.append("  `%s` %s%s" %
                                 (col['name'],
                                  col['field_type_name'].lower(),
                                  length_str))
            else:
                col_parts.append(
                    "  `%s` %s(%s)" % (col['name'],
                                       col['field_type_name'].lower(),
                                       length)
                )

            # unsigned
            if col_flags & _FIELDFLAG_DECIMAL == 0 and _is_unsigned(col):
                col_parts.append(" unsigned")

            # zerofill
            if col_flags & _FIELDFLAG_ZEROFILL and _is_unsigned(col):
                col_parts.append(" zerofill")

            # character set and collation options
            if _is_cs_enabled(col):
                col_parts.extend(self._get_charset_collation(col))

            # null
            if col_flags & _FIELDFLAG_MAYBE_NULL:
                if not col['default']:
                    col_parts.append(" DEFAULT NULL")
            elif not _is_blob(col):
                col_parts.append(" NOT NULL")

            # default - Check the _FIELDFLAG_NO_DEFAULT flag. If this flag
            #           is set, there is no default.
            default = col['default']
            if col['field_type'] in [_MYSQL_TYPE_TIMESTAMP,
                                     _MYSQL_TYPE_TIMESTAMP2]:
                col_parts.append(" DEFAULT CURRENT_TIMESTAMP "
                                 "ON UPDATE CURRENT_TIMESTAMP")
            elif col_flags & _FIELDFLAG_NO_DEFAULT == 0 and \
                    default is not None:
                col_parts.append(_format_default(col, col_flags,
                                                 length, decimals))

            # auto increment
            if col['unireg_type'] == _NEXT_NUMBER:
                col_parts.append(" AUTO_INCREMENT")

            if len(col['comment']) > 0:
                col_parts.append(" comment '%s'" % col['comment'])

            # if not the last column or if there are keys, append comma
            if i < stop - 1 or self.key_data['num_keys'] > 0:
                col_parts.append(",")
            col_parts.append(" ")
            columns.append("".join(col_parts))

        return columns

    def _get_key_size(self, col, key_info, flags):
        """Get the key size option for column

        col[in]        Column data dictionary
        key_info[in]   Key information
        flags[in]      Key flags

        Returns string - string of (N) for size or None for no size information
        """
        size_info = None
        if _no_keysize(col) or self.csi is None:
            return size_info
        key_len = int(key_info['length'])
        pack_len = _get_pack_length(col)
        if col['field_type_name'].upper() == "VARCHAR":
            field_len = int(col['field_length'])
        elif (_is_real(col) or _is_unsigned(col) or _is_decimal(col)) and \
                pack_len[0]:
            field_len = int(pack_len[0])
        else:
            field_len = int(pack_len[1])
        field_cs_num = (col['charset_low'] << 8) + col['charset']
        if self.csi:
            maxlen = self.csi.get_maxlen(field_cs_num)
        else:
            maxlen = 1

        # Geometry is an exception
        if col['field_type'] == _MYSQL_TYPE_GEOMETRY:
            if self.csi:
                size_info = "(%d)" % key_len
            else:
                size_info = "(UNKNOWN)"

        elif field_len != key_len and \
                not int(flags) & _HA_FULLTEXT and not int(flags) & _HA_SPATIAL:
            if self.csi:
                size_info = "(%d)" % (key_len / maxlen)
            else:
                size_info = "(UNKNOWN)"
        return size_info

    def _get_key_columns(self):
        """Build the key column definitions

        This method constructs the key definitions from the column data
        read from the file.

        Returns list of strings - key column definitions
        """
        keys = []
        key_info = zip(self.key_data['key_names'], self.key_data['keys'])
        num_keys = len(key_info)
        i = 0
        for key, info in key_info:
            if key == "PRIMARY":
                key_prefix = "PRIMARY KEY"
            elif not info['flags'] & _HA_NOSAME:
                key_prefix = "UNIQUE KEY"
            else:
                key_prefix = "KEY"
            key_str = "%s `%s` (%s)"
            key_cols = ""
            for k in range(0, len(info['key_parts'])):
                key_part = info['key_parts'][k]
                col = self.column_data[key_part['field_num'] - 1]
                key_cols += "`%s`" % col['name']
                size_str = self._get_key_size(col, key_part, info['flags'])
                if size_str:
                    key_cols += size_str
                if k < len(info['key_parts']) - 1:
                    key_cols += ","
            algorithm = _KEY_ALG[info['algorithm']]
            if algorithm != 'UNDEFINED':
                key_str += " USING %s" % algorithm
            if i < num_keys - 1:
                key_str += ","
            keys.append(key_str % (key_prefix, key, key_cols))
            i += 1
        return keys

    def _get_table_options(self):
        """Read the general table options from the file.

        Returns string - options string for CREATE statement
        """
        options = []

        gen = self.general_data   # short name to save indent, space

        options.append(") ENGINE=%s" % self.engine_str)

        if self.partition_str is not None and len(self.partition_str):
            options.append("%s" % self.partition_str)

        if gen['avg_row_length'] > 0:
            options.append("AVG_ROW_LENGTH = %s" % gen['avg_row_length'])

        if gen['key_block_size'] > 0:
            options.append("KEY_BLOCK_SIZE = %s" % gen['key_block_size'])

        if gen['max_rows'] > 0:
            options.append("MAX_ROWS = %s" % gen['max_rows'])

        if gen['min_rows'] > 0:
            options.append("MIN_ROWS = %s" % gen['min_rows'])

        if gen['default_charset'] > 0:
            # If no character set information, add unknown tag to prompt user
            if self.csi:
                c_id = int(gen['default_charset'])
                cs_name = self.csi.get_name(c_id)
                if cs_name is not None:
                    options.append("DEFAULT CHARSET=%s" % cs_name)
                elif not self.quiet:
                    print "# WARNING: Cannot find character set by id =", c_id

                # collation
                def_col = self.csi.get_default_collation(c_id)
                col = self.csi.get_collation(c_id)
                if def_col is not None and col is not None and def_col != col:
                    options.append("COLLATE=`%s`" % col)
                elif def_col is None and not self.quiet:
                    print "# WARNING: Cannot find default collation " + \
                          "for table using id =", c_id
                elif col is None and not self.quiet:
                    print "# WARNING: Cannot find collation for table " + \
                        "using id =", c_id

        row_format = ""
        row_type = int(gen['row_type'])
        if row_type == _ROW_TYPE_FIXED:
            row_format = "FIXED"
        elif row_type == _ROW_TYPE_DYNAMIC:
            row_format = "DYNAMIC"
        elif row_type == _ROW_TYPE_COMPRESSED:
            row_format = "COMPRESSED"
        elif row_type == _ROW_TYPE_REDUNDANT:
            row_format = "REDUNDANT"
        elif row_type == _ROW_TYPE_COMPACT:
            row_format = "COMPACT"
        if len(row_format) > 0:
            options.append("ROW_FORMAT = %s" % row_type)

        if self.comment_str is not None and len(self.comment_str):
            options.append("COMMENT '%s'" % self.comment_str)

        if len(options) > 1:
            return options[0] + " " + ", ".join(options[1:]) + ";"
        return options[0] + ";"

    def _build_create_statement(self):
        """Build the create statement for the .frm file.

        This method builds the CREATE TABLE information as read from
        the file.

        Returns string - CREATE TABLE string
        """
        if self.general_data is None:
            raise UtilError("Header information missing.")

        # CREATE statement preamble
        parts = []

        # Create preamble
        preamble = "CREATE TABLE %s`%s` ("
        if self.db_name is not None and len(self.db_name) > 1:
            db_str = "`%s`." % self.db_name
        else:
            db_str = ""
        parts.append(preamble % (db_str, self.table))

        # Get columns
        parts.extend(self._get_column_definitions())

        # Get indexes
        parts.extend(self._get_key_columns())

        # Create postamble and table options
        parts.append(self._get_table_options())

        return "\n".join(parts)

    def get_type(self):
        """Return the file type - TABLE or VIEW
        """
        # Fail if we cannot read the file
        try:
            self.frm_file = open(self.frm_path, "rb")
        except Exception, error:
            raise UtilError("The file %s cannot be read.\n%s" %
                            (self.frm_path, error))

        # Read the file type
        file_type = struct.unpack("<H", self.frm_file.read(2))[0]

        # Close file and exit
        self.frm_file.close()

        # Take action based on file type
        if file_type == _TABLE_TYPE:
            return "TABLE"
        elif file_type == _VIEW_TYPE:
            return "VIEW"
        else:
            return "UNKNOWN"

    def show_statistics(self):
        """Show general file and table statistics
        """

        print "# File Statistics:"
        file_stats = os.stat(self.frm_path)
        file_info = {
            'Size': file_stats[stat.ST_SIZE],
            'Last Modified': time.ctime(file_stats[stat.ST_MTIME]),
            'Last Accessed': time.ctime(file_stats[stat.ST_ATIME]),
            'Creation Time': time.ctime(file_stats[stat.ST_CTIME]),
            'Mode': file_stats[stat.ST_MODE],
        }
        for value, data in file_info.iteritems():
            print "#%22s : %s" % (value, data)
        print

        # Fail if we cannot read the file
        try:
            self.frm_file = open(self.frm_path, "rb")
        except Exception, error:
            raise UtilError("The file %s cannot be read.\n%s" %
                            (self.frm_path, error))

        # Read the file type
        file_type = struct.unpack("<H", self.frm_file.read(2))[0]

        # Take action based on file type
        if file_type != _TABLE_TYPE:
            return

        # Read general information
        self._read_header()

        # Close file and exit
        self.frm_file.close()

        version = str(self.general_data['MYSQL_VERSION_ID'])
        ver_str = "%d.%d.%d" % (int(version[0]), int(version[1:3]),
                                int(version[3:]))
        def_part_eng = 'None'
        if self.general_data['default_part_eng'] > 0:
            def_part_eng = _engine_types[bisect.bisect_left(
                _engine_keys,
                self.general_data['default_part_eng'])]['text']
        print "# Table Statistics:"
        table_info = {
            'MySQL Version': ver_str,
            'frm Version': self.general_data['frm_version'],
            'Engine': self.general_data['legacy_db_type'],
            'IO_SIZE': self.general_data['IO_SIZE'],
            'frm File_Version': self.general_data['frm_file_ver'],
            'Def Partition Engine': def_part_eng,
        }
        for value, data in table_info.iteritems():
            print "#%22s : %s" % (value, data)
        print

    def show_create_table_statement(self):
        """Show the CREATE TABLE statement

        This method reads the .frm file specified in the constructor and
        builds a fascimile CREATE TABLE statement if the .frm file describes
        a table. For views, the method displays the CREATE VIEW statement
        contained in the file.
        """
        if not self.quiet:
            print "# Reading .frm file for %s:" % self.frm_path

        # Fail if we cannot read the file
        try:
            self.frm_file = open(self.frm_path, "rb")
        except Exception, error:
            raise UtilError("The file %s cannot be read.\n%s" %
                            (self.frm_path, error))

        # Read the file type
        file_type = struct.unpack("<H", self.frm_file.read(2))[0]

        # Take action based on file type
        if file_type == _TABLE_TYPE:
            if not self.quiet:
                print "# The .frm file is a TABLE."

            # Read general information
            self._read_header()
            if self.verbosity > 1:
                print "# General Data from .frm file:"
                pprint(self.general_data)

            # Read key information
            self._read_keys()
            if self.verbosity > 1:
                print "# Index (key) Data from .frm file:"
                pprint(self.key_data)

            # Read default field values information
            self._read_default_values()

            # Read partition information
            self._read_engine_data()
            if self.verbosity > 1:
                print "# Engine string:", self.engine_str
                print "# Partition string:", self.partition_str

            # Read column information
            self._read_column_data()
            if self.verbosity > 1:
                print "# Column Data from .frm file:"
                pprint(self.column_data)
                print "# Number of columns:", self.num_cols
                pprint(self.column_data[1:])

            # Read comment
            self._read_comment()
            if self.verbosity > 1:
                print "# Comment:", self.comment_str

            if self.csi is not None and self.verbosity > 2:
                print "# Character sets read from server:"
                self.csi.print_charsets()

            create_table_statement = self._build_create_statement()
            if not self.quiet:
                print "# CREATE TABLE Statement:\n"
            print create_table_statement
            print

        elif file_type == _VIEW_TYPE:
            # Skip heading
            self.frm_file.read(8)
            view_data = {}
            for line in self.frm_file.readlines():
                field, value = line.strip('\n').split("=", 1)
                view_data[field] = value
            if self.verbosity > 1:
                pprint(view_data)
            if not self.quiet:
                print "# CREATE VIEW Statement:\n"
            print view_data['query']
            print
        else:
            raise UtilError("Invalid file type. Magic bytes = %02x" %
                            file_type)

        # Close file and exit
        self.frm_file.close()

    def change_storage_engine(self):
        """Change the storage engine in an .frm file to MEMORY

        This method edits a .frm file to change the storage engine to the
        the MEMORY engine.

        CAUTION: Method will change the contents of the file.

        Returns tuple - (original engine type, original engine name,
                         sever version from the file)
        """
        # Here we must change the code in position 0x03 to the engine code
        # and the engine string in body of the file (Calculated location)
        if self.verbosity > 1 and not self.quiet:
            print "# Changing engine for .frm file %s:" % self.frm_path

        # Fail if we cannot read the file
        try:
            self.frm_file = open(self.frm_path, "r+b")
        except Exception, error:
            raise UtilError("The file %s cannot be read.\n%s" %
                            (self.frm_path, error))

        # Read the file type
        file_type = struct.unpack("<H", self.frm_file.read(2))[0]

        # Do nothing if this is a view.
        if file_type == _VIEW_TYPE:
            return None

        # Abort if not table.
        if file_type != _TABLE_TYPE:
            raise UtilError("Invalid file type. Magic bytes = %02x" %
                            file_type)

        # Replace engine value
        self.frm_file.read(1)  # skip 1 byte
        engine_type = struct.unpack("<B", self.frm_file.read(1))[0]

        # Read general information
        self._read_header()
        if self.verbosity > 1:
            print "# General Data from .frm file:"
            pprint(self.general_data)

        engine_str = ""
        server_version = str(self.general_data['MYSQL_VERSION_ID'])

        offset = self.general_data['IO_SIZE'] + \
            self.general_data['tmp_key_length'] + \
            self.general_data['rec_length']

        self.frm_file.seek(offset + 2, 0)

        engine_len = struct.unpack("<H", self.frm_file.read(2))[0]
        engine_str = "".join(struct.unpack("c" * engine_len,
                                           self.frm_file.read(engine_len)))
        if self.verbosity > 1:
            print "# Engine string:", engine_str

        # If this is a CSV storage engine, don't change the engine type
        # and instead create an empty .CSV file
        if engine_type == _DB_TYPE_CSV_DB:
            new_csv = os.path.splitext(self.frm_path)
            f_out = open(new_csv[0] + ".CSV", "w")
            f_out.close()
        elif engine_type == _DB_TYPE_ARCHIVE_DB:
            new_csv = os.path.splitext(self.frm_path)
            f_out = open(new_csv[0] + ".ARZ", "w")
            f_out.close()
        elif engine_type == _DB_TYPE_MRG_MYISAM:
            new_csv = os.path.splitext(self.frm_path)
            f_out = open(new_csv[0] + ".MRG", "w")
            f_out.close()
        elif engine_type == _DB_TYPE_BLACKHOLE_DB:
            pass  # Nothing to do for black hole storage engine
        else:
            # Write memory type
            self.frm_file.seek(3)
            self.frm_file.write(struct.pack("<B", 6))

            # Write memory name
            self.frm_file.seek(offset + 2, 0)
            self.frm_file.write(struct.pack("<H", 6))
            self.frm_file.write("MEMORY")

        # Close file and exit
        self.frm_file.close()

        return engine_type, engine_str, server_version
