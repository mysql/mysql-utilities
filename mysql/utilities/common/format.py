#
# Copyright (c) 2010, 2013 Oracle and/or its affiliates. All rights reserved.
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
    format_tabular_list - Format and write row data as a separated-value list or
                          as a grid layout like mysql client query results
                          Writes to a file specified (e.g. sys.stdout)
"""

import csv
import os

_MAX_WIDTH = 78
_TWO_COLUMN_DISPLAY = "{0:{1}}  {2:{3}}"

def _format_col_separator(file, columns, col_widths, quiet=False):
    """Format a row of the header with column separators

    file[in]           file to print to (e.g. sys.stdout)
    columns[in]        list of column names
    col_widths[in]     width of each column
    quiet[in]          if True, do not print
    """
    if quiet:
        return
    stop = len(columns)
    for i in range(0, stop):
        width = int(col_widths[i]+2)
        file.write('{0}{1:{1}<{2}}'.format("+", "-", width))
    file.write("+\n")

def _format_row_separator(file, columns, col_widths, row, quiet=False):
    """Format a row of data with column separators.

    file[in]           file to print to (e.g. sys.stdout)
    columns[in]        list of column names
    col_widths[in]     width of each column
    rows[in]           data to print
    quiet[in]          if True, do not print
    """
    i = 0
    if len(columns) == 1 and row != columns:
        row = [row]
    for i, col in enumerate(columns):
        if not quiet:
            file.write("| ")
        file.write("{0:<{1}} ".format("%s" % row[i], col_widths[i]))
    if not quiet:
        file.write("|")
    file.write("\n")

def format_tabular_list(file, columns, rows, options={}):
    """Format a list in a pretty grid format.

    This method will format and write a list of rows in a grid or ?SV list.

    file[in]           file to print to (e.g. sys.stdout)
    columns[in]        list of column names
    rows[in]           list of rows to print
    options[in]        options controlling list:
        print_header   if False, do not print header
        separator      if set, use the char specified for a ?SV output
        quiet          if True, do not print the grid text (no borders)
        print_footer   if False, do not print footer
    """

    print_header = options.get("print_header", True)
    separator = options.get("separator", None)
    quiet = options.get("quiet", False)
    print_footer = options.get("print_footer", True)
    
    # do nothing if no rows.
    if len(rows) == 0:
        return
    if separator is not None:
        if os.name == "posix":
            csv_writer = csv.writer(file, delimiter=separator)
        else:
            csv_writer = csv.writer(file, delimiter=separator,
                                    lineterminator='\n')
        if print_header:
            csv_writer.writerow(columns)
        for row in rows:
            csv_writer.writerow(row)
    else:
        # Calculate column width for each column
        col_widths = []
        for col in columns:
            size = len(col)
            col_widths.append(size+1)

        stop = len(columns)
        for row in rows:
            # if there is one column, just use row.
            if stop == 1:
                col_size = len(row[0]) + 1
                if col_size > col_widths[0]:
                    col_widths[0] = col_size
            else:
                for i in range(0, stop):
                    col_size = len("%s" % row[i]) + 1
                    if col_size > col_widths[i]:
                        col_widths[i] = col_size

        # print header
        if print_header:
            _format_col_separator(file, columns, col_widths, quiet)
            _format_row_separator(file, columns, col_widths, columns, quiet)
        _format_col_separator(file, columns, col_widths, quiet)
        for row in rows:
            _format_row_separator(file, columns, col_widths, row, quiet)
        if print_footer:
            _format_col_separator(file, columns, col_widths, quiet)


def format_vertical_list(file, columns, rows):
    """Format a list in a vertical format.

    This method will format and write a list of rows in a vertical format
    similar to the \G format in the mysql monitor.

    file[in]           file to print to (e.g. sys.stdout)
    columns[in]        list of column names
    rows[in]           list of rows to print
    """

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
        file.write('{0:{0}<{1}}{2:{3}>{4}}. row {0:{0}<{1}}\n'.format("*", 25,
                                                                      row_num,
                                                                      ' ', 8))
        for i in range(0, stop):
            file.write("{0:>{1}}: {2}\n".format(columns[i], max_colwidth,
                                                row[i]))

    if row_num > 0:
        file.write("%d rows.\n" % int(row_num))


def print_list(file, format, columns, rows, no_headers=False, sort=False):
    """Print a list based on format.
    
    Prints a list of rows in the format chosen. Default is GRID.

    file[in]          file to print to (e.g. sys.stdout)
    format[in]        Format (GRID, CSV, TAB, VERTICAL)
    columns[in]       Column headings
    rows[in]          Rows to print
    no_headers[in]    If True, do not print headings (column names)
    sort[in]          If True, sort list before printing
    """

    if sort:
        rows.sort()
    list_options = {
        'print_header' : not no_headers
    }
    if format == "vertical":
        format_vertical_list(file, columns, rows)
    elif format == "tab":
        list_options['separator'] = '\t'
        format_tabular_list(file, columns, rows, list_options)
    elif format == "csv":
        list_options['separator'] = ','
        format_tabular_list(file, columns, rows, list_options)
    else:  # default to table format
        format_tabular_list(file, columns, rows, list_options)


def _get_max_key_dict_list(dictionary_list, key, alias_key=None):
    """Get maximum key length for display calculation
    
    dictionary_list[in]   Dictionary to print
    key[in]               Name of the key
    use_alias[in]         If not None, add alias to width too
    
    Returns int - max width of key
    """
    lcal = lambda x: len(str(x or ''))
    dl = dictionary_list
    tmp = [ (lcal(item[key]), lcal(item.get(alias_key, 0))) for item in dl ]
    return max([ (x[0]+x[1]+3) if x[1] else x[0] for x in tmp])


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
    import textwrap
    
    max_name = _get_max_key_dict_list(dictionary_list, keys[0])
    if max_name < len(column_names[0]):
        max_name = len(column_names[0])
    max_value = (max_width - 2 - max_name) or 25
    if show_header:
        print(_TWO_COLUMN_DISPLAY.format(column_names[0], max_name,
                                         column_names[1], max_value))
        print(_TWO_COLUMN_DISPLAY.format('-'*(max_name), max_name,
                                         '-'*max_value, max_value))
    for item in dictionary_list:
        name = item[keys[0]]
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
