#!/usr/bin/python

# Keep the imports sorted (alphabetically) in each group. Makes
# merging easier.

import distutils.core
import os
import sys
import re
import subprocess
from glob import glob

# Setup function to use
from distutils.core import setup

from distutils.command.build_scripts import build_scripts as _build_scripts
from distutils.command.install import install as _install
from distutils.command.install_scripts import install_scripts as _install_scripts

from distutils.file_util import copy_file, write_file
from distutils.dir_util import remove_tree
from distutils.filelist import findall
from distutils.core import Command
from distutils import log, dir_util

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
        ('root=', None,
         "install everything relative to this alternate root directory"),
        ]

    boolean_options = _install_scripts.boolean_options + ['skip-profile']

    def initialize_options(self):
        _install_scripts.initialize_options(self)
        self.skip_profile = None

    def finalize_options(self):
        _install_scripts.finalize_options(self)
        self.set_undefined_options('install',
                                   ('skip_profile', 'skip_profile'))

        self.profile_filename = 'mysql-utilities.sh'
        self.profile_file = os.path.join(self.build_dir, self.profile_filename)

    def _create_shell_profile(self):
        """Creates and installes the shell profile
        """
        if self.skip_profile:
            log.info("Not adding shell profile %s (skipped)" % (
                     os.path.join(install_dir, self.profile_filename)))
            return

        # When creating an RPM, we need to fix the location of scripts
        building_rpm = False
        if 'BUILDROOT' in self.install_dir:
            building_rpm = True
            install_dir = re.search('BUILDROOT/.*?(/.*)$',
                                    self.install_dir).group(1)
        else:
            install_dir = '/etc/profile.d'
            destfile = os.path.join(install_dir, self.profile_filename)
            if not os.access(destfile, os.X_OK | os.W_OK):
                log.info("Not installing mysql-utilities.sh in "
                         "%s (no permission)" % install_dir)
                self.skip_profile = True
                return

        if os.path.exists(os.path.dirname(self.profile_file)):
            outfile = self.profile_file
            if os.path.isdir(outfile) and not os.path.islink(outfile):
                dir_util.remove_tree(outfile)
            elif os.path.exists(outfile):
                log.info("Removing %s", outfile)
                os.unlink(outfile)

            script = PROFILE_SCRIPT % (install_dir,)
            log.info("Writing %s", outfile)
            open(outfile, "w+").write(script)

        if not building_rpm:
            self.copy_file(outfile, install_dir)

    def run(self):
        # We should probably use distutils.dist.execute here to allow
        # --dry-run to work properly.
        self._create_shell_profile()
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
        ('record=', None,
         "filename in which to record list of installed files"),
        ('root=', None,
         "install everything relative to this alternate root directory"),
    ]

    boolean_options = ['force']

    def initialize_options(self):
        self.install_base = None
        self.build_dir = None
        self.force = None
        self.skip_build = None
        self.record = None
        self.root = None

    def finalize_options(self):
        self.set_undefined_options('install',
                                   ('install_data', 'install_base'),
                                   ('force', 'force'),
                                   ('root', 'root'),
                                   )
        self.set_undefined_options('build_sphinx',
                                   ('build_dir', 'build_dir'),
                                   )

        if self.root:
            # Convert absolute to relative
            if self.install_base[0] == '/':
                self.target_dir = os.path.join(self.root, self.install_base[1:])
            else:
                self.target_dir = os.path.join(self.root, self.install_base)
        else:
            self.target_dir = os.path.join(self.install_base, 'man')

        self.source_dir = os.path.join(self.build_dir, 'man')

    def run(self):
        outfiles = []
        man_files = glob(os.path.join(self.source_dir, '*.[12345678]'))
        for man_file in man_files:
            man_dir = 'man' + os.path.splitext(man_file)[1][1:]
            man_page = os.path.basename(man_file)
            self.mkpath(man_dir)
            man_install = os.path.join(self.target_dir, man_dir, man_page)
            self.copy_file(man_file, man_install)
            outfiles.append(man_install)
            print "man_install:", man_install
        self.outfiles = outfiles

        # write list of installed files, if requested.
        if self.record:
            outputs = self.get_outputs()
            if self.root:               # strip any package prefix
                root_len = len(self.root)
                for counter in xrange(len(outputs)):
                    outputs[counter] = outputs[counter][root_len:]
            self.execute(write_file,
                         (self.record, outputs),
                         "writing list of installed files to '%s'" %
                         self.record)

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

