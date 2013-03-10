#!/usr/bin/env python
#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
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
"""Script for downloading manuals

This scripts downloads the manuals from the given source.
Usage:
   python support/scripts/download_manuals.py <URL>

The location specified by <URL> should contain the same files as found
in the docs/ folder.
The downloaded manuals will replace the placeholders in the docs/ folder
and make it ready for packaging.

Note that this script is only useful internally at Oracle.
"""

from __future__ import print_function

import sys
import os
import urllib2
from optparse import OptionParser
import logging

logger = logging.getLogger("utilities_manuals")

# This script should run in the root source of MySQL Utilities
_CHECK_FILES = [
    os.path.exists('mysql'),
    os.path.exists('docs/man'),
    os.path.exists('support/scripts'),
    os.path.exists('support/MSWindows'),
    os.path.isfile('setup.py'),
    os.path.isfile('info.py')]
if not all(_CHECK_FILES):
    sys.stderr.write("This scripts needs to be executed from the root of the "
                     "MySQL Utilities source.")
    sys.exit(1)

# Add root of source to PYTHONPATH
sys.path.insert(0, os.getcwd())

def validate_url(url):
    """Validates the given URL"""
    try:
        urllib2.urlopen(url)
    except urllib2.HTTPError as err:
        print("URL Validation failed: {errmsg}".format(errmsg=err))
        sys.exit(1)

    # Check some files and folders
    subs = ['/man/', '/man-gpl/']
    for sub in subs:
        try:
            urllib2.urlopen(url + sub)
        except urllib2.HTTPError as err:
            print("URL Validation failed on '{checked}': {errmsg}".format(
                checked=sub, errmsg=err))
            sys.exit(1)

    print("URL validated")

def download_manpages(url, commercial=False):
    """Download manual pages

    The url is a valid URL which has either /man or /man-gpl as
    subfolders. When the commercial argument is set to True, the
    non-GPL manual pages will be downloaded.
    """
    if commercial:
        url = url + '/man/'
    else:
        url = url + '/man-gpl/'

    # Get manuals we need to download
    mans = os.listdir('docs/man')
    for man in mans:
        try:
            furl = urllib2.urlopen(url + man)
        except urllib2.HTTPError as err:
            print("Failed downloading {man}: {errmsg}".format(
                man=man, errmsg=err))
            sys.exit(1)
        
        # Small files, read and write all at once
        try:
            fp = open(os.path.join('docs/man', man), 'wb')
            fp.write(furl.read())
            fp.close()
        except (urllib2.HTTPError, os.error) as err:
            print("Failed downloading {man}: {errmsg}".format(
                man=man, errmsg=err))
            sys.exit(1)
        print("Downloaded {man}".format(man=man))

def main():
    """Main"""
    optparser = OptionParser()
    optparser.set_usage("usage: %prog url")
    optparser.add_option('','--commercial', dest='commercial',
        action="store_true", default=False,
        help='Get manuals for non GPL packaging')
    (options, args) = optparser.parse_args()

    try:
        manual_url = args[0]
    except IndexError:
        print("URL missing")
        optparser.print_usage()
        sys.exit(1)
    print("Downloading manuals using URL {url}".format(url=manual_url))

    validate_url(manual_url)

    if options.commercial:
        print("Downloading non-GPL (commercial) manuals")
    else:
        print("Downloading GPL manuals")
    download_manpages(manual_url, commercial=options.commercial)

if __name__ == '__main__':
    main()
