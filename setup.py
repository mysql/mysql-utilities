#!/usr/bin/python

# Keep the imports sorted (alphabetically) in each group. Makes
# merging easier.

import distutils.core
import os
import sys

# Setup function to use
from distutils.core import setup

from distutils.command.build_scripts import build_scripts as _build_scripts
from distutils.command.install import install as _install
from distutils.command.install_scripts import install_scripts as _install_scripts
from info import META_INFO, INSTALL

COMMANDS = {
    'cmdclass': {
        },
    }

ARGS = {
}

PROFILE_SCRIPT = '''
prepend_path () (
    IFS=':'
    for D in $PATH; do
        if test x$D != x$1; then
            OUTPATH="${OUTPATH:+$OUTPATH:}$D"
        fi
    done
    echo "$1:$OUTPATH"
)

PATH=`prepend_path %s`
'''

class install_scripts(_install_scripts):
    description = (_install_scripts.description
                   + " and add path to /etc/profile.d")

    user_options = _install_scripts.user_options + [
        ("skip-profile", None, "Skip installing a profile script"),
        ]

    boolean_options = _install_scripts.boolean_options + ['skip-profile']

    profile_file = "/etc/profile.d/mysql-utilities.sh"

    def initialize_options(self):
        _install_scripts.initialize_options(self)
        self.skip_profile = None

    def finalize_options(self):
        _install_scripts.finalize_options(self)
        self.set_undefined_options('install',
                                   ('skip_profile', 'skip_profile'))

    def run(self):
        from distutils import log, dir_util
        # We should probably use distutils.dist.execute here to allow
        # --dry-run to work properly.
        if not self.skip_profile:
            if os.path.exists(os.path.dirname(self.profile_file)):
                outfile = self.profile_file
                if os.path.isdir(outfile) and not os.path.islink(outfile):
                    dir_util.remove_tree(outfile)
                elif os.path.exists(outfile):
                    log.info("Removing %s", outfile)
                    os.unlink(outfile)
                script = PROFILE_SCRIPT % (self.install_dir,)
                log.info("Writing %s", outfile)
                open(outfile, "w+").write(script)
            else:
                log.info("Not adding %s%s", self.profile_file,
                         " (skipped)" if self.skip_profile else "")
        _install_scripts.run(self)

    def get_outputs(self):
        outputs = _install_scripts.get_outputs(self)
        if not self.skip_profile:
            outputs.append(self.profile_file)
        return outputs

class install_man(distutils.core.Command):
    description = "install (Unix) manual pages"

    user_options = [
        ('install-base=', None, "base installation directory"),
        ('force', 'f', 'force installation (overwrite existing files)'),
        ('build-dir=', 'b', 'Build directory'),
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
        from glob import glob
        from distutils import log

        outfiles = []
        man_files = glob(os.path.join(self.source_dir, '*.[12345678]'))
        for man_file in man_files:
            man_dir = 'man' + os.path.splitext(man_file)[1][1:]
            man_page = os.path.basename(man_file)
            self.mkpath(man_dir)
            man_install = os.path.join(self.target_dir, man_dir, man_page)
            self.copy_file(man_file, man_install)
            outfiles.append(man_install)
        self.outfiles = outfiles

    def get_outputs(self):
        return self.outfiles or []

# See if we have Sphinx installed, otherwise, just ignore building
# documentation.
class install(_install):
    user_options = _install.user_options + [
        ("skip-profile", None, "Skip installing a profile script"),
        ]

    boolean_options = _install.boolean_options + ['skip-profile']

    def initialize_options(self):
        _install.initialize_options(self)
        self.skip_profile = False

    def finalize_options(self):
        _install.finalize_options(self)

COMMANDS['cmdclass'].update({
        'install': install,
        })

try:
    import sphinx.setup_command

    # Add install_man command if we have Sphinx
    install.sub_commands = _install.sub_commands + [
        ('install_man', lambda self: True),
        ]

    COMMANDS['cmdclass'].update({
            'install_man': install_man,
            'build_sphinx': sphinx.setup_command.BuildDoc,
            'build_man': sphinx.setup_command.BuildDoc,
            })

    COMMANDS.setdefault('options',{}).update({
            'build_man': { 'builder': 'man' },
            })
except ImportError:
    pass

class build_scripts(_build_scripts):
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
        _build_scripts.run(self)
        self.scripts = saved_scripts

if os.name != "nt":
    COMMANDS['cmdclass'].update({
        'build_scripts': build_scripts,
        'install_scripts': install_scripts,
        })

ARGS.update(META_INFO)
ARGS.update(INSTALL)
ARGS.update(COMMANDS)
setup(**ARGS)
