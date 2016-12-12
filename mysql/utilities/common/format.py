#
# Copyright (c) 2010, 2016 Oracle and/or its affiliates. All rights reserved.
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
This module contains helper methods for formatting output.

METHODS
    format_tabular_list - Format and write row data as a separated-value list
                          or as a grid layout like mysql client query results
                          Writes to a file specified (e.g. sys.stdout)
"""

import codecs
import csv
import os
import textwrap

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

from mysql.utilities.common.sql_transform import to_sql


_MAX_WIDTH = 78
_TWO_COLUMN_DISPLAY = "{0:{1}}  {2:{3}}"


class UnicodeWriter(object):
    """A CSV writer which will write rows to CSV file `f_out`,
    which is encoded in the given encoding.
    """

    def __init__(self, f_out, dialect="excel", encoding="utf-8", **kwds):
        """Contructor

        f_out[in]        file to print to (e.g. sys.stdout)
        dialect[in]      description of the dialect in use by the writer
        encoding[in]     encoding
        """
        # Redirect output to a queue
        self.queue = StringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f_out
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        """Write the row parameter to the writer's file object.

        row[in]     sequence of strings or numbers
        """
        self.writer.writerow([val.encode("utf-8") if isinstance(val, unicode)
                              else val for val in row])
        data = self.queue.getvalue()
        data = data.decode("utf-8")  # pylint: disable=R0204
        data = self.encoder.encode(data)
        self.stream.write(data)
        self.queue.truncate(0)

    def writerows(self, rows):
        """Write all rows parameter to the writer's file object.

        rows[in]     list of row objects
        """
        for row in rows:
            self.writerow(row)


def _format_col_separator(f_out, columns, col_widths, quiet=False):
    """Format a row of the header with column separators

    f_out[in]          file to print to (e.g. sys.stdout)
    columns[in]        list of column names
    col_widths[in]     width of each column
    quiet[in]          if True, do not print
    """
    if quiet:
        return
    stop = len(columns)
    for i in range(0, stop):
        width = int(col_widths[i] + 2)
        f_out.write('{0}{1:{1}<{2}}'.format("+", "-", width))
    f_out.write("+\n")


def _format_row_separator(f_out, columns, col_widths, row, quiet=False):
    """Format a row of data with column separators.

    f_out[in]          file to print to (e.g. sys.stdout)
    columns[in]        list of column names
    col_widths[in]     width of each column
    rows[in]           data to print
    quiet[in]          if True, do not print
    """
    i = 0
    if len(columns) == 1 and row != columns:
        row = [row]
    for i, _ in enumerate(columns):
        if not quiet:
            f_out.write("| ")
        val = row[i].encode("utf-8") if isinstance(row[i], unicode) \
            else row[i]
        if isinstance(val, str):
            val = u"{0:<{1}}".format(val.decode("utf-8"), col_widths[i] + 1)
            f_out.write(val.encode("utf-8"))
        else:
            f_out.write("{0:<{1}} ".format("%s" % val, col_widths[i]))

    if not quiet:
        f_out.write("|")
    f_out.write("\n")


def get_col_widths(columns, rows):
    """
    This function gets the maximum column width for a list of rows

    Returns: list - max column widths
    """
    # Calculate column width for each column
    col_widths = []
    for col in columns:
        size = len(col.decode("utf-8") if isinstance(col, str) else col)
        col_widths.append(size + 1)

    stop = len(columns)
    for row in rows:
        row = [val.encode("utf-8") if isinstance(val, unicode)
               else val for val in row]
        # if there is one column, just use row.
        if stop == 1:
            col_size = len(row[0].decode("utf-8")
                           if isinstance(row[0], str) else str(row[0]))
            col_size += 1
            if col_size > col_widths[0]:
                col_widths[0] = col_size
        else:
            for i in range(0, stop):
                col_size = len(row[i].decode("utf-8")
                               if isinstance(row[i], str) else str(row[i]))
                col_size += 1
                if col_size > col_widths[i]:
                    col_widths[i] = col_size
    return col_widths


def format_tabular_list(f_out, columns, rows, options=None):
    """Format a list in a pretty grid format.

    This method will format and write a list of rows in a grid or CSV list.

    f_out[in]          file to print to (e.g. sys.stdout)
    columns[in]        list of column names
    rows[in]           list of rows to print
    options[in]        options controlling list:
        print_header   if False, do not print header
        separator      if set, use the char specified for a CSV output
        quiet          if True, do not print the grid text (no borders)
        print_footer   if False, do not print footer
        none_to_null   if True converts None values to NULL
    """
    if options is None:
        options = {}
    print_header = options.get("print_header", True)
    separator = options.get("separator", None)
    quiet = options.get("quiet", False)
    print_footer = options.get("print_footer", True)
    none_to_null = options.get("none_to_null", False)
    convert_to_sql = options.get('to_sql', False)

    # do nothing if no rows.
    if len(rows) == 0:
        return
    if separator is not None:
        if os.name == "posix":
            # Use \n as line terminator in POSIX (non-Windows) systems.
            csv_writer = UnicodeWriter(f_out, delimiter=separator,
                                       lineterminator='\n')
        else:
            # Use the default line terminator '\r\n' on Windows.
            csv_writer = UnicodeWriter(f_out, delimiter=separator)
        if print_header:
            csv_writer.writerow(columns)
        for row in rows:
            row = [val.encode("utf-8") if isinstance(val, unicode)
                   else val for val in row]
            if convert_to_sql:
                # Convert value to SQL (i.e. add quotes if needed).
                row = ['NULL' if col is None else to_sql(col) for col in row]
            if none_to_null:
                # Convert None values to 'NULL'
                row = ['NULL' if val is None else val for val in row]
            csv_writer.writerow(row)
    else:
        # Calculate column width for each column
        col_widths = options.get('col_widths', None)
        if not col_widths:
            col_widths = get_col_widths(columns, rows)

        # print header
        if print_header:
            _format_col_separator(f_out, columns, col_widths, quiet)
            _format_row_separator(f_out, columns, col_widths, columns, quiet)
        _format_col_separator(f_out, columns, col_widths, quiet)
        for row in rows:
            # Note: lists need to be converted to tuple as expected by
            # next method (to handle single column rows correctly)
            if convert_to_sql:
                # Convert value to SQL (i.e. add quotes if needed).
                row = tuple(('NULL' if col is None else to_sql(col)
                             for col in row))
            if none_to_null:
                # Convert None values to 'NULL'
                row = tuple(('NULL' if val is None else val for val in row))
            _format_row_separator(f_out, columns, col_widths, row, quiet)
        if print_footer:
            _format_col_separator(f_out, columns, col_widths, quiet)


def format_vertical_list(f_out, columns, rows, options=None):
    r"""Format a list in a vertical format.

    This method will format and write a list of rows in a vertical format
    similar to the \G format in the mysql monitor.

    f_out[in]          file to print to (e.g. sys.stdout)
    columns[in]        list of column names
    rows[in]           list of rows to print
    options[in]        options controlling list:
        none_to_null   if True converts None values to NULL
    """
    if options is None:
        options = {}
    none_to_null = options.get("none_to_null", False)

    # do nothing if no rows.
    if len(rows) == 0:
        return

    max_colwidth = 0
    # Calculate maximum column width for all columns
    for col in columns:
        if len(col) + 1 > max_colwidth:
            max_colwidth = len(col) + 1

    stop = len(columns)
    row_num = 0
    for row in rows:
        row_num += 1
        f_out.write('{0:{0}<{1}}{2:{3}>{4}}. row {0:{0}<{1}}\n'.format("*", 25,
                                                                       row_num,
                                                                       ' ', 8))
        if none_to_null:
            # Convert None values to 'NULL'
            row = ['NULL' if not val else val for val in row]
        for i in range(0, stop):
            col = columns[i].decode("utf-8") \
                if isinstance(columns[i], str) else columns[i]
            val = row[i].decode("utf-8") \
                if isinstance(row[i], str) else row[i]
            out = u"{0:>{1}}: {2}\n".format(col, max_colwidth, val)
            f_out.write(out.encode("utf-8"))

    if row_num > 0:
        row_str = 'rows' if row_num > 1 else 'row'
        f_out.write("{0} {1}.\n".format(row_num, row_str))


def print_list(f_out, fmt, columns, rows, no_headers=False, sort=False,
               to_sql=False, col_widths=None):
    """Print a list< based on format.

    Prints a list of rows in the format chosen. Default is GRID.

    f_out[in]         file to print to (e.g. sys.stdout)
    fmt[in]           Format (GRID, CSV, TAB, VERTICAL)
    columns[in]       Column headings
    rows[in]          Rows to print
    no_headers[in]    If True, do not print headings (column names)
    sort[in]          If True, sort list before printing
    to_sql[out]       If True, converts columns to SQL format before
                      printing them to the output.
    col_widths[in]    col widths to use instead of actual col
    """

    if not col_widths:
        col_widths = []
    if sort:
        rows.sort()
    list_options = {
        'print_header': not no_headers,
        'to_sql': to_sql,
        'col_widths': col_widths,
    }
    if fmt == "vertical":
        format_vertical_list(f_out, columns, rows)
    elif fmt == "tab":
        list_options['separator'] = '\t'
        format_tabular_list(f_out, columns, rows, list_options)
    elif fmt == "csv":
        list_options['separator'] = ','
        format_tabular_list(f_out, columns, rows, list_options)
    else:  # default to table format
        format_tabular_list(f_out, columns, rows, list_options)


def _get_max_key_dict_list(dictionary_list, key, alias_key=None):
    """Get maximum key length for display calculation

    dictionary_list[in]   Dictionary to print
    key[in]               Name of the key
    use_alias[in]         If not None, add alias to width too

    Returns int - max width of key
    """
    def lcal(x):
        """ calculate string length """
        return len(str(x or ''))
    dl = dictionary_list
    tmp = [(lcal(item[key]), lcal(item.get(alias_key, 0))) for item in dl]
    return max([(x[0] + x[1] + 3) if x[1] else x[0] for x in tmp])


def print_dictionary_list(column_names, keys, dictionary_list,
                          max_width=_MAX_WIDTH, use_alias=True,
                          show_header=True):
    """Print a multiple-column list with text wrapping

    column_names[in]       Column headings
    keys[in]               Keys for dictionary items
    dictionary_list[in]    Dictionary to print (list of)
    max_width[in]          Max width
    use_alias[in]          If True, use keys[2] to print an alias
    """
    # max column size for the name
    max_name = _get_max_key_dict_list(dictionary_list, keys[0])
    if max_name < len(column_names[0]):
        max_name = len(column_names[0])
    min_value = 25  # min column size for the value
    max_value = max_width - 2 - max_name  # max column size for the value
    if max_value < min_value:
        max_value = min_value
        max_name = max_width - 2 - max_value

    if show_header:
        print(_TWO_COLUMN_DISPLAY.format(column_names[0], max_name,
                                         column_names[1], max_value))
        print(_TWO_COLUMN_DISPLAY.format('-' * (max_name), max_name,
                                         '-' * max_value, max_value))
    for item in dictionary_list:
        name = item[keys[0]]
        if len(name) > max_name:
            name = "{0}...".format(name[:(max_name - 3)])
        value = item[keys[1]]
        if isinstance(value, (bool, int)) or value is None:
            description = [str(value)]
        elif not value:
            description = ['']
        else:
            description = textwrap.wrap(value, max_value)

        if use_alias and len(keys) > 2 and len(item[keys[2]]) > 0:
            name += ' | ' + item[keys[2]]
        print(_TWO_COLUMN_DISPLAY.format(name, max_name,
                                         description[0], max_value))
        for i in range(1, len(description)):
            print(_TWO_COLUMN_DISPLAY.format('', max_name, description[i],
                                             max_value))


def convert_dictionary_list(dict_list):
    """Convert a dictionary to separated lists of keys and values.

    Convert the list of items of the given dictionary (i.e. pairs key, value)
    to a set of columns containing the keys and a set of rows containing the
    values.

    dict_list[in]    Dictionary with a list of items to convert

    Returns tuple - (columns, rows)
    """
    cols = []
    rows = []
    # First, get a list of the columns
    for node in dict_list:
        for key in node.keys():
            if key not in cols:
                cols.append(key)

    # Now form the rows replacing missing columns with None
    for node in dict_list:
        row = []
        for col in cols:
            row.append(node.get(col, None))
        rows.append(row)

    return (cols, rows)
