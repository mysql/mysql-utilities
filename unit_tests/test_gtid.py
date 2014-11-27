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
This files contains unit tests for mysql.utilities.common.gtid module.
"""

import unittest

from mysql.utilities.common.gtid import (get_last_server_gtid,
                                         gtid_set_cardinality,
                                         gtid_set_itemize,
                                         gtid_set_union)


class TestBinaryLogFile(unittest.TestCase):

    def test_get_last_server_gtid(self):
        # Get last GTID from a given GTID set (for all UUIDs and non-existing).
        gtid_set = ('cfb4dd08-588e-11e4-89aa-606720440b68:7,'
                    'D4F8EB6E-588e-11E4-89AA-606720440b68:1-4:6:8:10-11,'
                    'da1f90b1-588e-11e4-89aa-606720440b68:5-8')
        expected_result = ['cfb4dd08-588e-11e4-89aa-606720440b68:7',
                           'd4f8eb6e-588e-11e4-89aa-606720440b68:11',
                           'da1f90b1-588e-11e4-89aa-606720440b68:8', None]
        uuids = ['cfb4dd08-588e-11e4-89aa-606720440b68',
                 'd4f8eb6e-588e-11e4-89aa-606720440b68',
                 'da1f90b1-588e-11e4-89aa-606720440b68',
                 'aaaaaaaa-588e-11e4-89aa-606720440b68']
        for i, uuid in enumerate(uuids):
            result = get_last_server_gtid(gtid_set, uuid)
            self.assertEqual(expected_result[i], result)

    def test_gtid_set_cardinality(self):
        # Determine the number og GTIDs in a GTID set.
        gtid_set = 'cfb4dd08-588e-11e4-89aa-606720440b68:7,'
        self.assertEqual(1, gtid_set_cardinality(gtid_set))
        gtid_set = 'da1f90b1-588e-11e4-89aa-606720440b68:5-8'
        self.assertEqual(4, gtid_set_cardinality(gtid_set))
        gtid_set = ('cfb4dd08-588e-11e4-89aa-606720440b68:7,'
                    'D4F8EB6E-588e-11E4-89AA-606720440b68:1-4:6:8:10-11,'
                    'da1f90b1-588e-11e4-89aa-606720440b68:5-8')
        self.assertEqual(13, gtid_set_cardinality(gtid_set))

    def test_gtid_set_union(self):
        # Union of GTID sets with the same UUID.
        gtid_set_a = 'cfb4dd08-588e-11e4-89aa-606720440b68:1-3'
        gtid_set_b = 'cfb4dd08-588e-11e4-89aa-606720440b68:7'
        expected_result = 'cfb4dd08-588e-11e4-89aa-606720440b68:1-3:7'
        result = gtid_set_union(gtid_set_a, gtid_set_b)
        self.assertEqual(expected_result, result)

        # Union of GTID sets with different UUIDs.
        gtid_set_a = 'd4f8eb6e-588e-11e4-89aa-606720440b68:7'
        gtid_set_b = 'cfb4dd08-588e-11e4-89aa-606720440b68:1-3'
        expected_result = ('cfb4dd08-588e-11e4-89aa-606720440b68:1-3,'
                           'd4f8eb6e-588e-11e4-89aa-606720440b68:7')
        result = gtid_set_union(gtid_set_a, gtid_set_b)
        self.assertEqual(expected_result, result)

        # Union of GTID sets with different UUIDs and intersecting intervals.
        gtid_set_a = ('cfb4dd08-588e-11e4-89aa-606720440b68:2-4:6:8-9:12,'
                      'd4f8eb6e-588e-11e4-89aa-606720440b68:7')
        gtid_set_b = 'cfb4dd08-588e-11e4-89aa-606720440b68:1-3:9-11:13'
        expected_result = ('cfb4dd08-588e-11e4-89aa-606720440b68:1-4:6:8-13,'
                           'd4f8eb6e-588e-11e4-89aa-606720440b68:7')
        result = gtid_set_union(gtid_set_a, gtid_set_b)
        self.assertEqual(expected_result, result)

        # Union of GTID sets not in the normalized format (itemized) and with
        # repeated values.
        gtid_set_a = ('da1f90b1-588e-11e4-89aa-606720440b68:5,'
                      'cfb4dd08-588e-11e4-89aa-606720440b68:2-4:6:8-9:12,'
                      'd4f8eb6e-588e-11e4-89aa-606720440b68:7,'
                      'da1f90b1-588e-11e4-89aa-606720440b68:1,'
                      'd4f8eb6e-588e-11e4-89aa-606720440b68:7,'
                      'da1f90b1-588e-11e4-89aa-606720440b68:9,'
                      'da1f90b1-588e-11e4-89aa-606720440b68:4:1-2')
        gtid_set_b = ('cfb4dd08-588e-11e4-89aa-606720440b68:1-3:9-11:13,'
                      'da1f90b1-588e-11e4-89aa-606720440b68:9:1-2')
        expected_result = ('cfb4dd08-588e-11e4-89aa-606720440b68:1-4:6:8-13,'
                           'd4f8eb6e-588e-11e4-89aa-606720440b68:7,'
                           'da1f90b1-588e-11e4-89aa-606720440b68:1-2:4-5:9')
        result = gtid_set_union(gtid_set_a, gtid_set_b)
        self.assertEqual(expected_result, result)

    def test_gtid_set_itemize(self):
        gtid_set = ('cfb4dd08-588e-11e4-89aa-606720440b68:7,'
                    'd4f8eb6e-588e-11e4-89aa-606720440b68:1-4:6:8:10-11,'
                    'da1f90b1-588e-11e4-89aa-606720440b68:5-8')
        expected_result = [
            ('cfb4dd08-588e-11e4-89aa-606720440b68', [7]),
            ('d4f8eb6e-588e-11e4-89aa-606720440b68',
             [1, 2, 3, 4, 6, 8, 10, 11]),
            ('da1f90b1-588e-11e4-89aa-606720440b68', [5, 6, 7, 8])
        ]
        # Decompose (itemize) a GTID set with different intervals and UUIDs.
        self.assertEqual(gtid_set_itemize(gtid_set), expected_result)