class bdist_rpm(Command):
    """Create a RPM distribution"""
    description = 'create a source RPM distribution'
    user_options = [
        ('bdist-base=', 'd',
         "base directory for creating built distributions"),
        ('rpm-base=', 'd',
         "base directory for creating RPMs (default <bdist-dir>/rpm)"),
        ('keep-temp', 'k',
         "keep the pseudo-installation tree around after "
         "creating the distribution archive"),
        ('dist-dir=', 'd',
         "directory to put final built distributions in"),
    ]

    def initialize_options(self):
        """Initialize the options"""
        self.bdist_base = None
        self.rpm_base = None
        self.keep_temp = 0
        self.dist_dir = None
    
    def finalize_options(self):
        """Finalize the options"""
        self.set_undefined_options('bdist',
                                   ('bdist_base', 'bdist_base'))

        if not self.rpm_base:
            self.rpm_base = os.path.join(self.bdist_base, 'rpm')

        self.rpm_spec = 'support/RPM/mysql_utilities.spec'

        self.set_undefined_options('bdist', ('dist_dir', 'dist_dir'))

    def _populate_rpmbase(self):
        """Create and populate the RPM base directory"""
        #self.mkpath(self.rpm_base)
        self._rpm_dirs = {}
        dirs = ['BUILD', 'RPMS', 'SOURCES', 'SPECS', 'SRPMS']
        for dirname in dirs:
            self._rpm_dirs[dirname] = os.path.join(self.rpm_base, dirname)
            self.mkpath(self._rpm_dirs[dirname])
    
    def _prepare_distribution(self):
        raise NotImplemented

    def _create_rpm(self):
        log.info("creating RPM using rpmbuild")

        cmd = ['rpmbuild',
            '-bb',
            '-D', "_topdir " + os.path.abspath(self.rpm_base),
            '-D', "release_info " + META_INFO['description'],
            '-D', "version " + META_INFO['version'],
            self.rpm_spec
            ]
        if not self.verbose:
           cmd.append('--quiet')

        self.spawn(cmd)
        print ' '.join(cmd)

        rpms = os.path.join(self.rpm_base, 'RPMS')
        for base, dirs, files in os.walk(rpms):
            for filename in files:
                if filename.endswith('.rpm'):
                    filepath = os.path.join(base, filename)
                    copy_file(filepath, self.dist_dir)

    def run(self):
        """Run the distutils command"""
        # check whether we can execute rpmbuild
        if not self.dry_run:
            try:
                devnull = open(os.devnull, 'w')
                subprocess.Popen('rpmbuild', stdin=devnull, stdout=devnull)
            except OSError:
                raise DistutilsError("Cound not execute rpmbuild. Make sure "
                                     "it is installed and in your PATH")

        self._populate_rpmbase()
        
        saved_dist_files = self.distribution.dist_files[:]
        sdist = self.reinitialize_command('sdist')
        sdist.formats = ['gztar']
        self.run_command('sdist')
        self.distribution.dist_files = saved_dist_files

        source = sdist.get_archive_files()[0]
        source_dir = self._rpm_dirs['SOURCES']
        self.copy_file(source, source_dir)
        
        self._create_rpm()

        if not self.keep_temp:
            remove_tree(self.bdist_base, dry_run=self.dry_run)

if os.name != "nt":
    COMMANDS['cmdclass'].update({
        'build_scripts': build_scripts,
        'install_scripts': install_scripts,
        'bdist_rpm': bdist_rpm,
        })

ARGS.update(META_INFO)
ARGS.update(INSTALL)
ARGS.update(COMMANDS)
setup(**ARGS)
