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
This module helps to format the ssl options on MUT to be used on mysqld when
cloning a server and running the utilities.
"""

import os

ssl_user = "root_ssl"

ssl_pass = "root_ssl"

STD_DATA_PATH = "./std_data/ssl_certs/"

SSL_CA = "{0}/cacert.pem"

SSL_CERT = "{0}/server-cert.pem"

SSL_KEY = "{0}/server-key.pem"

ssl_c_ca = os.path.abspath(SSL_CA.format(STD_DATA_PATH)).replace('\\', '/')

ssl_c_cert = os.path.abspath(SSL_CERT.format(STD_DATA_PATH)).replace('\\', '/')

ssl_c_key = os.path.abspath(SSL_KEY.format(STD_DATA_PATH)).replace('\\', '/')

SSL_OPTS = (
    ' --ssl-ca={0}/cacert.pem'
    ' --ssl-cert={0}/server-cert.pem'
    ' --ssl-key={0}/server-key.pem'
).format(os.path.abspath(STD_DATA_PATH)).replace('\\', '/')

SSL_OPTS_UTIL = (
    ' --ssl-ca={0}/cacert.pem'
    ' --ssl-cert={0}/client-cert.pem'
    ' --ssl-key={0}/client-key.pem'
)

MYSQLD_SSL = (
    '"--log-bin=mysql-bin --report-host=localhost '
    '--bind-address=:: --master-info-repository=table {ssl_opts} "'
).format(ssl_opts=SSL_OPTS)

CREATE_SSL_USER = ("GRANT ALL PRIVILEGES ON *.* TO '{0}'@'localhost' "
                   "IDENTIFIED BY '{1}' REQUIRE SSL".format(ssl_user,
                                                            ssl_pass))

CREATE_SSL_USER_2 = ("GRANT ALL PRIVILEGES ON *.* TO '{0}'@'127.0.0.1' "
                     "IDENTIFIED BY '{1}' REQUIRE SSL".format(ssl_user,
                                                              ssl_pass))


def ssl_server_opts(std_data_path=STD_DATA_PATH):
    """Formats the server ssl options with the given path.

    std_data_path[in]    The path where the ssl certificates are located.
                         (Default is './std_data/ssl_certs/')

    Returns a string with the server ssl-ca, ssl-cert and ssl-key options and
    theirs respective values.
    """
    return SSL_OPTS.format(os.path.abspath(std_data_path)).replace('\\', '/')


def ssl_util_opts(std_data_path=STD_DATA_PATH):
    """Formats the ssl util/client options with the given path.

    std_data_path[in]    The path where the ssl certificates are located.
                         (Default is './std_data/ssl_certs/')

    Returns a string with the util/client ssl-ca, ssl-cert and ssl-key options
    and theirs respective values.
    """
    return SSL_OPTS_UTIL.format(os.path.abspath(std_data_path)).replace('\\',
                                                                        '/')


# Second ssl
ssl_user_b = "root_ssl_b"

ssl_pass_b = "root_ssl_b"

SSL_CA_B = "{0}/utils-cacert.pem"

SSL_CERT_B = "{0}/utils-server-cert.pem"

SSL_KEY_B = "{0}/utils-server-key.pem"

ssl_c_ca_b = os.path.abspath(SSL_CA_B.format(STD_DATA_PATH)
                             ).replace('\\', '/')

ssl_c_cert_b = os.path.abspath(SSL_CERT_B.format(STD_DATA_PATH)
                               ).replace('\\', '/')

ssl_c_key_b = os.path.abspath(SSL_KEY_B.format(STD_DATA_PATH)
                              ).replace('\\', '/')

SSL_OPTS_B = (
    ' --ssl-ca={0}/utils-cacert.pem'
    ' --ssl-cert={0}/utils-server-cert.pem'
    ' --ssl-key={0}/utils-server-key.pem'
).format(os.path.abspath(STD_DATA_PATH)).replace('\\', '/')

SSL_OPTS_UTIL_B = (
    ' --ssl-ca={0}/utils-cacert.pem'
    ' --ssl-cert={0}/utils-client-cert.pem'
    ' --ssl-key={0}/utils-client-key.pem'
)

MYSQLD_SSL_B = (
    '"--log-bin=mysql-bin --report-host=localhost '
    '--bind-address=:: --master-info-repository=table {ssl_opts} "'
).format(ssl_opts=SSL_OPTS_B)

CREATE_SSL_USER_B = ("GRANT ALL PRIVILEGES ON *.* TO '{0}'@'localhost' "
                     "IDENTIFIED BY '{1}' REQUIRE SSL"
                     ).format(ssl_user_b, ssl_pass_b)

CREATE_SSL_USER_2_B = ("GRANT ALL PRIVILEGES ON *.* TO '{0}'@'127.0.0.1' "
                       "IDENTIFIED BY '{1}' REQUIRE SSL"
                       ).format(ssl_user_b, ssl_pass_b)


def ssl_server_opts_b(std_data_path=STD_DATA_PATH):
    """Formats the server ssl options with the given path.

    std_data_path[in]    The path where the ssl certificates are located.
                         (Default is './std_data/ssl_certs/')

    Returns a string with the server ssl-ca, ssl-cert and ssl-key options and
    theirs respective values.
    """
    return SSL_OPTS_B.format(os.path.abspath(std_data_path)).replace('\\', '/')


def ssl_util_opts_b(std_data_path=STD_DATA_PATH):
    """Formats the ssl util/client options with the given path.

    std_data_path[in]    The path where the ssl certificates are located.
                         (Default is './std_data/ssl_certs/')

    Returns a string with the util/client ssl-ca, ssl-cert and ssl-key options
    and theirs respective values.
    """
    return SSL_OPTS_UTIL_B.format(os.path.abspath(std_data_path)).replace('\\',
                                                                          '/')
