#!/bin/sh
#
# Copyright (c) 2015, Oracle and/or its affiliates. All rights reserved.
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
# The script creates the SSL certificates used to setup a MySQL Server
# instance and connect to it on MySQL Utilities tests.
#
# Usage:
#  $ sh generate.sh <certs-prefix>
#

OU="MySQL-Utilities"
PREFIX=utils
DESTDIR=$PREFIX"-certs"
DAYS=3653

OPENSSL=`which openssl`
if [ $? -ne 0 ]; then
    echo "openssl was not found in your PATH."
    exit 1
fi

# Certificate files prefix
if [ "$1" != "" ]; then
    PREFIX=$1
    DESTDIR=$1"-certs"
else
    echo "Prefix: "$PREFIX" will be used on certificate file names."
fi

# Destination folder
if [ ! -d $DESTDIR ]; then
    echo "Creatring destination folder "$DESTDIR"."
    mkdir $DESTDIR
fi
if [ ! -d $DESTDIR ]; then
    echo "Destination folder "$DESTDIR" could not be created."
    exit 2
fi

echo
echo "Creating the CA Certificate"
echo
$OPENSSL genrsa 2048 > $DESTDIR/$PREFIX-ca-key.pem
if [ $? -ne 0 ]; then
    exit 3
fi
SUBJ="/OU=$OU Root CA/CN=MySQLUtils Root CA"
$OPENSSL req -batch -new -x509 -nodes -days $DAYS -subj "$SUBJ" \
    -key $DESTDIR/$PREFIX-ca-key.pem -out $DESTDIR/$PREFIX-cacert.pem
if [ $? -ne 0 ]; then
    exit 3
fi

# MySQL Server Certificate: create, remove passphrase, sign it

echo "Creating the Server Certificate"

SUBJ="/OU=$OU Server Cert/CN=localhost"
$OPENSSL req -batch -newkey rsa:2048 -days $DAYS -nodes -subj "$SUBJ" \
    -keyout $DESTDIR/$PREFIX-server-key.pem -out $DESTDIR/$PREFIX-server-req.pem
if [ $? -ne 0 ]; then
    exit 3
fi
$OPENSSL rsa -in $DESTDIR/$PREFIX-server-key.pem \
    -out $DESTDIR/$PREFIX-server-key.pem
if [ $? -ne 0 ]; then
    exit 3
fi
$OPENSSL x509 -req -in $DESTDIR/$PREFIX-server-req.pem -days $DAYS \
    -CA $DESTDIR/$PREFIX-cacert.pem -CAkey $DESTDIR/$PREFIX-ca-key.pem \
    -set_serial 01 -out $DESTDIR/$PREFIX-server-cert.pem
if [ $? -ne 0 ]; then
    exit 3
fi

# MySQL Client Certificate: generate, remove passphase, sign
echo
echo "Generating Client Certificate"
echo
SUBJ="/OU=$OU Client Cert/CN=localhost"
$OPENSSL req -batch -newkey rsa:2048 -days $DAYS -nodes -subj "$SUBJ" \
    -keyout $DESTDIR/$PREFIX-client-key.pem -out $DESTDIR/$PREFIX-client_req.pem
if [ $? -ne 0 ]; then
    exit 3
fi
$OPENSSL rsa -in $DESTDIR/$PREFIX-client-key.pem \
    -out $DESTDIR/$PREFIX-client-key.pem
if [ $? -ne 0 ]; then
    exit 3
fi
$OPENSSL x509 -req -in $DESTDIR/$PREFIX-client_req.pem -days $DAYS \
    -CA $DESTDIR/$PREFIX-cacert.pem -CAkey $DESTDIR/$PREFIX-ca-key.pem \
    -set_serial 01 -out $DESTDIR/$PREFIX-client-cert.pem
if [ $? -ne 0 ]; then
    exit 3
fi
$OPENSSL verify -CAfile $DESTDIR/$PREFIX-cacert.pem \
    $DESTDIR/$PREFIX-server-cert.pem $DESTDIR/$PREFIX-client-cert.pem
if [ $? -ne 0 ]; then
    exit 3
fi


# Clean up
echo
echo "Cleaning up"
echo
(cd $DESTDIR; rm $PREFIX-server-req.pem $PREFIX-client_req.pem)

