# Copyright (c) 2013, 2014, Oracle and/or its affiliates. All rights reserved.
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

"""This file contains python script to be used inside Jenkins and whose job is
to run the entire MUT test suite with different MySQL Server versions"""

import os
import urllib
import urllib2
import time
import platform
import sys
import shutil
import re
from support.jenkins.common import working_path

OS = {
    "Linux": {
        #"5.5":   ("daily-5.5",
        #           "binary-release-community_el6-x86-64bit_tar-gz"),
        "5.6":   ("daily-5.6",
                  "binary-release-advanced_el6-x86-64bit_tar-gz"),
        "trunk": ("daily-trunk",
                  "binary-release-advanced_el7-x86-64bit_tar-gz"),
    },
    "Windows": {
        #"5.5":   ("daily-5.5",
        #          "binary-release-community_windows-x86-64bit_zip"),
        "5.6":   ("daily-5.6",
                  "binary-release-advanced_windows-x86-64bit_zip"),
        "trunk": ("daily-trunk",
                  "binary-release-advanced_windows-x86-64bit_zip"),
    }
}

SPECIAL_GA_LINUX = {
    "5.7.5-m15": ("http://alvheim.se.oracle.com/trees/mysql/mysql-5.7.5-m15/"
                  "dist/packages/mysql-advanced-5.7.5-m15-"
                  "linux-glibc2.5-x86_64.tar.gz"),
    # Disabled until we get a better machine to run the tests
    # "5.6.8-rc": "http://alvheim.se.oracle.com/trees/mysql/mysql-5.6.8-rc/"
    #             "dist/packages/mysql-5.6.8-rc-linux2.6-x86_64.tar.gz",
    # "5.6.9-rc": "http://alvheim.se.oracle.com/trees/mysql/mysql-5.6.9-rc/"
    #             "dist/packages/mysql-5.6.9-rc-linux-glibc2.5-x86_64.tar.gz",
}

SPECIAL_GA_WIN = {
    "5.7.5-m15": ("http://alvheim.se.oracle.com/trees/mysql/mysql-5.7.5-m15/"
                  "dist/packages/mysql-advanced-5.7.5-m15-winx64.zip")
    # Disabled until we get a better machine to run the tests
    # "5.6.8-rc": "http://alvheim.se.oracle.com/trees/mysql/mysql-5.6.8-rc/"
    #             "dist/packages/mysql-5.6.8-rc-winx64.zip",
    # "5.6.9-rc": "http://alvheim.se.oracle.com/trees/mysql/mysql-5.6.9-rc/"
    #             "dist/packages/mysql-advanced-5.6.9-rc-winx64.zip",
}

GA_DIR_SUFFIX = "GA"
UPCOMING_DIR_SUFFIX = "UPCOMING"


def download_binary(uri, download_dir, filename):
    # download, try 3 times before error
    with working_path(download_dir):
        attempt = 1
        fname = os.path.join(download_dir, filename)
        while attempt <= 3:
            try:
                urllib.urlcleanup()
                print("Downloading {0} from {1}, attempt {2}".format(
                    fname, uri, attempt))
                urllib.urlretrieve(uri, fname)
                break
            except IOError:
                try:
                    os.remove(fname)
                except OSError:
                    pass
                attempt += 1
                # sleep for 5 minutes
                time.sleep(300)
        else:
            print("ERROR: Downloading '{0}' for OS '{1}' "
                  "FAILED".format(uri, platform.system()))
            sys.exit(1)


def _get_mysql_uri(version_name, os_name, advanced=True, get64bit=True):
    """Returns the specific uri to download the mysql version with the
    specified version_name or None if it cannot find it.

    version_name[in] string with the mysql version name.
    os_name[in]      string with the operating system name. Supports Linux and
                     Windows.
    advanced[in]     if True returns the uri for the advanced version, else
                     returns the uri for the normal version.
    get64bit[in]     if True returns the 64 bit package, else the 32bit.

    """
    os_name = os_name.lower()
    if os_name not in ['linux', 'windows']:
        raise ValueError("invalid os_name, supported values are 'Linux' or "
                         "'Windows'")
    uri = ("http://alvheim.se.oracle.com/trees/mysql/{0}/dist/"
           "packages".format(version_name))
    if os_name == 'windows':
        os_str = ''
        extension_str = re.escape('.zip')
        if get64bit:
            arch_str = 'winx64'
        else:
            arch_str = 'win32'
    else:
        os_str = 'linux'
        extension_str = re.escape('.tar.gz')
        if get64bit:
            arch_str = re.escape('x86_64')
        else:
            arch_str = 'i686'
    if advanced:
        version_str = re.escape("mysql-advanced-")
    else:
        version_str = re.escape("mysql-")

    #build pattern
    pattern_str = ('<a\shref="({0}(?:noinstall\-)?\d.*?{1}.*?'
                   '{2}(:?\-glibc\d+)?{3})">'.format(version_str, os_str,
                                                     arch_str, extension_str))
    #res =
    pattern = re.compile(pattern_str)
    for line in urllib.urlopen(uri):
        match = re.search(pattern, line)
        if match:
            return "{0}/{1}".format(uri, match.group(1))
    else:
        raise LookupError("Could not retrieve the download uri for version {0}"
                          "{1} on {2} for arch {3}".format(
                          version_name, ' advanced'*advanced, os_name,
                          arch_str))


