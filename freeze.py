#!/usr/bin/python

import sys
import cx_Freeze

from info import META_INFO, INSTALL, COMMANDS

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
cx_Freeze.setup(**ARGS)

