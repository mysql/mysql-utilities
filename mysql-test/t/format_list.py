# -*- coding: utf-8 -*-
#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights reserved.
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
format_list test.
"""

import os

import mutlib

from mysql.utilities.common.format import format_tabular_list
from mysql.utilities.common.format import format_vertical_list


class test(mutlib.System_test):
    """Test format module
    In this test, we execute the format_tabular_list and format_vertical_list
    methods in the format module.
    """

    def check_prerequisites(self):
        return self.check_num_servers(0)

    def setup(self):
        return True

    def run(self):
        test_file = open('format_test', 'w')

        rows_1 = [('one',), ('two',), ('three',)]
        cols_1 = ['a']
        rows_2 = [('one', None), ('two', None), ('three', None)]
        cols_2 = ['a', 'b']
        rows_3 = [('one', None, 31), ('two', None, 32), ('three', None, 33)]
        cols_3 = ['a', 'b', 'c']
        rows_4 = [(u'á', u'é', u'í'), (u'á', u'é', u'í'), (u'á', u'é', u'í')]
        cols_4 = [u'á', u'é', u'í']

        format_tabular_list(test_file, cols_1, rows_1)
        format_tabular_list(test_file, cols_2, rows_2)
        format_tabular_list(test_file, cols_3, rows_3)
        format_tabular_list(test_file, cols_4, rows_4)
        # Force usage of csv module
        format_tabular_list(test_file, cols_4, rows_4, {'separator': ','})
        format_vertical_list(test_file, cols_1, rows_1)
        format_vertical_list(test_file, cols_2, rows_2)
        format_vertical_list(test_file, cols_3, rows_3)
        format_vertical_list(test_file, cols_4, rows_4)
        test_file.close()

        test_file = open('format_test', 'r')
        for line in test_file.readlines():
            self.results.append(line)
        test_file.close()
        # Fix result file for Windows removing extra chars at end (CRLF)
        self.replace_result("á,é,í", "á,é,í\n")
        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        try:
            os.unlink('format_test')
        except OSError:
            pass
        return True
