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
"""Implements the Distutils command 'sdist'

Implements the Distutils command 'sdist_com' 
"""

import sys
import os

from distutils import log
from distutils.dir_util import (create_tree, remove_tree, mkpath, copy_tree,
                                remove_tree)
from distutils.file_util import copy_file, move_file
from distutils.sysconfig import get_python_version
from distutils.command.sdist import sdist
from distutils.filelist import FileList

from support.distribution.utils import get_dist_name
from support.distribution import commercial

class GenericSourceGPL(sdist):
    """Create a generic source GNU GPLv2 distribution

    This class generates a generic source distribution GNU GPLv2 licensed.
    Generic means that it will contain both Python v2 and Python v3 code.

    GenericSourceGPL is meant to replace distutils.sdist.
    """
    description = 'create a generic source distribution (Python 2.x and 3.x)'
    user_options = [
        ('prune', None,
         "specifically exclude files/directories that should not be "
         "distributed (build tree, RCS/CVS dirs, etc.) "
         "[default; disable with --no-prune]"),
        ('no-prune', None,
         "don't automatically exclude anything"),
        ('formats=', None,
         "formats for source distribution (comma-separated list)"),
        ('keep-temp', 'k',
         "keep the distribution tree around after creating " +
         "archive file(s)"),
        ('dist-dir=', 'd',
         "directory to put the source distribution archive(s) in "
         "[default: dist]"),
        ('owner=', 'u',
         "Owner name used when creating a tar file [default: current user]"),
        ('group=', 'g',
         "Group name used when creating a tar file [default: current group]"),
        ('tag=', 't',
         "Adds a tag name after the release version"),
        ]

    boolean_options = ['prune',
                       'force-manifest',
                       'keep-temp']

    negative_opt = {'no-prune': 'prune' }

    default_format = {'posix': 'gztar',
                      'nt': 'zip' }

    def initialize_options(self):
        self.tag = ''
        self.owner = None
        self.group = None
        sdist.initialize_options(self)

    def copy_extra_files(self, base_dir):
        extra_files = [
        ]
        for src, dest in extra_files:
            self.copy_file(src, dest)

    def rename_info_files(self, base_dir):
        info_files = [
            ('README.txt', 'README_Utilities.txt'),
            ('CHANGES.txt', 'CHANGES_Utilities.txt')
        ]
        for src, dest in info_files:
            self.move_file(os.path.join(base_dir, src),
                           os.path.join(base_dir, dest))

    def make_release_tree(self, base_dir, files):
        self.mkpath(base_dir)
        create_tree(base_dir, files, dry_run=self.dry_run)

        msg = "copying files to %s..." % base_dir

        if not files:
            log.warn("no files to distribute -- empty manifest?")
        else:
            log.info(msg)
        for file in files:
            if not os.path.isfile(file):
                log.warn("'%s' not a regular file -- skipping" % file)
            else:
                dest = os.path.join(base_dir, file)
                self.copy_file(file, dest)

        self.copy_extra_files(base_dir)

        self.rename_info_files(base_dir)

        self.distribution.metadata.write_pkg_info(base_dir)

    def make_distribution(self):
        """Create the source distribution(s).  First, we create the release
        tree with 'make_release_tree()'; then, we create all required
        archive files (according to 'self.formats') from the release tree.
        Finally, we clean up by blowing away the release tree (unless
        'self.keep_temp' is true).  The list of archive files created is
        stored so it can be retrieved later by 'get_archive_files()'.
        """
        # Don't warn about missing meta-data here -- should be (and is!)
        # done elsewhere.
        base_dir = self.distribution.get_fullname()
        base_name = os.path.join(self.dist_dir, base_dir)

        self.make_release_tree(base_dir, self.filelist.files)
        archive_files = []              # remember names of files we create
        # tar archive must be created last to avoid overwrite and remove
        if 'tar' in self.formats:
            self.formats.append(self.formats.pop(self.formats.index('tar')))

        if self.tag:
            self.tag = "-{0}".format(self.tag)

        for fmt in self.formats:
            dist_ver = self.distribution.metadata.version
            newname = base_name.replace(
                          '{0}'.format(dist_ver),
                          '{0}{1}'.format(dist_ver, self.tag)
                      )
            file = self.make_archive(newname, fmt, base_dir=base_dir)

            archive_files.append(file)
            self.distribution.dist_files.append(('sdist', '', file))

        self.archive_files = archive_files

        if not self.keep_temp:
            remove_tree(base_dir, dry_run=self.dry_run)

    def run(self):
        self.distribution.data_files = None
        self.filelist = FileList()
        for cmd_name in self.get_sub_commands():
            self.run_command(cmd_name)

        self.get_file_list()
        self.make_distribution()

