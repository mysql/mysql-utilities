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
This module contains function to manipulate GTIDs.
"""


def get_last_server_gtid(gtid_set, server_uuid):
    """Get the last GTID of the specified GTID set for the given server UUID.

    This function retrieves the last GTID from the specified set for the
    specified server UUID. In more detail, it returns the GTID with the greater
    sequence value that matches the specified UUID.

    Note: The method assumes that GTID sets are grouped by UUID (separated by
    comma ',') and intervals appear in ascending order (i.e., the last one is
    the greater one).

    gtid_set[in]        GTID set to search and get last (greater) GTID value.
    server_uuid[in]     Server UUID to match, as a GTID set might contain data
                        for different servers (UUIDs).

    Returns a string with the last GTID value in the set for the given server
    UUID in the format 'uuid:n'. If no GTID are found in the set for the
    specified server UUID then None is returned.
    """
    uuid_sets = gtid_set.split(',')
    for uuid_set in uuid_sets:
        uuid_set_elements = uuid_set.strip().split(':')
        # Note: UUID are case insensitive, but can appear with mixed cases for
        # some server versions (e.g., for 5.6.9, lower case in server_id
        # variable and upper case in GTID_EXECUTED set).
        if uuid_set_elements[0].lower() == server_uuid.lower():
            last_interval = uuid_set_elements[-1]
            try:
                _, end_val = last_interval.split('-')
                return '{0}:{1}'.format(server_uuid, end_val)
            except ValueError:
                # Error raised for single values (not an interval).
                return '{0}:{1}'.format(server_uuid, last_interval)
    return None


def gtid_set_cardinality(gtid_set):
    """Determine the cardinality of the specified GTID set.

    This function counts the number of elements in the specified GTID set.

    gtid_set[in]    target set of GTIDs to determine the cardinality.

    Returns the number of elements of the specified GTID set.
    """
    count = 0
    uuid_sets = gtid_set.split(',')
    for uuid_set in uuid_sets:
        intervals = uuid_set.strip().split(':')[1:]
        for interval in intervals:
            try:
                start_val, end_val = interval.split('-')
                count = count + int(end_val) - int(start_val) + 1
            except ValueError:
                # Error raised for single values (not an interval).
                count += 1
    return count


def gtid_set_union(gtid_set_a, gtid_set_b):
    """Perform the union of two GTID sets.

    This method computes the union of two GTID sets and returns the result of
    the operation.

    Note: This method support input GTID sets not in the normalized form,
    i.e., with unordered and repeated UUID sets and intervals, but with
    a valid syntax.

    gtid_set_a[in]      First GTID set (set A).
    gtid_set_b[in]      Second GTID set (set B).

    Returns a string with the result of the set union operation between the
    two given GTID sets.
    """
    def get_gtid_dict(gtid_a, gtid_b):
        """Get a dict representation of the specified GTID sets.

        Combine the given GTID sets into a single dict structure, removing
        duplicated UUIDs and string intervals.

        Return a dictionary (not normalized) with the GTIDs contained in both
        input GTID sets. For example, for the given (not normalized) GTID sets
        'uuid_a:2:5-7,uuid_b:4' and 'uuid_a:2:4-6:2,uuid_b:1-3' the follow dict
        will be returned:
        {'uuid_a': set(['2', '5-7', '4-6']), 'uuid_b': set(['4','1-3'])}
        """
        res_dict = {}
        uuid_sets_a = gtid_a.split(',')
        uuid_sets_b = gtid_b.split(',')
        uuid_sets = uuid_sets_a + uuid_sets_b
        for uuid_set in uuid_sets:
            uuid_set_values = uuid_set.split(':')
            uuid_key = uuid_set_values[0]
            if uuid_key in res_dict:
                res_dict[uuid_key] = \
                    res_dict[uuid_key].union(uuid_set_values[1:])
            else:
                res_dict[uuid_key] = set(uuid_set_values[1:])
        return res_dict

    # Create auxiliary dict representation of both input GTID sets.
    gtid_dict = get_gtid_dict(gtid_set_a, gtid_set_b)

    # Perform the union between the GTID sets.
    union_gtid_list = []
    for uuid in gtid_dict:
        intervals = gtid_dict[uuid]
        # Convert the set of string intervals into a single list of tuples
        # with integers, in order to be handled easily.
        intervals_list = []
        for values in intervals:
            interval = values.split('-')
            intervals_list.append((int(interval[0]), int(interval[-1])))
        # Compute the union of the tuples (intervals).
        union_set = []
        for start, end in sorted(intervals_list):
            # Note: no interval start before the next one (ordered list).
            if union_set and start <= union_set[-1][1] + 1:
                # Current interval intersects or is consecutive to the last
                # one in the results.
                if union_set[-1][1] < end:
                    # If the end of the interval is greater than the last one
                    # then augment it (set the new end), otherwise do nothing
                    # (meaning the interval is fully included in the last one).
                    union_set[-1] = (union_set[-1][0], end)
            else:
                # No interval in the results or the interval does not intersect
                # nor is consecutive to the last one, then add it to the end of
                # the results list.
                union_set.append((start, end))
        # Convert resulting union set to a valid string format.
        union_str = ":".join(
            ["{0}-{1}".format(vals[0], vals[1])
             if vals[0] != vals[1] else str(vals[0]) for vals in union_set]
        )
        # Concatenate UUID and add the to the result list.
        union_gtid_list.append("{0}:{1}".format(uuid, union_str))

    # GTID sets are sorted alphabetically, return the result accordingly.
    return ','.join(sorted(union_gtid_list))


def gtid_set_itemize(gtid_set):
    """Itemize the given GTID set.

    Decompose the given GTID set into a list of individual GTID items grouped
    by UUID.

    gtid_set[in]    GTID set to itemize.

    Return a list of tuples with the UUIDs and transactions number for all
    individual items in the GTID set. For example: 'uuid_a:1-3:5,uuid_b:4' is
    converted into [('uuid_a', [1, 2, 3, 5]), ('uuid_b', [4])].
    """
    gtid_list = []
    uuid_sets = gtid_set.split(',')
    for uuid_set in uuid_sets:
        uuid_set_elements = uuid_set.split(':')
        trx_num_list = []
        for interval in uuid_set_elements[1:]:
            try:
                start_val, end_val = interval.split('-')
                trx_num_list.extend(range(int(start_val), int(end_val) + 1))
            except ValueError:
                # Error raised for single values (not an interval).
                trx_num_list.append(int(interval))
        gtid_list.append((uuid_set_elements[0], trx_num_list))
    return gtid_list
