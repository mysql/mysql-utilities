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
This module contains helper methods for formatting output.

METHODS
    format_tabular_list - Format and write row data as a separated-value list or
                          as a grid layout like mysql client query results
                          Writes to a file specified (e.g. sys.stdout)
"""

import csv
import os

def _format_col_separator(file, columns, col_widths, silent=False):
    """Format a row of the header with column separators

    file[in]           file to print to (e.g. sys.stdout)
    columns[in]        list of column names
    col_widths[in]     width of each column
    silent[in]         if True, do not print
    """
    if silent:
        return
    stop = len(columns)
    for i in range(0, stop):
        width = int(col_widths[i]+2)
        file.write('{0}{1:{1}<{2}}'.format("+", "-", width)) 
    file.write("+\n")
    
def _format_row_separator(file, columns, col_widths, row, silent=False):
    """Format a row of data with column separators.

    file[in]           file to print to (e.g. sys.stdout)
    columns[in]        list of column names
    col_widths[in]     width of each column
    rows[in]           data to print
    silent[in]         if True, do not print
    """
    i = 0
    for col in columns:
        if not silent:
            file.write("| ")
        file.write("{0:<{1}} ".format("%s" % row[i], col_widths[i]))
        i += 1
    if not silent:
        file.write("|")
    file.write("\n")

def format_tabular_list(file, columns, rows, print_header=True,
                       separator=None, silent=False,
                       print_footer=True):
    """Format a list in a pretty grid format.
    
    This method will format and write a list of rows in a grid or ?SV list.

    file[in]           file to print to (e.g. sys.stdout)
    columns[in]        list of column names
    rows[in]           list of rows to print
    print_header[in]   if False, do not print header
    separator[in]      if set, use the char specified for a ?SV output
    silent[in]         if True, do not print the grid text (no borders)
    print_footer[in]   if False, do not print footer
    """
    
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
            for i in range(0, stop):
                col_size = len("%s" % row[i]) + 1
                if col_size > col_widths[i]:
                    col_widths[i] = col_size
                    
        # print header
        if print_header:
            _format_col_separator(file, columns, col_widths, silent)
            _format_row_separator(file, columns, col_widths, columns, silent)
        _format_col_separator(file, columns, col_widths, silent)
        for row in rows:
            _format_row_separator(file, columns, col_widths, row, silent)
        if print_footer:
            _format_col_separator(file, columns, col_widths, silent)
    
    
def format_vertical_list(file, columns, rows):
    """Format a list in a vertical format.
    
    This method will format and write a list of rows in a vertical format
    similar to the \G format in the mysql monitor.

    file[in]           file to print to (e.g. sys.stdout)
    columns[in]        list of column names
    rows[in]           list of rows to print
    silent[in]         if True, do not print the grid text (no borders)
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
        print "%d rows." % int(row_num)
                    

