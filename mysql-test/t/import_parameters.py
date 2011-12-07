#!/usr/bin/env python

import os
import import_basic
from mysql.utilities.exception import MUTLibError, UtilDBError

class test(import_basic.test):
    """check parameters for import utility
    This test executes a basic check of parameters for mysqldbimport.
    It uses the import_basic test as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return import_basic.test.check_prerequisites(self)

    def setup(self):
        return import_basic.test.setup(self)

    def do_skip_test(self, cmd_str, comment, expected_res=0):
        # Precheck: check db and save the results.
        self.results.append("BEFORE:\n")
        self.results.append(self.check_objects(self.server2, "util_test"))

        res = self.run_test_case(expected_res, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # Now, check db and save the results.
        self.results.append("AFTER:\n")
        res = self.server2.exec_query("SHOW DATABASES LIKE 'util_test'")
        if res == () or res == []:
            self.results.append("Database was NOT created.\n")
        else:
            self.results.append("Database was created.\n")
        self.results.append(self.check_objects(self.server2, "util_test"))
        try:
            self.drop_db(self.server2, "util_test")
        except:
            pass # ok if this fails - it is a spawned server

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server=" + self.build_connection_string(self.server1)
        to_conn = "--server=" + self.build_connection_string(self.server2)

        cmd_str = "mysqldbimport.py %s %s --import=definitions " % \
                  (to_conn, self.export_import_file)

        cmd_opts = " --help"
        comment = "Test case 1 - help"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # Now test the skips

        # Note: data and blobs must be done separately
        _SKIPS = ("grants", "events", "functions", "procedures",
                  "triggers", "views", "tables", "create_db")
        _FORMATS = ("CSV", "SQL")

        case_num = 2
        for format in _FORMATS:
            # Create an import file
            export_cmd = "mysqldbexport.py %s util_test --export=BOTH " % \
                         from_conn
            export_cmd += "--format=%s --display=BRIEF > %s " % \
                          (format, self.export_import_file)
            comment = "Generating import file"
            res = self.run_test_case(0, export_cmd, comment)
            if not res:
                raise MUTLibError("%s: failed" % comment)

            cmd_opts = "%s --format=%s --skip=" % (cmd_str, format)
            for skip in _SKIPS:
                if case_num != 2 and case_num != 2 + len(_SKIPS):
                    cmd_opts += ","
                cmd_opts += "%s" % skip
                comment = "Test case %d - no %s" % (case_num, skip)
                self.do_skip_test(cmd_opts, comment)
                case_num += 1


        # Now test --skip=data, --skip-blobs
        # Create an import file with blobs

        try:
            res = self.server1.exec_query("ALTER TABLE util_test.t3 "
                                          "ADD COLUMN me_blob BLOB")
            res = self.server1.exec_query("UPDATE util_test.t3 SET "
                                          "me_blob = 'This, is a BLOB!'")
        except UtilDBError, e:
            raise MUTLibError("Failed to add blob column: %s" % e.errmsg)

        export_cmd = "mysqldbexport.py %s util_test --export=BOTH " % \
                     from_conn
        export_cmd += "--format=%s --display=BRIEF > %s " % \
                      ("CSV", self.export_import_file)
        comment = "Generating import file"
        res = self.run_test_case(0, export_cmd, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # No skips for reference (must skip events for deterministic reasons
        cmd_str = "mysqldbimport.py %s %s --import=both --dryrun " % \
                  (to_conn, self.export_import_file)
        cmd_str += " --format=CSV --bulk-insert "
        comment = "Test case %d - no %s" % (case_num, "events")
        res = self.run_test_case(0, cmd_str+"--skip=events", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        case_num += 1

        cmd_str = "mysqldbimport.py %s %s --import=both --dryrun " % \
                  (to_conn, self.export_import_file)
        cmd_str += " --format=CSV --bulk-insert "
        comment = "Test case %d - no %s" % (case_num, "data")
        res = self.run_test_case(0, cmd_str+"--skip=events,data", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        case_num += 1

        cmd_str = "mysqldbimport.py %s %s --import=both --dryrun " % \
                  (to_conn, self.export_import_file)
        cmd_str += " --format=CSV --skip-blobs --bulk-insert "
        comment = "Test case %d - no %s" % (case_num, "blobs")
        res = self.run_test_case(0, cmd_str+"--skip=events", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        case_num += 1

        # Lastly, do a quiet import

        cmd_str = "mysqldbimport.py %s %s --import=both --quiet " % \
                  (to_conn, self.export_import_file)
        cmd_str += " --format=CSV --bulk-insert "
        comment = "Test case %d - no %s" % (case_num, "messages (quiet)")
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        case_num += 1

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return import_basic.test.cleanup(self)
