#
# Copyright (c) 2013 Oracle and/or its affiliates. All rights reserved.
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
This files contains unit tests for reading the MySQL login configuration file.
"""
import os
import subprocess
import tempfile
import time
import unittest

from mysql.utilities.exception import UtilError

from mysql.utilities.common.my_print_defaults import my_login_config_exists
from mysql.utilities.common.my_print_defaults import my_login_config_path
from mysql.utilities.common.my_print_defaults import MyDefaultsReader
from mysql.utilities.common.tools import get_tool_path

_TEST_LOGIN_PATH = 'test_my_print_defaults'
_TEST_USER = '127.0.0.1'
_TEST_HOST = 'localuser'
_TEST_UNKNOWN_LOGIN_PATH = 'test_unknown_group_data'


def mysql_tools_found():
    # mysql_config_editor needs to be accessible to run the tests
    try:
        return get_tool_path(None, "mysql_config_editor", search_PATH=True)
    except Exception:
        return None


@unittest.skipUnless(mysql_tools_found(),
                     "MySQL client tools (e.g. mysql_config_editor) must be "
                     "accessible to run this test.")
class TestMyPrintDefaults(unittest.TestCase):
    # NOTE: MySQL client tools (e.g., my_print_defaults) must be accessible,
    # for example by including their location in the PATH.

    @classmethod
    def setUpClass(cls):
        # Find mysql_config_editor to manipulate data from .mylogin.cnf
        try:
            cls.edit_tool_path = get_tool_path(None, "mysql_config_editor",
                                               search_PATH=True)
        except UtilError as err:
            raise UtilError("MySQL client tools must be accessible to run "
                            "this test (%s). Please add the location of the "
                            "MySQL client tools to your PATH." % err.errmsg)

        # Create login-path data
        cmd = ("{mysql_config_editor} set --login-path={login_path} "
               "--host={host} --user={user}")
        cmd = cmd.format(mysql_config_editor=cls.edit_tool_path,
                         login_path=_TEST_LOGIN_PATH,
                         host=_TEST_HOST, user=_TEST_USER)

        # Execute command to create login-path data
        proc = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE,
                                stdin=subprocess.PIPE)
        # Overwrite login-path if already exists (i.e. answer 'y' to question)
        proc.communicate(input='y')

    @classmethod
    def tearDownClass(cls):
        # Remove login-path data
        cmd = "{mysql_config_editor} remove --login-path={login_path}"
        cmd = cmd.format(mysql_config_editor=cls.edit_tool_path,
                         login_path=_TEST_LOGIN_PATH)

        # Create a temporary file to redirect stdout
        out_file = tempfile.TemporaryFile()

        # Execute command to remove login-path data
        subprocess.call(cmd.split(' '), stdout=out_file)

    def setUp(self):
        # For safety, store the current PATH (to be restored)
        self.env_path = os.environ['PATH']

    def tearDown(self):
        # For safety, restore the PATH (previously stored)
        os.environ['PATH'] = self.env_path

    def test_my_login_config_path(self):
        # Check if the path (directory) to .mylogin.cnf exists
        path = my_login_config_path()
        self.assertTrue(os.path.isdir(path))

    def test_my_login_config_exists(self):
        # Check if .my_login.cnf file exists
        self.assertTrue(my_login_config_exists())

    def test_MyDefaultsReader(self):
        # Test the creation of MyDefaultsReader object

        # find_my_print_defaults_tool=False
        cfg_reader = MyDefaultsReader(find_my_print_defaults_tool=False)
        self.assertIsNone(cfg_reader.tool_path)
        self.assertDictEqual(cfg_reader._config_data, {})

        # find_my_print_defaults_tool=True (by default)
        cfg_reader = MyDefaultsReader()
        self.assertDictEqual(cfg_reader._config_data, {})
        self.assertTrue(os.path.isfile(cfg_reader.tool_path))

        # keep the location of the tool (to use as basedir)
        tool_dir = os.path.dirname(cfg_reader.tool_path)

        # Empty the PATH - UtilError raised if tool is not found
        os.environ['PATH'] = ''
        self.assertRaises(UtilError, MyDefaultsReader)

        # Specify a basedir to find the tool (PATH empty)
        options = {
            'basedir': tool_dir
        }
        cfg_reader = MyDefaultsReader(options)
        self.assertDictEqual(cfg_reader._config_data, {})
        self.assertTrue(os.path.isfile(cfg_reader.tool_path))

    def test_search_my_print_defaults_tool(self):
        # Test the search for the my_print_defaults tool
        cfg_reader = MyDefaultsReader(find_my_print_defaults_tool=False)
        self.assertIsNone(cfg_reader.tool_path)

        cfg_reader.search_my_print_defaults_tool()
        self.assertTrue(os.path.isfile(cfg_reader.tool_path))

        # keep the location of the tool (to use as search_path)
        tool_dir = os.path.dirname(cfg_reader.tool_path)

        # Empty the PATH - UtilError raised if tool is not found
        os.environ['PATH'] = ''
        cfg_reader = MyDefaultsReader(find_my_print_defaults_tool=False)
        self.assertIsNone(cfg_reader.tool_path)
        self.assertRaises(UtilError, cfg_reader.search_my_print_defaults_tool)

        # Specify the search paths to find the tool (PATH empty)
        self.assertRaises(UtilError, cfg_reader.search_my_print_defaults_tool,
                          ['not-a-valid-path'])
        cfg_reader.search_my_print_defaults_tool(['not-a-valid-path',
                                                  tool_dir])
        self.assertTrue(os.path.isfile(cfg_reader.tool_path))

    def test_check_tool_version(self):
        # Test the check of the my_print_defaults tool version
        # NOTE: current tool version is 1.6 (not have been update lately)
        cfg_reader = MyDefaultsReader()
        self.assertTrue(cfg_reader.check_tool_version(1, 6),
                        "Only version 1.6 or above of my_prints_defaults tool"
                        " is supported. Please add the location of a "
                        "supported tool version to your PATH (at the "
                        "beginning).")
        self.assertTrue(cfg_reader.check_tool_version(1, 0))
        self.assertFalse(cfg_reader.check_tool_version(1, 99))
        self.assertFalse(cfg_reader.check_tool_version(99, 0))
        self.assertTrue(cfg_reader.check_tool_version(0, 0))
        self.assertTrue(cfg_reader.check_tool_version(0, 99))

    def test_check_login_path_support(self):
        # Test if the my_print_defaults tool supports login-path options
        # NOTE: The version of the my_print_defaults tool as not been updated
        # properly (latest known version is 1.6). Therefore, not all the
        # my_print_defaults tools that report the version 1.6 support the use
        # of login-path.

        cfg_reader = MyDefaultsReader()
        self.assertTrue(cfg_reader.check_login_path_support(),
                        "The used my_prints_defaults tool does not support "
                        "login-path options: %s. Please add the location of a"
                        "tool that support login-path to your PATH (at the "
                        "beginning)." % cfg_reader.tool_path)

    def test_get_group_data(self):
        # Test the retrieve of the login-path group data from .mylogin.cnf

        cfg_reader = MyDefaultsReader(find_my_print_defaults_tool=False)

        # Test the assertion: First, my_print_defaults must be found.
        self.assertRaises(AssertionError, cfg_reader.get_group_data,
                          _TEST_LOGIN_PATH)

        cfg_reader.search_my_print_defaults_tool()

        expected_res = {
            'host': _TEST_HOST,
            'user': _TEST_USER
        }
        # 1rst time, get data from my_prints_defaults
        start_time1 = time.time()
        grp_data = cfg_reader.get_group_data(_TEST_LOGIN_PATH)
        end_time1 = time.time()
        self.assertEqual(expected_res, grp_data)

        # 2nd time, return previously obtained information (faster)
        start_time2 = time.time()
        grp_data = cfg_reader.get_group_data(_TEST_LOGIN_PATH)
        end_time2 = time.time()
        self.assertEqual(expected_res, grp_data)

        # Must be faster to retrieve the same data the second time
        self.assertLess((end_time2 - start_time2), (end_time1 - start_time1))

        # Return None if the specified group does not exist
        grp_data = cfg_reader.get_group_data(_TEST_UNKNOWN_LOGIN_PATH)
        self.assertIsNone(grp_data)

    def test_get_option_value(self):
        # Test the retrieve of specific option values from .mylogin.cnf

        cfg_reader = MyDefaultsReader(find_my_print_defaults_tool=False)

        # Test the assertion: First, my_print_defaults must be found.
        self.assertRaises(AssertionError, cfg_reader.get_option_value,
                          _TEST_LOGIN_PATH, _TEST_HOST)
        self.assertRaises(AssertionError, cfg_reader.get_option_value,
                          _TEST_LOGIN_PATH, _TEST_USER)

        cfg_reader.search_my_print_defaults_tool()

        expected_res = {
            'host': _TEST_HOST,
            'user': _TEST_USER
        }

        # Get user
        opt_value = cfg_reader.get_option_value(_TEST_LOGIN_PATH, 'user')
        self.assertEqual(expected_res['user'], opt_value)

        # Get host
        opt_value = cfg_reader.get_option_value(_TEST_LOGIN_PATH, 'host')
        self.assertEqual(expected_res['host'], opt_value)

        # Return None if the specified option/group does not exist
        opt_value = cfg_reader.get_option_value(_TEST_LOGIN_PATH, 'unknown')
        self.assertIsNone(opt_value)
        opt_value = cfg_reader.get_option_value(_TEST_UNKNOWN_LOGIN_PATH,
                                                'user')
        self.assertIsNone(opt_value)
        opt_value = cfg_reader.get_option_value(_TEST_UNKNOWN_LOGIN_PATH,
                                                'host')
        self.assertIsNone(opt_value)

if __name__ == "__main__":
    unittest.main()
