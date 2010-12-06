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

from info import META_INFO, INSTALL

COMMANDS = {
    'cmdclass': {
        },
    }

ARGS = {
    'test_suite': 'tests.test_all',
}

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
    # No Sphinx installed

    from distutils.command.install import install

    COMMANDS['cmdclass'].update({
            'install': install,
    })

class MyBuildScripts(distutils.command.build_scripts.build_scripts):
    """Class for providing a customized version of build_scripts.

    When ``run`` is called, this command class will:
    1. Create a copy of all ``.py`` files in the **scripts** option
       that does not have the ``.py`` extension.
    2. Replace the list in the **scripts** attribute with a list
       consisting of the script files with the ``.py`` extension
       removed.
    3. Call run method in `distutils.command.build_scripts`.
    4. Restore the scripts list to the old value, for other commands
       to use."""

    def run(self):
        from distutils import log
        if not self.scripts:
            return
        saved_scripts = self.scripts
        self.scripts = []
        for script in saved_scripts:
            script = distutils.util.convert_path(script)
            script_copy, script_ext = os.path.splitext(script)

            if script_ext != '.py':
                log.debug("Not removing extension from %s since it's not '.py'", script)
            else:
                log.debug("Copying %s -> %s", script, script_copy)
                self.copy_file(script, script_copy)
                self.scripts.append(script_copy)
        # distutils is compatible with 2.1 so we cannot use super() to
        # call it.
        distutils.command.build_scripts.build_scripts.run(self)
        self.scripts = saved_scripts

if os.name != "nt":
    COMMANDS['cmdclass'].update({
        'build_scripts': MyBuildScripts,
        })

ARGS.update(META_INFO)
ARGS.update(INSTALL)
ARGS.update(COMMANDS)
setuptools.setup(**ARGS)