def get_GA_binaries_uris(versions):
    """Returns a dict with the URIs to download each of the latest server
    version for each platform.

    versions[in]  list with the major versions that we want to download:
                  E.g if we want the download links for the latest 5.5 and 5.6
                  versions = ["5.5", "5.6"]
    """
    lines = urllib.urlopen("http://alvheim.se.oracle.com/trees/"
                           "mysql/").readlines()
    version_dict = dict((version, []) for version in versions)
    res_dict = {'Linux': {}, 'Windows': {}}

    re_patterns = {}
    # build pattern list
    for version in versions:
        re_patterns[version] = re.compile(
            '<a\shref="(mysql-({0}\.?\d*))/'.format(re.escape(version)))
    for line in lines:
        for version in versions:
            match = re.search(re_patterns[version], line)
            if match:
                version_dict[version].append((match.group(1), match.group(2)))

    # Now get the maximum version
    # Convert version string to ints to correctly get the maximum version
    max_func = lambda tpl: (map(int, tpl[1].split('.')), tpl[0])
    for version in versions:
        if version_dict[version]:
            version_dict[version] = max(version_dict[version], key=max_func)[0]
        else:
            print("Warning: No GA versions found for MySQL "
                  "{0}".format(version))
            del version_dict[version]
    # Build download uri for each OS and version
    for version, v_name in version_dict.iteritems():
        # Get the 64 bit advanced version for linux and windows
        try:
            download_uri_linux = _get_mysql_uri(v_name, 'linux')
            res_dict['Linux'][version_dict[version]] = download_uri_linux
        except LookupError as err:
            print(str(err))
        try:
            download_uri_windows = _get_mysql_uri(v_name, 'windows')
            res_dict['Windows'][version_dict[version]] = download_uri_windows
        except LookupError as err:
            print(str(err))
    return res_dict


def get_filename(uri):
    """Returns the archive filename looking at the url"""
    if not (uri.endswith(".zip") or uri.endswith(".tar.gz")):
        print("ERROR: '{0}' is not a valid URI".format(uri))
        sys.exit(1)
    # Break the url from the right on the first occurrence of mysql word
    fname = "mysql-{0}".format(uri.rsplit("mysql-")[-1])
    return fname


def get_latest_uris(os_dict):
    uri_list = []
    for _, info_tuple in os_dict.items():
        branch = info_tuple[0]
        product = info_tuple[1]
        # download, try 3 times before error
        attempt = 1
        while attempt <= 3:
            try:
                url = ("http://pb2.no.oracle.com/web.py?template=latest&"
                       "count=1&skip=50&branch={0}"
                       "&product={1}".format(branch, product))
                latest = urllib2.urlopen(url).read().strip()
                print("Getting URIs for OS '{1}' "
                      "(attempt: {2})".format(latest, platform.system(),
                                              attempt))
                url = latest.split(" ")[0]
                uri_list.append(url)
                break
            except IOError:
                attempt += 1
                # sleep for 5 minutes
                time.sleep(300)
        else:
            print("ERROR: Retrieving URIs for Operating System '{0}' "
                  "FAILED".format(platform.system()))
            sys.exit(1)

    return uri_list

if __name__ == "__main__":
    try:
        outdir = os.environ["BINARIES_HOME"]
    except KeyError:
        print("ERROR: Please set the BINARIES_HOME environment variable")
        sys.exit(1)
    try:
        os_dict = OS[platform.system()]
    except KeyError:
        print("There is no information regarding Operating System '{0}' "
              "in the hosts dict".format(platform.system()))
        sys.exit(1)

    # CLEANUP existing BINARIES
    outdir = os.path.normpath(outdir)
    parent_dir, _ = os.path.split(outdir)
    if os.path.isdir(parent_dir):
        try:
            shutil.rmtree(outdir)
        except OSError:
            print("ERROR: Failed to delete directory '{0}'".format(outdir))
        try:
            os.mkdir(outdir)
        except OSError:
            print("ERROR: Failed to create directory '{0}'".format(outdir))
            sys.exit(1)
    else:
        print("ERROR: '{0}' is not a valid path".format(outdir))

    uri_to_retrieve_pb = []
    uri_to_retrieve_ga = []
    uri_to_retrieve_pb.extend(get_latest_uris(os_dict))
    latest_ga_dict = get_GA_binaries_uris(['5.5', '5.6', '5.7'])
    if platform.system() == 'Windows':
        uri_to_retrieve_ga.extend(SPECIAL_GA_WIN.values())
        uri_to_retrieve_ga.extend(latest_ga_dict['Windows'].values())
    elif platform.system() == 'Linux':
        uri_to_retrieve_ga.extend(SPECIAL_GA_LINUX.values())
        uri_to_retrieve_ga.extend(latest_ga_dict['Linux'].values())
    else:
        print("ERROR: This operating system is not yet supported")

    # Get filename and retrieve it
    # Create directories to download upcoming and ga versions
    upcoming_dir = os.path.join(outdir, UPCOMING_DIR_SUFFIX)
    ga_dir = os.path.join(outdir, GA_DIR_SUFFIX)

    for directory in [ga_dir, upcoming_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory)

    # Download binaries
    for uri in uri_to_retrieve_pb:
        fname = get_filename(uri)
        download_binary(uri, upcoming_dir, fname)

    for uri in uri_to_retrieve_ga:
        fname = get_filename(uri)
        download_binary(uri, ga_dir, fname)