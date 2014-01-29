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
import socket
import platform
import sys
import shutil
from support.jenkins.common import working_path

HOSTS = {
    "blade03": {
        #"5.1":   ("mysql-5.1", "binary-max-linux-x86_64-tar-gz"),
        #"5.5":   ("daily-5.5",
        #           "binary-release-community_el6-x86-64bit_tar-gz"),
        "5.6":   ("daily-5.6",
                  "binary-release-advanced_el6-x86-64bit_tar-gz"),
        "trunk": ("daily-trunk",
                  "binary-release-advanced_el6-x86-64bit_tar-gz"),
    },
    "blade23": {
        #"5.1":   ("mysql-5.1",   "tree-max-win-x86_64-zip"),
        #"5.5":   ("daily-5.5",
        #          "binary-release-community_windows-x86-64bit_zip"),
        "5.6":   ("daily-5.6",
                  "binary-release-advanced_windows-x86-64bit_zip"),
        "trunk": ("daily-trunk",
                  "binary-release-advanced_windows-x86-64bit_zip"),
    }
}

LATEST_GA_LINUX = {
    "5.1.73": "http://alvheim.se.oracle.com/trees/mysql/mysql-5.1.73/dist/"
              "packages/mysql-advanced-5.1.73-linux-x86_64-glibc23.tar.gz",
    "5.5.35": "http://alvheim.se.oracle.com/trees/mysql/mysql-5.5.35/dist/"
              "packages/mysql-advanced-5.5.35-linux2.6-x86_64.tar.gz",
    "5.6.8-rc": "http://alvheim.se.oracle.com/trees/mysql/mysql-5.6.8-rc/dist/"
                "packages/mysql-5.6.8-rc-linux2.6-x86_64.tar.gz",
    "5.6.9-rc": "http://alvheim.se.oracle.com/trees/mysql/mysql-5.6.9-rc/dist/"
                "packages/mysql-5.6.9-rc-linux-glibc2.5-x86_64.tar.gz",
    "5.6.15": "http://alvheim.se.oracle.com/trees/mysql/mysql-5.6.15/dist/"
              "packages/mysql-advanced-5.6.15-linux-glibc2.5-x86_64.tar.gz",

}

LATEST_GA_WIN = {
    "5.1.73": "http://alvheim.se.oracle.com/trees/mysql/mysql-5.1.73/dist/"
              "packages/mysql-advanced-noinstall-5.1.73-winx64.zip",
    "5.5.35": "http://alvheim.se.oracle.com/trees/mysql/mysql-5.5.35/dist/"
              "packages/mysql-advanced-5.5.35-winx64.zip",
    "5.6.8-rc": "http://alvheim.se.oracle.com/trees/mysql/mysql-5.6.8-rc/dist/"
                "packages/mysql-5.6.8-rc-winx64.zip",
    "5.6.9-rc": "http://alvheim.se.oracle.com/trees/mysql/mysql-5.6.9-rc/dist/"
                "packages/mysql-advanced-5.6.9-rc-winx64.zip",
    "5.6.15": "http://alvheim.se.oracle.com/trees/mysql/mysql-5.6.15/dist/"
              "packages/mysql-advanced-5.6.15-winx64.zip",
}


def get_hostname():
    return socket.gethostname()


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
            print("ERROR: Downloading '{0}' for host '{1}' "
                  "FAILED".format(uri, get_hostname()))
            sys.exit(1)


def get_filename(uri):
    """Returns the archive filename looking at the url"""
    if not (uri.endswith(".zip") or uri.endswith(".tar.gz")):
        print("ERROR: '{0}' is not a valid URI".format(uri))
        sys.exit(1)
    # Break the url from the right on the first ocurrence of mysql word
    fname = "mysql-{0}".format(uri.rsplit("mysql-")[-1])
    return fname


def get_latest_uris(h_dict):
    uri_list = []
    for _, info_tuple in h_dict.items():
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
                print("Getting URIs for host '{1}' "
                      "(attempt: {2})".format(latest, get_hostname(), attempt))
                url = latest.split(" ")[0]
                uri_list.append(url)
                break
            except IOError:
                attempt += 1
                # sleep for 5 minutes
                time.sleep(300)
        else:
            print("ERROR: Retrieving URIs for host '{0}' "
                  "FAILED".format(get_hostname()))
            sys.exit(1)

    return uri_list

if __name__ == "__main__":
    hostname = get_hostname()
    try:
        outdir = os.environ["BINARIES_HOME"]
    except KeyError:
        print("ERROR: Please set the BINARIES_HOME environment variable")
        sys.exit(1)
    try:
        host_dict = HOSTS[hostname]
    except KeyError:
        print("There is no information regarding hostname '{0}' "
              "in the hosts dict".format(hostname))
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

    uri_to_retrieve = []
    uri_to_retrieve.extend(get_latest_uris(host_dict))
    if platform.system() == 'Windows':
        uri_to_retrieve.extend(LATEST_GA_WIN.values())
    elif platform.system() == 'Linux':
        uri_to_retrieve.extend(LATEST_GA_LINUX.values())
    else:
        print("ERROR: This operating system is not yet supported")
    # Get filename and retrieve it
    for uri in uri_to_retrieve:
        fname = get_filename(uri)
        download_binary(uri, outdir, fname)
