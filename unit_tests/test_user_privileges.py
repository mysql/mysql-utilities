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

import unittest

from collections import defaultdict

from mysql.utilities.common import user, server
from mysql.utilities.exception import UtilError


class TestUserPrivileges(unittest.TestCase):

    def setUp(self):

        dummy_s1 = server.Server({"conn_info": "user1@notexists:999999"})
        dummy_s2 = server.Server({"conn_info": "user2@notexists:999998"})

        self.user1 = user.User(dummy_s1, "user1@'%'")
        self.user2 = user.User(dummy_s2, "user2@'%'")
        # Monkey patch grant_tables_enabled method since it is used on
        # has_privilege method
        self.user1.server1.grant_tables_enabled = lambda: True
        self.user2.server1.grant_tables_enabled = lambda: True
        self.user1_dict = None
        self.user2_dict = None

        # Monkey patch User get_grants method
        self.user1.get_grants = lambda **x: self.user1_dict
        self.user2.get_grants = lambda **x: self.user2_dict

    def _get_privs_dict(self, grant_str, def_dict=None):
        grants_tpl = user.User._parse_grant_statement(grant_str)
        if def_dict is None:
            def_dict = defaultdict(lambda: defaultdict(set))
        def_dict[grants_tpl.db][grants_tpl.object].update(
            grants_tpl.privileges)

        return def_dict

    def test_equal_privs(self):

        self.user1_dict = self._get_privs_dict(
            "GRANT SELECT, UPDATE ON `mysql`.* TO 'user1'@'%'")
        self.user2_dict = self._get_privs_dict(
            "GRANT UPDATE, SELECT ON mysql.* TO 'user2'@'%' IDENTIFIED BY "
            "PASSWORD '*123DD712CFDED6313E0DDD2A6E0D62F12E580A6F'")

        # Users are equivalent, so it should be true both ways
        self.assertTrue(self.user2.contains_user_privileges(self.user1))
        self.assertTrue(self.user1.contains_user_privileges(self.user2))
        self.assertEquals(set(), self.user2.missing_user_privileges(
            self.user1))
        self.assertEquals(set(), self.user1.missing_user_privileges(
            self.user2))

        # A user should contain the same privileges as itself
        self.assertTrue(self.user2.contains_user_privileges(self.user2))
        self.assertEquals(set(), self.user2.missing_user_privileges(
            self.user2))

        # If we are cloning parameter is true,  it needs to have an extra
        # GRANT OPTION grant

        self.assertFalse(self.user2.contains_user_privileges(
            self.user1, plus_grant_option=True))
        # When cloning is True, we need to set the user_dict again due to
        # the way we stubbed the User.get_grants method
        self.user1_dict = self._get_privs_dict(
            "GRANT SELECT, UPDATE ON `mysql`.* TO 'user1'@'%'")

        self.assertEquals(set([("GRANT OPTION", '`mysql`', '*')]),
                          self.user2.missing_user_privileges(
                              self.user1, plus_grant_option=True))

        self.user1_dict = self._get_privs_dict(
            "GRANT SELECT, UPDATE ON `mysql`.* TO 'user1'@'%'")

        self.assertFalse(self.user1.contains_user_privileges(
            self.user2, plus_grant_option=True))
        # Now user2 has GRANT OPTION and can clone U1, but not the other
        # way around
        self.user1_dict = self._get_privs_dict(
            "GRANT SELECT, UPDATE ON `mysql`.* TO 'user1'@'%'")
        self.user2_dict = self._get_privs_dict(
            "GRANT UPDATE, SELECT ON `mysql`.* TO 'user2'@'%' IDENTIFIED BY "
            "PASSWORD '*123DD712CFDED6313E0DDD2A6E0D62F12E580A6F' "
            "WITH GRANT OPTION")
        self.assertTrue(self.user2.contains_user_privileges(
            self.user1, plus_grant_option=True))
        self.user1_dict = self._get_privs_dict(
            "GRANT SELECT, UPDATE ON `mysql`.* TO 'user1'@'%'")
        self.assertFalse(self.user1.contains_user_privileges(
            self.user2, plus_grant_option=True))

    def test_subset_privs(self):

        # Tests that GRANT OPTION is not added with the usage privilege
        # when used together with plus_grant_option option
        self.user1_dict = self._get_privs_dict(
            "GRANT USAGE ON *.* TO 'user1'@'%'")
        self.user2_dict = self._get_privs_dict(
            "GRANT SELECT, UPDATE ON `mysql`.* TO 'user2'@'%'")

        self.assertTrue(self.user2.contains_user_privileges(
            self.user1, plus_grant_option=True))
        self.assertFalse(self.user1.contains_user_privileges(
            self.user2, plus_grant_option=True))

        self.user1_dict = self._get_privs_dict(
            "GRANT SELECT, UPDATE ON `mysql`.`users` TO 'user1'@'%'")
        self.user2_dict = self._get_privs_dict(
            "GRANT SELECT, UPDATE ON `mysql`.* TO 'user2'@'%'")

        # User2 has privileges for entire mysql database, unlike user1.
        self.assertTrue(self.user2.contains_user_privileges(self.user1))
        self.assertFalse(self.user1.contains_user_privileges(self.user2))
        self.assertEquals(set(), self.user2.missing_user_privileges(
            self.user1))
        self.assertEquals(set([('SELECT', '`mysql`', '*'),
                               ('UPDATE', '`mysql`', '*')]),
                          self.user1.missing_user_privileges(self.user2))

        self.user1_dict = self._get_privs_dict(
            "GRANT SELECT, UPDATE, DELETE ON `mysql`.`users` TO 'user1'@'%'")
        self.user2_dict = self._get_privs_dict(
            "GRANT SELECT, UPDATE ON `mysql`.* TO 'user2'@'%'")
        self.assertFalse(self.user2.contains_user_privileges(self.user1))
        self.assertFalse(self.user1.contains_user_privileges(self.user2))

        self.user1_dict = self._get_privs_dict(
            "GRANT SELECT, UPDATE ON `mysql`.`users` TO 'user1'@'%'")
        self.user1_dict = self._get_privs_dict(
            "GRANT SELECT ON `mysql`.`db` TO 'user1'@'%'", self.user1_dict)
        self.user2_dict = self._get_privs_dict(
            "GRANT SELECT ON `mysql`.* TO 'user2'@'%'")
        self.assertFalse(self.user2.contains_user_privileges(self.user1))
        self.assertFalse(self.user1.contains_user_privileges(self.user2))

        self.user2_dict = self._get_privs_dict(
            "GRANT UPDATE ON `mysql`.* TO 'user2'@'%'", self.user2_dict)
        self.assertTrue(self.user2.contains_user_privileges(self.user1))
        self.assertFalse(self.user1.contains_user_privileges(self.user2))

        # Usage privilege is the same as no privileges.
        self.user1_dict = self._get_privs_dict(
            "GRANT USAGE ON *.* TO 'user1'@'%'")
        self.user2_dict = self._get_privs_dict(
            "GRANT SELECT, UPDATE ON `mysql`.* TO 'user2'@'%'")
        self.assertTrue(self.user2.contains_user_privileges(self.user1))
        self.assertFalse(self.user1.contains_user_privileges(self.user2))
        self.assertEquals(set(), self.user2.missing_user_privileges(
            self.user1))
        self.assertEquals(set([('SELECT', '`mysql`', '*'),
                               ('UPDATE', '`mysql`', '*')]),
                          self.user1.missing_user_privileges(self.user2))

    def test_double_star_privs(self):

        # ALL PRIVILEGES grant is a superset of all other grants except for
        # the GRANT OPTION privilege.
        self.user1_dict = self._get_privs_dict(
            "GRANT SELECT, UPDATE, DELETE ON `mysql`.`users` TO 'user1'@'%'")
        self.user2_dict = self._get_privs_dict(
            "GRANT ALL PRIVILEGES ON `mysql`.* TO 'user2'@'%'")
        self.assertTrue(self.user2.contains_user_privileges(self.user1))
        self.assertFalse(self.user1.contains_user_privileges(self.user2))

        self.user1_dict = self._get_privs_dict(
            "GRANT SELECT, UPDATE, DELETE ON `mysql`.`users` TO 'user1'@'%'")
        self.user2_dict = self._get_privs_dict(
            "GRANT ALL PRIVILEGES ON `mysql`.`users` TO 'user2'@'%'")
        self.assertTrue(self.user2.contains_user_privileges(self.user1))
        self.assertFalse(self.user1.contains_user_privileges(self.user2))

        self.user1_dict = self._get_privs_dict(
            "GRANT SELECT, UPDATE, DELETE ON `mysql`.`users` TO 'user1'@'%' "
            "WITH GRANT OPTION")
        self.user2_dict = self._get_privs_dict(
            "GRANT ALL PRIVILEGES ON `mysql`.`users` TO 'user2'@'%'")
        self.assertFalse(self.user2.contains_user_privileges(self.user1))
        self.assertFalse(self.user1.contains_user_privileges(self.user2))
        self.assertEquals(set([('GRANT OPTION', '`mysql`', '`users`')]),
                          self.user2.missing_user_privileges(self.user1))
        self.assertEquals(set([('ALL PRIVILEGES', '`mysql`', '`users`')]),
                          self.user1.missing_user_privileges(self.user2))

        self.user1_dict = self._get_privs_dict(
            "GRANT SELECT, UPDATE, DELETE ON `mysql`.`users` TO 'user1'@'%'")
        self.user2_dict = self._get_privs_dict(
            "GRANT ALL PRIVILEGES ON `mysql`.`db` TO 'user2'@'%'")
        self.assertFalse(self.user2.contains_user_privileges(self.user1))
        self.assertFalse(self.user1.contains_user_privileges(self.user2))

        self.user1_dict = self._get_privs_dict(
            "GRANT SELECT, UPDATE, DELETE ON `mysql`.users TO 'user1'@'%'")
        self.user2_dict = self._get_privs_dict(
            "GRANT SELECT, UPDATE, DELETE ON *.* TO 'user2'@'%'")
        self.assertTrue(self.user2.contains_user_privileges(self.user1))
        self.assertFalse(self.user1.contains_user_privileges(self.user2))
        self.assertEquals(set(), self.user2.missing_user_privileges(
            self.user1))
        self.assertEquals(set([("UPDATE", '*', '*'), ("SELECT", '*', '*'),
                               ("DELETE", '*', '*')]),
                          self.user1.missing_user_privileges(self.user2))

        self.user1_dict = self._get_privs_dict(
            "GRANT ALL PRIVILEGES ON *.* TO 'user1'@'%'")
        self.user2_dict = self._get_privs_dict(
            "GRANT ALL PRIVILEGES ON *.* TO 'user2'@'%' WITH GRANT OPTION")

        self.assertTrue(self.user2.contains_user_privileges(self.user1))
        self.assertFalse(self.user1.contains_user_privileges(self.user2))
        self.assertEquals(set(), self.user2.missing_user_privileges(
            self.user1))
        self.assertEquals(set([("GRANT OPTION", '*', '*')]),
                          self.user1.missing_user_privileges(self.user2))

    def test_parse_grant_statement(self):
        # Test function
        self.assertEquals(user.User._parse_grant_statement(
            "GRANT ALTER ROUTINE, EXECUTE ON FUNCTION `util_test`.`f1` TO "
            "'priv_test_user2'@'%' WITH GRANT OPTION"),
            (set(['GRANT OPTION', 'EXECUTE', 'ALTER ROUTINE']), None,
                '`util_test`', '`f1`', "'priv_test_user2'@'%'"))
        # Test procedure
        self.assertEquals(user.User._parse_grant_statement(
            "GRANT ALTER ROUTINE ON PROCEDURE `util_test`.`p1` TO "
            "'priv_test_user2'@'%' IDENTIFIED BY "
            "PASSWORD '*123DD712CFDED6313E0DDD2A6E0D62F12E580A6F' "
            "WITH GRANT OPTION"),
            (set(['GRANT OPTION', 'ALTER ROUTINE']), None,
                '`util_test`', '`p1`', "'priv_test_user2'@'%'"))
        # Test with quoted objects
        self.assertEquals(user.User._parse_grant_statement(
            "GRANT CREATE VIEW ON `db``:db`.```t``.``export_2` TO "
            "'priv_test_user'@'%'"),
            (set(['CREATE VIEW']), None, '`db``:db`.```t``', '``export_2`',
                "'priv_test_user'@'%'"))
        self.assertEquals(user.User._parse_grant_statement(
            "GRANT CREATE VIEW ON `db``:db`.```t``.* TO "
            "'priv_test_user'@'%'"),
            (set(['CREATE VIEW']), None, '`db``:db`.```t``', '*',
                "'priv_test_user'@'%'"))
        # Test multiple grants with password and grant option
        self.assertEquals(user.User._parse_grant_statement(
            "GRANT UPDATE, SELECT ON `mysql`.* TO 'user2'@'%' IDENTIFIED BY "
            "PASSWORD '*123DD712CFDED6313E0DDD2A6E0D62F12E580A6F' "
            "REQUIRE SSL WITH GRANT OPTION"),
            (set(['GRANT OPTION', 'UPDATE', 'SELECT']), None, '`mysql`',
                '*', "'user2'@'%'"))
        self.assertEquals(user.User._parse_grant_statement(
            "GRANT UPDATE, SELECT ON `mysql`.* TO 'user2'@'%' IDENTIFIED BY "
            "PASSWORD REQUIRE SSL WITH GRANT OPTION"),
            (set(['GRANT OPTION', 'UPDATE', 'SELECT']), None, '`mysql`',
                '*', "'user2'@'%'"))
        # Test proxy privileges
        self.assertEquals(user.User._parse_grant_statement(
            "GRANT PROXY ON ''@'' TO 'root'@'localhost' WITH GRANT OPTION"),
            (set(['GRANT OPTION', 'PROXY']), "''@''", None, None,
                "'root'@'localhost'"))
        self.assertEquals(user.User._parse_grant_statement(
            "GRANT PROXY ON 'root'@'%' TO 'root'@'localhost' WITH GRANT "
            "OPTION"),
            (set(['GRANT OPTION', 'PROXY']), "'root'@'%'", None, None,
                "'root'@'localhost'"))
        self.assertRaises(UtilError, user.User._parse_grant_statement,
                          "GRANT PROXY 'root'@'%' TO 'root'@'localhost' WITH "
                          "GRANT OPTION")
if __name__ == '__main__':
    unittest.main()
