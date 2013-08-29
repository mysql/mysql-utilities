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
"""Implements the Distutils command 'bdist_com'

Implements the Distutils command 'bdist_com' which creates a built
commercial distribution into a folder.
"""

import os
from distutils import log, archive_util
from distutils.util import byte_compile
from distutils.dir_util import remove_tree, mkpath, copy_tree
from distutils.errors import DistutilsOptionError
from distutils.file_util import copy_file
from distutils.sysconfig import get_python_version
from distutils.command.bdist import bdist
from distutils.command.sdist import show_formats

from support.distribution.utils import get_dist_name
from support.distribution import commercial

class BuiltCommercial(bdist):
    """Create a Built Commercial distribution"""
    description = 'create a commercial built distribution'
    user_options = [
        ('bdist-dir=', 'd',
         "temporary directory for creating the distribution"),
        ('keep-temp', 'k',
         "keep the pseudo-installation tree around after " +
         "creating the distribution archive"),
        ('dist-dir=', 'd',
         "directory to put final built distributions in"),
        ('include-sources=', 'i',
         "exclude sources built distribution (default: True)"),
        ('formats=', None,
         "formats for source distribution (comma-separated list)"),
        ('hide-pyver', 'h',
         "do not add the python version to the package name"),
    ]

    boolean_options = [
        'keep-temp', 'include-sources', 'hide_pyver'
    ]

    help_options = [
        ('help-formats', None,
         "list available distribution formats", show_formats)
        ]

    def initialize_options (self):
        """Initialize the options"""
        self.bdist_dir = None
        self.keep_temp = 0
        self.hide_pyver = 0
        self.dist_dir = None
        self.include_sources = False
        self.plat_name = ''
        self.formats = None
        self.archive_files = None

    def finalize_options(self):
        """Finalize the options"""
        if self.bdist_dir is None:
            bdist_base = self.get_finalized_command('bdist').bdist_base
            self.bdist_dir = os.path.join(bdist_base, 'dist')

        self.set_undefined_options('bdist',
                                   ('dist_dir', 'dist_dir'),
                                   ('plat_name', 'plat_name'),)

        self.ensure_string_list('formats')
        if self.formats is None:
            log.info("No format was specified, with format option, resulting "
                     "build will remain in folder specified with dist-dir "
                     "option or 'dist' if was not specified.")
            self.formats = []

        bad_format = archive_util.check_archive_formats(self.formats)
        if bad_format:
            raise DistutilsOptionError, \
                  "unknown archive format '%s'" % bad_format
        
        self.dist_name = get_dist_name(
            self.distribution,
            source_only_dist=self.include_sources,
            # Hide python version for package name
            hide_pyver=self.hide_pyver,
            commercial=True)
        
        commercial_license = 'Other/Proprietary License'
        self.distribution.metadata.license = commercial_license
        
        python_version = get_python_version()
        if self.include_sources:
            pyver = python_version[0:2]
        else:
            pyver = python_version
        
        # Change classifiers
        new_classifiers = []
        for classifier in self.distribution.metadata.classifiers:
            if classifier.startswith("License ::"):
                classifier = "License :: " + commercial_license
            elif (classifier.startswith("Programming Language ::")
                and (pyver not in classifier)):
                log.info("removing classifier %s" % classifier)
                continue
            new_classifiers.append(classifier)
        self.distribution.metadata.classifiers = new_classifiers
        self.distribution.metadata.long_description = (
            commercial.COMMERCIAL_LICENSE_NOTICE)

    def _remove_sources(self):
        """Remove Python source files from the build directory"""
        log.info("_remove_sources")
        for base, dirs, files in os.walk(self.bdist_dir):
            for filename in files:
                if filename.endswith('.py'):
                    filepath = os.path.join(base, filename)
                    log.info("removing source '%s'", filepath)
                    os.unlink(filepath)

    def add_docs(self, docpath):
        mkpath(docpath)
        copy_tree('docs', docpath)

    def _write_setuppy(self):
        content = commercial.COMMERCIAL_SETUP_PY.format(**{
            'name': self.distribution.metadata.name,
            'version': self.distribution.metadata.version,
            'description': self.distribution.metadata.description,
            'long_description': self.distribution.metadata.long_description,
            'author': self.distribution.metadata.author,
            'author_email': self.distribution.metadata.author_email,
            'license': self.distribution.metadata.license,
            'keywords': ' '.join(self.distribution.metadata.keywords),
            'url': self.distribution.metadata.url,
            'download_url': self.distribution.metadata.download_url,
            'classifiers': self.distribution.metadata.classifiers,
            })

        fp = open(os.path.join(os.path.join(self.dist_target), 'setup.py'),
                  'w')
        fp.write(content)
        fp.close()

    def _copy_from_pycache(self, start_dir):
        for base, dirs, files in os.walk(start_dir):
            for filename in files:
                if filename.endswith('.pyc'):
                    filepath = os.path.join(base, filename)
                    new_name = filename.split('.')[0] + '.pyc'
                    os.rename(filepath, os.path.join(base, '..', new_name))

        for base, dirs, files in os.walk(start_dir):
            if base.endswith('__pycache__'):
                os.rmdir(base)

    def run(self):
        """Run the distutils command"""
        log.info("installing library code to %s" % self.bdist_dir)
        to_compile = []
        self.archive_files = []

        self.dist_target = os.path.join(self.dist_dir, self.dist_name)
        log.info("distribution will be available as '%s'" % self.dist_target)

        # build command: just to get the build_base
        cmdbuild = self.get_finalized_command("build")
        self.build_base = cmdbuild.build_base

        # install libs
        install = self.reinitialize_command('install_lib',
                                            reinit_subcommands=1)
        install.compile = False
        install.warn_dir = 0
        install.install_dir = self.bdist_dir

        log.info("installing to %s" % self.bdist_dir)
        self.run_command('install_lib')
        log.info('install_lib finish')
        # install extra files

        extra_files = {
            # no extra files at the moment
        }
        for src, dest in extra_files.items():
            self.copy_file(src, dest)

        installed_files = install.get_outputs()

        #install MAN pages
        install_man = self.reinitialize_command('install_man',
                                                reinit_subcommands=1)
        install_man.root = self.bdist_dir # + "/usr/bin/"

        log.info("installing to %s" % self.bdist_dir)
        self.run_command('install_man')
        log.info('install_man finish')

        #installing scripts
        log.info('===== installing script =====')
        install_scripts = self.reinitialize_command('install_scripts',
                                                     reinit_subcommands=1)
        #install_scripts.root = self.bdist_dir # + "/usr/bin/"
        #install_scripts.build_dir = self.bdist_dir
        scripts_instal_dir = os.path.join(self.bdist_dir, "usr", "bin") #scripts_dir
        install_scripts.install_dir = scripts_instal_dir 
        #install_scripts.get_outputs()
        
        log.info("installing to %s" % scripts_instal_dir)
        self.run_command('install_scripts')
        log.info('install_scripts finish')

        if not os.path.exists(scripts_instal_dir):
            log.error("scripts not found at {0}".format(self.dist_target))
        else:
            installed_sripts = [os.path.join(scripts_instal_dir, script)
                                for script in os.listdir(scripts_instal_dir)]
            installed_files.extend(installed_sripts)
        log.debug("installed_scripts {0}".format(installed_sripts))

        # install_egg_info command
        cmd_egginfo = self.reinitialize_command('install_egg_info',
                                                reinit_subcommands=1)
        cmd_egginfo.install_dir = self.bdist_dir
        self.run_command('install_egg_info')

        #installed_files.append(extra_files['version.py'])
        log.debug("bdist_dir {0}".format(self.bdist_dir))
        # remove the GPL license
        ignore = [
            os.path.join(self.bdist_dir,
                         os.path.join('mysql','__init__.py')),
            #os.path.join(self.bdist_dir,
            #             os.path.join('mysql', 'utilities', '__init__.py')),
            os.path.join(self.bdist_dir,
                         os.path.join('mysql', 'utilities', 'command',
                                      '__init__.py')),
            os.path.join(self.bdist_dir,
                         os.path.join('mysql', 'utilities', 'common',
                                      '__init__.py')),
            cmd_egginfo.target,
        ]
        for pyfile in installed_files:
            if pyfile not in ignore and not 'connector' in pyfile:
                commercial.remove_gpl(pyfile, dry_run=self.dry_run)

        log.info("setting copyright notice in utilities __init__")
        if os.name == 'nt':
            commercial.remove_full_gpl_cr(os.path.curdir, self.dry_run)
        else:
            commercial.remove_full_gpl_cr(self.bdist_dir, self.dry_run)

        # compile and remove sources
        if not self.include_sources:
            files_to_compile = [file for file in installed_files
                                if not file.startswith(scripts_instal_dir)]
            byte_compile(files_to_compile, optimize=0,
                         force=True, prefix=install.install_dir)
            self._remove_sources()
            if get_python_version().startswith('3'):
                self._copy_from_pycache(os.path.join(self.bdist_dir, 'mysql'))

        # create distribution
        comm_path = os.path.join('support', 'commercial_docs')
        info_files = [
            (os.path.join(comm_path, 'README_com.txt'), 'README_com.txt'),
            (os.path.join(comm_path, 'LICENSE_com.txt'), 'LICENSE_com.txt')
        ]
        copy_tree(self.bdist_dir, self.dist_target)
        pkg_info = mkpath(os.path.join(self.dist_target))
        for src, dst in info_files:
            if dst is None:
                copy_file(src, self.dist_target)
            else:
                copy_file(src, os.path.join(self.dist_target, dst))

        self.add_docs(os.path.join(self.dist_target, 'docs'))

        self._write_setuppy()

        if 'tar' in self.formats:
            self.formats.append(self.formats.pop(self.formats.index('tar')))

        log.info("specified formats: {0}".format(self.formats))
        for fmt in self.formats:
            log.debug("dist_target {0}".format(self.dist_target))
            log.debug("bdist_dir {0}".format(self.bdist_dir))
            log.debug("dist_dir {0}".format(self.dist_dir))
            log.debug("dist_name {0}".format(self.dist_name))

            afile = self.make_archive(self.dist_target, fmt,
                                      root_dir=self.dist_dir,
                                      base_dir=self.dist_name)
            self.archive_files.append(afile)
            self.distribution.dist_files.append(('bdist_com', '', afile))

        if not self.keep_temp and self.formats:
            log.info("Removing temp: {0}".format(self.dist_target))
            remove_tree(self.dist_target, dry_run=self.dry_run)

def get_archive_files(self):
        """Return the list of archive files created when the command
        was run, or None if the command hasn't run yet.
        """
        return self.archive_files

