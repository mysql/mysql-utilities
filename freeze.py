#!/usr/bin/python

import sys

from info import META_INFO, INSTALL, COMMANDS

from cx_Freeze import setup     # Setup function to use

if sys.platform.startswith("win32"):
    META_INFO['name'] = 'MySQL Utilities'

ARGS = {
    'executable': [
        cx_Freeze.Executable(exe, base="Console") for exe in INSTALL['scripts']
        ],
    'options': {
        'bdist_msi': { 'add_to_path': True, },
        }
    }

ARGS.update(META_INFO)
ARGS.update(INSTALL)
ARGS.update(COMMANDS)
setup(**ARGS)

