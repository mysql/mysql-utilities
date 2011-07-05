#!/usr/bin/env python

import mutlib
import os
import sys

class test(mutlib.System_test):
    """Test format module
    In this test, we execute the format_tabular_list and format_vertical_list
    methods in the format module.
    """

    def check_prerequisites(self):
        return self.check_num_servers(0)

    def setup(self):
        self.test_file = open('format_test', 'w')
        return True

    def run(self):

        from mysql.utilities.common.format import format_tabular_list
        from mysql.utilities.common.format import format_vertical_list

        rows_1 = [('one',),('two',),('three',)]
        cols_1 = ['a']
        rows_2 = [('one',None),('two',None),('three',None)]
        cols_2 = ['a','b']
        rows_3 = [('one',None,31),('two',None,32),('three',None,33)]
        cols_3 = ['a','b','c']

        format_tabular_list(self.test_file, cols_1, rows_1)
        format_tabular_list(self.test_file, cols_2, rows_2)
        format_tabular_list(self.test_file, cols_3, rows_3)
        format_vertical_list(self.test_file, cols_1, rows_1)
        format_vertical_list(self.test_file, cols_2, rows_2)
        format_vertical_list(self.test_file, cols_3, rows_3)
        self.test_file.close()

        self.test_file = open('format_test', 'r')
        for line in self.test_file.readlines():
            self.results.append(line)
        self.test_file.close()

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        os.unlink('format_test')
        return True