class SourceGPL(sdist):
    """Create source GNU GPLv2 distribution for specific Python version

    This class generates a source distribution GNU GPLv2 licensed for the
    Python version that is used. SourceGPL is used by other commands to
    generate RPM or other packages.
    """
    description = 'create a source distribution for Python v%s.x' % (
        get_python_version()[0])
    user_options = [
        ('bdist-dir=', 'd',
         "temporary directory for creating the distribution"),
        ('keep-temp', 'k',
         "keep the pseudo-installation tree around after " +
         "creating the distribution archive"),
        ('dist-dir=', 'd',
         "directory to put final built distributions in"),
        ('tag=', 't',
         "Adds a tag name after the release version"),
    ]

    boolean_options = [
        'keep-temp',
    ]
    
    negative_opt = []

    def initialize_options (self):
        """Initialize the options"""
        self.bdist_dir = None
        self.keep_temp = 0
        self.dist_dir = None
        self.plat_name = ''
        self.tag = None

    def finalize_options(self):
        """Finalize the options"""
        if self.bdist_dir is None:
            bdist_base = self.get_finalized_command('bdist').bdist_base
            self.bdist_dir = os.path.join(bdist_base, 'dist')

        self.set_undefined_options('bdist',
                                   ('dist_dir', 'dist_dir'),)
        
        python_version = get_python_version()
        pyver = python_version[0:2]
        
        # Change classifiers
        new_classifiers = []
        for classifier in self.distribution.metadata.classifiers:
            if (classifier.startswith("Programming Language ::")
                and (pyver not in classifier)):
                log.info("removing classifier %s" % classifier)
                continue
            new_classifiers.append(classifier)
        self.distribution.metadata.classifiers = new_classifiers

        license = open('README', 'r').read()
        self.distribution.metadata.long_description += "\n" + license
        if self.tag:
            self.tag = "-{0}".format(self.tag)

    def run(self):
        """Run the distutils command"""
        log.info("installing library code to %s" % self.bdist_dir)
        
        self.dist_name = get_dist_name(self.distribution,
                                       source_only_dist=True,
                                       python_version=get_python_version()[0])
        self.dist_target = os.path.join(self.dist_dir, self.dist_name)
        log.info("distribution will be available as '%s'" % self.dist_target)
        
        # build command: just to get the build_base
        cmdbuild = self.get_finalized_command("build")
        self.build_base = cmdbuild.build_base
        
        # install command
        install = self.reinitialize_command('install_lib',
                                            reinit_subcommands=1)
        install.compile = False
        install.warn_dir = 0
        install.install_dir = self.bdist_dir
        
        log.info("installing to %s" % self.bdist_dir)
        self.run_command('install_lib')

        # install extra files
        extra_files = {
            # No extra files
        }
        for src, dest in extra_files.items():
            self.copy_file(src, dest)
        
        # install_egg_info command
        cmd_egginfo = self.get_finalized_command('install_egg_info')
        cmd_egginfo.install_dir = self.bdist_dir
        self.run_command('install_egg_info')
        # we need the py2.x converted to py2 in the filename
        old_egginfo = cmd_egginfo.get_outputs()[0]
        new_egginfo = old_egginfo.replace(
            '-py' + sys.version[:3],
            '-py' + get_python_version()[0])
        move_file(old_egginfo, new_egginfo)
        
        # create distribution
        info_files = [
            ('README.txt', 'README_Utilities.txt'),
            ('LICENSE.txt', 'LICENSE.txt'),
            ('CHANGES.txt', 'CHANGES_Utilities.txt'),
            ('README_fabric.txt', 'README_fabric.txt'),
            ('CHANGES_fabric.txt', 'CHANGES_fabric.txt')
        ]
        copy_tree(self.bdist_dir, self.dist_target)
        pkg_info = mkpath(os.path.join(self.dist_target))
        for src, dst in info_files:
            if os.path.exists(src):
                if dst is None:
                    copy_file(src, self.dist_target)
                else:
                    copy_file(src, os.path.join(self.dist_target, dst))
            else:
                log.info("File not found: {0}".format(src))

        if not self.keep_temp:
            remove_tree(self.build_base, dry_run=self.dry_run)


