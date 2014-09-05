#
# Copyright (c) 2014, Oracle and/or its affiliates. All rights reserved.
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
This files contains unit tests for mysql.utilities.common.binary_log module.
"""

import os
import shutil
import tempfile
import time
import unittest

from mysql.utilities.common.binary_log_file import (
    filter_binary_logs_by_date, filter_binary_logs_by_sequence, get_index_file,
    is_binary_log_filename, LOG_TYPE_ALL, LOG_TYPE_BIN, LOG_TYPE_RELAY,
    LOG_TYPES, move_binary_log
)
from mysql.utilities.exception import UtilError


class TestBinaryLogFile(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create a temporary directories for 'test_move_binary_log'.
        cls.tmp_source = tempfile.mkdtemp()
        cls.tmp_destination = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        # Remove temporary directories created for 'test_move_binary_log'.
        shutil.rmtree(cls.tmp_source)
        shutil.rmtree(cls.tmp_destination)

    def test_is_binary_log_filename(self):
        # Check valid default binlog filenames.
        binlogs = ('foo-bin.000001', 'mysql-bin.999999')
        for filename in binlogs:
            self.assertTrue(
                is_binary_log_filename(filename, log_type=LOG_TYPE_BIN)
            )

        # Check valid default relay log filenames.
        relay_logs = ('foo-relay-bin.000001', 'mysql-relay-bin.999999')
        for filename in relay_logs:
            self.assertTrue(
                is_binary_log_filename(filename, log_type=LOG_TYPE_RELAY)
            )

        # Check valid default binary log (binlog and relay log) filenames.
        binary_logs = binlogs + relay_logs
        for filename in binary_logs:
            self.assertTrue(
                is_binary_log_filename(filename, log_type=LOG_TYPE_ALL)
            )

        # Check valid binary logs with a specific basename.
        basename = 'my-custom_filename'
        filename = '{0}.004321'.format(basename)
        for log_type in LOG_TYPES:
            self.assertTrue(
                is_binary_log_filename(filename, log_type=log_type,
                                       basename=basename)
            )

        # Check invalid default binlog filenames.
        not_binlogs = ('bin-foo.000001', 'foo_bin.000001', 'foo.bin.',
                       'mysql-bin.log')
        not_binlogs = not_binlogs + relay_logs
        for filename in not_binlogs:
            self.assertFalse(
                is_binary_log_filename(filename, log_type=LOG_TYPE_BIN)
            )

        # Check invalid default relay log filenames.
        not_relay_logs = ('relay-bin-foo.000001', 'foo_relay-bin.000001',
                          'foo.relay-bin', 'mysql-relay-bin.log')
        not_relay_logs = not_relay_logs + binlogs
        for filename in not_relay_logs:
            self.assertFalse(
                is_binary_log_filename(filename, log_type=LOG_TYPE_RELAY)
            )

        # Check invalid default binary log (binlog and relay log) filenames.
        not_binary_logs = ('bin-foo.000001', 'foo_bin.000001', 'foo.bin.',
                           'mysql-bin.log', 'relay-bin-foo.000001',
                           'foo_relay_bin.000001', 'foo.relay-bin',
                           'mysql-relay-bin.log')
        for filename in not_binary_logs:
            self.assertFalse(
                is_binary_log_filename(filename, log_type=LOG_TYPE_ALL)
            )

        # Check invalid binary logs with a specific basename.
        basename = 'my-custom_filename'
        not_custom_logs = ('{0}.log'.format(basename),) + binlogs + relay_logs
        for log_type in LOG_TYPES:
            for filename in not_custom_logs:
                self.assertFalse(
                    is_binary_log_filename(filename, log_type=log_type,
                                           basename=basename)
                )

        # Check invalid log type.
        self.assertRaises(UtilError, is_binary_log_filename,
                          'mysql-bin.0000001', log_type='invalid-type')

    def test_get_index_file(self):
         # Create fake binary log index file.
        test_index = os.path.join(self.tmp_source, 'test-bin.index')
        with open(test_index, 'w') as f_obj:
            f_obj.write("test file (fake binary log index)\n")

        # Determine index file (full path).
        self.assertEqual(
            get_index_file(self.tmp_source, 'test-bin.000001'),
            test_index
        )

        # Check error: unable to get index file.
        self.assertRaises(UtilError, get_index_file, self.tmp_source,
                          'test-relay-bin.000001')

    def test_move_binary_log(self):
        # Create fake binary log files to move and index file.
        test_files = ['test-bin.000001', 'test-relay-bin.000101']
        for filename in test_files:
            test_file = os.path.join(self.tmp_source, filename)
            with open(test_file, 'w') as f_obj:
                f_obj.write("test file (fake binary log)\n")
        test_index = os.path.join(self.tmp_source, 'test-bin.index')
        with open(test_index, 'w') as f_obj:
            for filename in test_files:
                f_obj.write("{0}\n".format(os.path.join('.', filename)))

        # Move test files.
        for filename in test_files:
            move_binary_log(self.tmp_source, self.tmp_destination, filename,
                            test_index)

        # Confirm if files were successfully moved.
        dest_files = os.listdir(self.tmp_destination)
        for filename in test_files:
            self.assertIn(filename, dest_files)
        # Confirm if index file was updated correctly.
        with open(test_index, 'r') as f_obj:
            data = f_obj.readlines()
        expected_data = [
            '{0}\n'.format(os.path.join(self.tmp_destination, filename))
            for filename in test_files
        ]
        self.assertEqual(data, expected_data)

        # Move file back to source directory.
        move_binary_log(self.tmp_destination, self.tmp_source, test_files[0],
                        test_index)

        # Check error: source directory is invalid (not exist).
        self.assertRaises(IOError, move_binary_log, 'not_exist',
                          self.tmp_destination, test_files[0],
                          test_index)

        # Check error: destination directory does not exist.
        self.assertRaises(IOError, move_binary_log, self.tmp_source,
                          'not_exist', test_files[0], test_index)

        # Check error: destination file already exists.
        self.assertRaises(shutil.Error, move_binary_log, self.tmp_source,
                          self.tmp_destination, test_files[1], test_index)

        # Check error: binary file does not exist.
        self.assertRaises(IOError, move_binary_log, self.tmp_source,
                          self.tmp_destination, 'not_exist-bin.0000001',
                          test_index)

        # Check error: index file does not exist.
        self.assertRaises(UtilError, move_binary_log, self.tmp_source,
                          self.tmp_destination, test_files[0],
                          'not_exist')

        # Check error: no entry for the binary file in the index file.
        test_file = os.path.join(self.tmp_source, 'not_in_index.000007')
        with open(test_file, 'w') as f_obj:
            f_obj.write("test file (fake binary log, not in index file)\n")
        self.assertRaises(UtilError, move_binary_log, self.tmp_source,
                          self.tmp_destination, 'not_in_index.000007',
                          test_index)

    def test_filter_binary_logs_by_sequence(self):
        # Generate test filenames.
        test_files = []
        for i in range(1, 10):
            test_files.append('my-bin.00000{0}'.format(i))
        for i in range(3, 8):
            test_files.append('my-relay-bin.00000{0}'.format(i))

        # Test filtering filenames by sequence number.
        test_seq = [(2, 4), 6]
        expected_files = ['my-bin.000002', 'my-bin.000003', 'my-bin.000004',
                          'my-bin.000006', 'my-relay-bin.000003',
                          'my-relay-bin.000004', 'my-relay-bin.000006']
        self.assertEqual(filter_binary_logs_by_sequence(test_files, test_seq),
                         expected_files)

        test_seq = [1, (4, 5), 7, (9, 15)]
        expected_files = ['my-bin.000001', 'my-bin.000004', 'my-bin.000005',
                          'my-bin.000007', 'my-bin.000009',
                          'my-relay-bin.000004',
                          'my-relay-bin.000005', 'my-relay-bin.000007']
        self.assertEqual(filter_binary_logs_by_sequence(test_files, test_seq),
                         expected_files)

        test_seq = [2, 3, 6, 8]
        expected_files = ['my-bin.000002', 'my-bin.000003', 'my-bin.000006',
                          'my-bin.000008', 'my-relay-bin.000003',
                          'my-relay-bin.000006']
        self.assertEqual(filter_binary_logs_by_sequence(test_files, test_seq),
                         expected_files)

        test_seq = [(3, 5), (8, 10)]
        expected_files = ['my-bin.000003', 'my-bin.000004', 'my-bin.000005',
                          'my-bin.000008', 'my-bin.000009',
                          'my-relay-bin.000003', 'my-relay-bin.000004',
                          'my-relay-bin.000005']
        self.assertEqual(filter_binary_logs_by_sequence(test_files, test_seq),
                         expected_files)

    def test_filter_binary_logs_by_date(self):
        # Create fake binary log files for test.
        test_files = ['test-bin.000001', 'test-relay-bin.000101']
        for filename in test_files:
            test_file = os.path.join(self.tmp_source, filename)
            with open(test_file, 'w') as f_obj:
                f_obj.write("test file (fake binary log)\n")

        # No files older than 1 day.
        expected_files = []
        self.assertEqual(
            filter_binary_logs_by_date(test_files, self.tmp_source, 1),
            expected_files
        )

        # Check error: elapsed days must be > 0.
        self.assertRaises(UtilError, filter_binary_logs_by_date, test_files,
                          self.tmp_source, -1)

        # Check error: invalid date format (yyyy-mm-dd).
        self.assertRaises(UtilError, filter_binary_logs_by_date, test_files,
                          self.tmp_source, 'invalid_date')

        # Check error: invalid date/time format (yyyy-mm-ddThh:mm:ss).
        self.assertRaises(UtilError, filter_binary_logs_by_date, test_files,
                          self.tmp_source, '2014-07-21Tinvalid_time')

        # Hack file modified date/time (set it 2 days and 1 second before).
        test_file = os.path.join(self.tmp_source, test_files[0])
        hacked_time = time.time() - (86400 * 2) - 1
        os.utime(test_file, (hacked_time, hacked_time))

        # Files with last modification +2 days ago.
        expected_files = ['test-bin.000001']
        self.assertEqual(
            filter_binary_logs_by_date(test_files, self.tmp_source, 2),
            expected_files
        )

        # Files with last modification prior to yesterday.
        yesterday = time.localtime(time.time() - 86400)
        yesterday_date = time.strftime('%Y-%m-%d', yesterday)
        yesterday_datetime = time.strftime('%Y-%m-%dT%H:%M:%S', yesterday)
        self.assertEqual(
            filter_binary_logs_by_date(test_files, self.tmp_source,
                                       yesterday_date),
            expected_files
        )
        self.assertEqual(
            filter_binary_logs_by_date(test_files, self.tmp_source,
                                       yesterday_datetime),
            expected_files
        )
