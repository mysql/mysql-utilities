#!/usr/bin/env python
#
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

"""
This file contains pylint and pep8 tests.

Requirements:
  pylint>=1.1.0
  pep8>=1.4.6
"""

import os
import sys
import csv
import optparse

try:
    from pylint import lint
    from pylint.reporters import BaseReporter
    from pylint.reporters.text import TextReporter, ColorizedTextReporter
    from pylint.__pkginfo__ import version as pylint_version
except ImportError:
    sys.stdout.write("Pylint is not installed on your system.\n")
    sys.exit(1)

try:
    from pep8 import StyleGuide, BaseReport, __version__ as pep8_version
except ImportError:
    sys.stdout.write("Pep8 is not installed on your system.\n")
    sys.exit(1)


_PYLINT_MIN_VERSION = "1.1.0"
_PEP8_MIN_VERSION = "1.4.6"
_PACKAGES = (
    os.path.join("mysql", "utilities"),
    os.path.join("mysql-test", "mutlib"),
    os.path.join("mysql-test", "t"),
    os.path.join("mysql-test", "suite", "experimental", "t"),
    os.path.join("mysql-test", "suite", "performance", "t"),
    os.path.join("mysql-test", "suite", "replication", "t"),
)
_CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))
(_BASE_PATH, _,) = os.path.split(_CURRENT_PATH)

if os.path.exists(os.path.join(_BASE_PATH, "internal")):
    _PACKAGES = _PACKAGES + (os.path.join("internal", "packaging"),)

# Add base path and mysql-test to sys.path
sys.path.append(_BASE_PATH)
sys.path.append(os.path.join(_BASE_PATH, "mysql-test", "mutlib"))

if pylint_version.split(".") < _PYLINT_MIN_VERSION.split("."):
    sys.stdout.write("ERROR: pylint version >= {0} is required to run "
                     "pylint_tests.\n".format(_PYLINT_MIN_VERSION))
    sys.exit(1)

if pep8_version.split(".") < _PEP8_MIN_VERSION.split("."):
    sys.stdout.write("ERROR: pep8 version >= {0} is required to run "
                     "pylint_tests.\n".format(_PEP8_MIN_VERSION))
    sys.exit(1)


class CustomTextReporter(TextReporter):
    """A reporter similar to TextReporter, but display messages in a custom
    format.
    """
    name = "custom"
    line_format = "{msg_id}:{line:4d},{column:2d}: {msg}"


class ParseableTextReporter(TextReporter):
    """A reporter very similar to TextReporter, but display messages in a form
    recognized by most text editors.
    """
    name = "parseable"
    line_format = "{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}"

    def __init__(self, output=None):
        """Contructor.
        """
        super(ParseableTextReporter, self).__init__(output)

    def on_set_current_module(self, module, filepath):
        """Sets the template for the current module.
        """
        self._template = unicode(self.line_format)


class CsvReporter(BaseReporter):
    """Reports messages in CSV format.
    """
    name = "csv"

    def __init__(self, output=None):
        """Constructor.
        """
        super(CsvReporter, self).__init__(output)
        self.writer = csv.writer(self.out, quoting=csv.QUOTE_ALL)
        self.writer.writerow(
            ["module", "msg_id", "line", "col", "obj", "msg"]
        )

    def add_message(self, msg_id, location, msg):
        """Receives a message.

        msg_id[in]    Message identifier
        location[in]  Tuple with (path, module, obj, line, col_offset)
        msg[in]       Message
        """
        (module, obj, line, col) = location[1:]
        self.writer.writerow([module, msg_id, line, col, obj, msg])

    def _display(self, layout):
        """Display the layout.
        """
        pass