class SourceCommercial(sdist):
    """Create commercial source distribution
    """
    description = 'create a commercial source distribution'

    def initialize_options (self):
        sdist.initialize_options(self)

    def finalize_options(self):
        def _get_fullname():
            return "%s-commercial-%s" % (
                self.distribution.get_name(), self.distribution.get_version())

        self.distribution.get_fullname = _get_fullname
        sdist.finalize_options(self)

    def _replace_gpl(self, basedir, filelist):
        """Replace the GPL license with Commercial license
        """
        ignore = [
            'ChangeLog', 'README.txt', 'setup.cfg', 'LICENSE.txt',
        ]

        for afile in filelist:
            fullpath = os.path.join(basedir, afile)
            if (os.path.basename(afile) == '__init__.py' and
                os.path.getsize(afile) == 0):
                continue
            if os.path.splitext(afile)[1] == '.pem':
                continue
            if afile.startswith('docs/'):
                continue
            if afile not in ignore:
                commercial.remove_gpl(fullpath, dry_run=self.dry_run)

    def _prepare_commercial(self, pkgdir, filelist):
        to_remove = [
            'COPYING', 'README', 'CHANGES.txt', 'LICENSE_com.txt',
            'README_com.txt'
            ]
        for afile in filelist:
            if afile in to_remove:
                os.unlink(os.path.join(pkgdir, afile))
                filelist.remove(afile)
                log.info("removing from distribution '%s'" % afile)

        comm_path = os.path.join('support', 'commercial_docs')
        copy_file(os.path.join(comm_path, 'LICENSE_com.txt'),
                  os.path.join(pkgdir, 'LICENSE_com.txt'))
        filelist.append('LICENSE_com.txt')
        copy_file(os.path.join(comm_path, 'README_com.txt'),
                  os.path.join(pkgdir, 'README_com.txt'))
        filelist.append('README_com.txt')

#        log.info("setting license information in version.py")
#        loc_version_py = os.path.join(pkgdir, 'version.py')
#        version_py = open(loc_version_py, 'r').readlines()
#        for (nr, line) in enumerate(version_py):
#            if line.startswith('LICENSE'):
#                version_py[nr] = 'LICENSE = "Commercial"\n'
#        fp = open(loc_version_py, 'w')
#        fp.write(''.join(version_py))
#        fp.close()

    def add_docs(self, docpath):
        mkpath(docpath)
        docfiles = [
            #No docs to at yet.
        ]

        for docfile in docfiles:
            self.copy_file(docfile, docpath)
            self.filelist.files.append(docfile)

    def make_release_tree(self, base_dir, files):
        """Create the directory tree becoming the distribution archive

        This method differs from the original forcing making a copy
        of the files instead of hard linking.
        """
        self.mkpath(base_dir)
        create_tree(base_dir, files, dry_run=self.dry_run)

        msg = "copying files to %s..." % base_dir
        log.info(msg)

        for afile in files:
            if not os.path.isfile(afile):
                log.warn("'%s' not a regular file -- skipping" % afile)
            else:
                dest = os.path.join(base_dir, afile)
                self.copy_file(afile, dest)

    def make_distribution(self):
        """Create the commercial source distributions
        """
        dist_name = self.distribution.get_fullname()
        pkg_dir = os.path.join(self.dist_dir, dist_name)

        self.add_docs(os.path.join(pkg_dir, 'docs'))

        self.make_release_tree(pkg_dir, self.filelist.files)
        self._prepare_commercial(pkg_dir, self.filelist.files)
        self._replace_gpl(pkg_dir, self.filelist.files)
        self.archive_files = []

        if 'tar' in self.formats:
            self.formats.append(self.formats.pop(self.formats.index('tar')))

        for fmt in self.formats:
            dist_ver = self.distribution.metadata.version
            newname = pkg_dir.replace(
                          '{0}'.format(dist_ver),
                          '{0}{1}'.format(dist_ver, self.tag)
                      )
            afile = self.make_archive(newname, fmt,
                                      root_dir=self.dist_dir,
                                      base_dir=dist_name)
            self.archive_files.append(afile)
            self.distribution.dist_files.append(('sdist_com', '', afile))

        if not self.keep_temp:
            remove_tree(pkg_dir, dry_run=self.dry_run)

    def run(self):
        sdist.run(self)
