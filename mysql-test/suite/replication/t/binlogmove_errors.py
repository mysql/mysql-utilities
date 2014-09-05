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
Test errors issued by the mysqlbinlogmove utility.
"""

import os

import mutlib

from mysql.utilities.exception import MUTLibError


class test(mutlib.System_test):
    """Test binlog relocate utility errors.

    This test checks the mysqlbinlogmove utility known error conditions.
    """

    def check_prerequisites(self):
        # No prerequisites required.
        return True

    def setup(self):
        self.res_fname = "result.txt"
        # No need to spawn any server.
        return True

    def run(self):

        cmd_base = "mysqlbinlogmove.py"

        test_num = 1
        comment = ("Test case {0} - server or binlog-dir required."
                   "").format(test_num)
        res = self.run_test_case(2, cmd_base, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - server and binlog-dir cannot be used "
                   "at the same time.").format(test_num)
        cmd = "{0} --server=root --binlog-dir=.".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - invalid server connection format."
                   "").format(test_num)
        cmd = "{0} --server=@:invalid".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - invalid binlog-dir directory."
                   "").format(test_num)
        cmd = "{0} --binlog-dir=/invalid/not/exist".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - missing destination directory."
                   "").format(test_num)
        cmd = "{0} --binlog-dir=.".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - multiple destinations."
                   "").format(test_num)
        cmd = "{0} --binlog-dir=. /target1 /target2".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - invalid destination directory."
                   "").format(test_num)
        cmd = "{0} --binlog-dir=. /invalid/not/exist".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - invalid binlog index file.".format(test_num)
        cmd = ("{0} --binlog-dir=. --bin-log-index=invalid.index "
               ".").format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - invalid relay log index file."
                   "").format(test_num)
        cmd = ("{0} --binlog-dir=. --relay-log-index=invalid.index "
               ".").format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - invalid log type.".format(test_num)
        cmd = "{0} --binlog-dir=. --log-type=fake .".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - invalid --sequence option "
                   "value".format(test_num))
        cmd = '{0} --sequence="",, --binlog-dir=. .'.format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = "Test case {0} - invalid SEQUENCE value".format(test_num)
        cmd = "{0} --sequence=ABC --binlog-dir=. .".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - invalid SEQUENCE interval "
                   "format".format(test_num))
        cmd = ("{0} --sequence=123,200-250-300 --binlog-dir=. "
               ".").format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - invalid SEQUENCE interval "
                   "lower bound".format(test_num))
        cmd = "{0} --sequence=.1-100 --binlog-dir=. .".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - invalid SEQUENCE interval "
                   "upper bound".format(test_num))
        cmd = "{0} --sequence=1- --binlog-dir=. .".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - invalid --modified-before option "
                   "value".format(test_num))
        cmd = "{0} --modified-before=INVALID --binlog-dir=. .".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - invalid MODIFIED_BEFORE number of "
                   "days".format(test_num))
        cmd = "{0} --modified-before=0 --binlog-dir=. .".format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - invalid MODIFIED_BEFORE date/time "
                   "format".format(test_num))
        cmd = ("{0} --modified-before=10:05:00T2014-07-21 --binlog-dir=. "
               ".").format(cmd_base)
        res = self.run_test_case(2, cmd, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except OSError:
                pass
        return True
