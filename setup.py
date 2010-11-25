#!/usr/bin/python

# Boilerplate code to install setuptools if it is not installed
import ez_setup
ez_setup.use_setuptools()

# Keep the imports sorted (alphabetically) in each group. Makes
# merging easier.

import distutils.core
import glob
import os
import setuptools
import sys

import mysql.utilities

from info import META_INFO, INSTALL, COMMANDS

class install_man(distutils.core.Command):
    description = "install (Unix) manual pages"

    user_options = [
        ('install-base=', None, "base installation directory"),
        ('force', 'f', 'force installation (overwrite existing files)'),
        ('build-dir=', None, 'Build directory'),
        ('skip-build', None, "skip the build steps"),
    ]

    boolean_options = ['force']

    def initialize_options(self):
        self.install_base = None
        self.build_dir = None
        self.force = None
        self.skip_build = None

    def finalize_options(self):
        self.set_undefined_options('install',
                                   ('install_data', 'install_base'),
                                   ('force', 'force'),
                                   )
        self.set_undefined_options('build_sphinx',
                                   ('build_dir', 'build_dir'),
                                   )
        self.target_dir = os.path.join(self.install_base, 'man')
        self.source_dir = os.path.join(self.build_dir, 'man')

    def run(self):
        for man_file in self.get_outputs():
            man_dir = 'man' + os.path.splitext(man_file)[1][1:]
            man_page = os.path.basename(man_file)
            self.mkpath(man_dir)
            man_install = os.path.join(self.target_dir, man_dir, man_page)
            self.copy_file(man_file, man_install)

    def get_outputs(self):
        return glob.glob(os.path.join(self.source_dir, '*.[12345678]'))

# See if we have Sphinx installed, otherwise, just ignore building
# documentation.
try:
    import sphinx.setup_command
    from distutils.command.install import install

    class MyInstall(install):
        sub_commands = install.sub_commands + [
            ('install_man', lambda self: True),
            ]

    COMMANDS['cmdclass'].update({
            'install': MyInstall,
            'install_man': install_man,
            'build_man': sphinx.setup_command.BuildDoc,
            })

    COMMANDS.setdefault('options',{}).update({
            'build_man': { 'builder': 'man' },
            })
except ImportError:
    # TODO: install pre-generated manual pages
    pass                        # No Sphinx installed

ARGS = {
    'test_suite': 'tests.test_all',
}

ARGS.update(META_INFO)
ARGS.update(INSTALL)
ARGS.update(COMMANDS)
setuptools.setup(**ARGS)