class Pep8Report(BaseReport):
    """Pep8 report class.
    """
    def __init__(self, options, line_format, output=None, colorized=False):
        """Constructor.
        """
        super(Pep8Report, self).__init__(options)
        self.line_format = "{0}\n".format(line_format)
        self.output = output or sys.stdout
        self.colorized = colorized

    def get_msg_and_id(self, text):
        """Returns a tuple with the message ID (with '8' as prefix) and the
        message colorized.
        """
        (msg_id, msg,) = text.split(" ", 1)
        if self.colorized:
            if msg_id[0] == "E":  # It's an error
                color = 31  # Red
            else:  # It's a warning
                color = 34  # Blue
            msg = u"\033[{0}m{1}\033[0m".format(color, text)

        # Use the prefix '8' to identify a PEP8 warning
        return ("8{0}".format(msg_id), msg,)

    def error(self, line_number, offset, text, check):
        """Report an error.
        """
        super(Pep8Report, self).error(line_number, offset, text, check)
        msg = text[5:].capitalize()
        msg_id = "8{0}".format(text[:4])

        if self.colorized:
            if msg_id[1] == "E":  # It's an error
                color = 31  # Red
            else:  # It's a warning
                color = 34  # Blue
            msg = u"\033[1;{0}m{1}\033[0m".format(color, msg)

        path = os.path.relpath(self.filename, _BASE_PATH)
        module_path = os.path.splitext(path)[0]
        module_name = ".".join(module_path.split(os.path.sep))
        if self.file_errors == 1:
            module_header = "************* Module {0}".format(module_name)
            if self.colorized:
                self.output.write("\033[7;33m{0}\033[0m\n"
                                  "".format(module_header))
            else:
                self.output.write("{0}\n".format(module_header))
        error_msg = self.line_format.format(msg_id=msg_id, line=line_number,
                                            column=offset, msg=msg, path=path,
                                            symbol="", obj="", C=msg_id[0])
        self.output.write(error_msg)


class CsvPep8Report(BaseReport):
    """CSV pep8 report class.
    """
    def __init__(self, options, writer):
        """Constructor.
        """
        super(CsvPep8Report, self).__init__(options)
        self.writer = writer

    def error(self, line_number, offset, text, check):
        """Report an error.
        """
        (msg_id, msg,) = text.split(" ", 1)
        path = os.path.splitext(os.path.basename(self.filename))[0]
        self.writer.writerow([path, "8{0}".format(msg_id), line_number, offset,
                              "", msg])


def process_items(reporter, items, tester):
    """Process list of modules or packages.
    """
    test_pylint = tester in ("pylint", "all",)
    test_pep8 = tester in ("pep8", "all",)

    if test_pep8:
        # PEP8 report instance setup
        pep8style = StyleGuide(parse_argv=False, config_file=False)
        if reporter.name == "csv":
            pep8style.options.report = CsvPep8Report(pep8style.options,
                                                     reporter.writer)
        else:
            colorized = (reporter.name == "colorized")
            pep8style.options.report = Pep8Report(pep8style.options,
                                                  reporter.line_format,
                                                  reporter.out,
                                                  colorized)

    pylint_rc_path = os.path.join(_CURRENT_PATH, "pylint.rc")
    for item in items:
        path = os.path.join(_BASE_PATH, item)
        if test_pylint:
            # Pylint tests
            lint.Run([path, "--rcfile={0}".format(pylint_rc_path)],
                     reporter=reporter, exit=False)
        if test_pep8:
            # Pep8 tests
            if item.endswith(".py"):
                pep8style.input_file(path)
            else:
                pep8style.input_dir(path)


if __name__ == "__main__":
    parser = optparse.OptionParser(description="Pylint code testing.")
    parser.add_option("-f", "--format", type="choice", dest="format",
                      default="text", choices=["text", "parseable", "csv"],
                      help="output format. It can be text, parseable or csv "
                      "(default=text).")
    parser.add_option("-c", "--colorized", action="store_true",
                      dest="colorized", default=False,
                      help="colorizes text output.")
    parser.add_option("-o", "--output", action="store", type="string",
                      dest="output", help="output file.")
    parser.add_option("-t", "--tester", type="choice", dest="tester",
                      default="all", choices=["pylint", "pep8", "all"],
                      help="testing tool to be used. It can be pylint, pep8 "
                      "or all (default=all).")
    (options, args) = parser.parse_args()

    # Set the output writer
    output = open(options.output, "wb") if options.output else sys.stdout

    if args:
        # Add list of modules or packages provided as args
        items = [os.path.abspath(item) for item in args]
    else:
        # Add default packages
        items = [os.path.join(_BASE_PATH, package) for package in _PACKAGES]

        # Add the modules from "script/" folder
        scripts_path = os.path.join(_BASE_PATH, "scripts")
        scripts = []
        for root, dirs, files in os.walk(scripts_path):
            scripts.extend(
                [os.path.join(_BASE_PATH, "scripts", f) for f in files
                 if f.endswith(".py")]
            )
        items.extend(scripts)

    try:
        if options.format == "csv":
            reporter = CsvReporter(output)
        elif options.format == "parseable":
            reporter = ParseableTextReporter(output)
        elif options.colorized and sys.stdout.isatty():
            reporter = ColorizedTextReporter(output)
            reporter.line_format = CustomTextReporter.line_format
        else:
            reporter = CustomTextReporter(output)

        process_items(reporter, items, options.tester)
    except KeyboardInterrupt:
        sys.stdout.write("\n")
    finally:
        output.close()
