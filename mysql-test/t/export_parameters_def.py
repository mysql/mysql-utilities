#!/usr/bin/env python

import os
import export_basic
from mysql.utilities.exception import MUTLibError

class test(export_basic.test):
    """check parameters for export utility
    This test executes a series of export database operations on a single
    server using a variety of parameters. It uses the export_basic test
    as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return export_basic.test.check_prerequisites(self)

    def setup(self):
        return export_basic.test.setup(self)
         
    def run(self):
        self.res_fname = "result.txt"
       
        from_conn = "--server=" + self.build_connection_string(self.server1)
       
        cmd_str = "mysqldbexport.py %s " % from_conn
        
        cmd_opts = "util_test --help"
        comment = "Test case 1 - help"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        # Now test the skips

        cmd_opts = "%s util_test --skip=grants" % cmd_str
        comment = "Test case 2 - no grants"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_opts += ",events"
        comment = "Test case 3 - no events"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_opts += ",functions"
        comment = "Test case 4 - no functions"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_opts += ",procedures"
        comment = "Test case 5 - no procedures"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_opts += ",triggers"
        comment = "Test case 6 - no triggers"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_opts += ",views"
        comment = "Test case 7 - no views"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_opts += ",tables"
        comment = "Test case 8 - no tables"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)        

        cmd_opts += ",create_db"
        comment = "Test case 9 - no create_db"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)        

        cmd_opts += ",data"
        comment = "Test case 10 - no data"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
            
        cmd_opts = "%s util_test --format=SQL --export=definitions" % cmd_str
        comment = "Test case 11 - SQL single rows"
        res = self.run_test_case(0, cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 12 - SQL bulk insert"
        res = self.run_test_case(0, cmd_opts + " --bulk-insert", comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        self.test_format_and_display_values(cmd_str + " util_test --export="+\
                                            "definitions --format=", 13)

        return True

    def test_format_and_display_values(self, cmd_opts, starting_case_num,
                                       full_format=True, no_headers=True,
                                       abbrev=True, displays=True):
        
        _FORMATS = ("sql", "csv", "tab", "GRID", "VERTICAL")
        _FORMATS_ABBREV = ("SQ", "CS", "ta", "g", "v")

        # First, with headers
        if full_format:
            for format in _FORMATS:
                cmd_variant = cmd_opts + format
                comment = "Test case %s - %s format" % \
                          (starting_case_num, format)
                res = self.run_test_case(0, cmd_variant, comment)
                starting_case_num += 1
                if not res:
                    raise MUTLibError("%s: failed" % comment)
        
        # Now without headers
        if no_headers:
            for format in _FORMATS:
                cmd_variant = cmd_opts + format + " --no-headers"
                comment = "Test case %s - %s format no headers" % \
                          (starting_case_num, format)
                res = self.run_test_case(0, cmd_variant, comment)
                starting_case_num += 1
                if not res:
                    raise MUTLibError("%s: failed" % comment)
        
        # Now the abbreviations
        if abbrev:
            for format in _FORMATS_ABBREV:
                cmd_variant = cmd_opts + format
                comment = "Test case %s - %s format" % \
                          (starting_case_num, format)
                res = self.run_test_case(0, cmd_variant, comment)
                starting_case_num += 1
                if not res:
                    raise MUTLibError("%s: failed" % comment)

        # Conduct format and display combination tests
        
        _DISPLAYS = ("BRIEF", "FULL", "NAMES")
        # SQL format not valid
        _FORMAT_DISPLAY = ("GRID","CSV","TAB","VERTICAL")

        if displays:
            for format in _FORMAT_DISPLAY:
                for display in _DISPLAYS:
                    cmd_variant = cmd_opts + format + " --display=%s" % display
                    comment = "Test case %s - %s format with %s display" % \
                              (starting_case_num, format, display)
                    res = self.run_test_case(0, cmd_variant, comment)
                    starting_case_num += 1
                    if not res:
                        raise MUTLibError("%s: failed" % comment)

        # Perform masking for deterministic output
        
        self.replace_result("CREATE EVENT `e1` ON SCHEDULE EVERY 1 YEAR",
                            "CREATE EVENT `e1` ON SCHEDULE EVERY 1 YEAR "
                            "STARTS XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\n")
        self.replace_result("CREATE DEFINER=`root`@`localhost` EVENT `e1`",
                            "CREATE EVENT `e1` ON SCHEDULE EVERY 1 YEAR "
                            "STARTS XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\n")
 

        self._mask_grid()
        self._mask_csv()
        self._mask_tab()
        self._mask_vertical()

        return True

    def _mask_grid(self):
	self.mask_column_result("| def ", "|", 2, " None           ")
        self.mask_column_result("| None           | util_test       | trg", "|",
                                2, " None             ")
        self.mask_column_result("| None             | util_test       | trg", "|",
                                6, " None                  ")
        self.mask_column_result("| None           | util_test     | t", "|",
                                16, " XXXX-XX-XX XX:XX:XX ")
        self.mask_column_result("| None           | util_test     | t", "|",
                                11, " XXXXXXXXXX ")
        self.mask_column_result("| None           | util_test     | t", "|",
                                12, " XXXXXXXXXX ")
        self.mask_column_result("| None           | util_test     | t", "|",
                                14, " XXXXXXXXXX ")
        self.mask_column_result("| None           | util_test     | t", "|",
                                17, " XXXX-XX-XX XX:XX:XX ")
        self.mask_column_result("| None           | util_test "
                                "    | e1          |", "|",
                                14, " XXXX-XX-XX XX:XX:XX ")
        self.mask_column_result("| util_test  | e1    |", "|",
                                18, " X           ")
        self.mask_column_result("| util_test  | e1    |", "|",
                                9, " XXXX-XX-XX XX:XX:XX  ")
        self.mask_column_result("| util_test  | e1    |", "|",
                                10, " XXXX-XX-XX XX:XX:XX  ")
        self.mask_column_result("| util_test  | e1    |", "|",
                                12, " XXXX-XX-XX XX:XX:XX  ")
        self.mask_column_result("| e1    | root@localhost  |", "|",
                                10, " XXXX-XX-XX XX:XX:XX  ")
        self.mask_column_result("| e1    | root@localhost  |", "|",
                                14, " X           ")
        self.mask_column_result("| util_test  | p1", "|",
                                14, " XXXX-XX-XX XX:XX:XX  ")
        self.mask_column_result("| util_test  | p1", "|",
                                15, " XXXX-XX-XX XX:XX:XX  ")
        self.mask_column_result("| util_test  | f1", "|",
                                14, " XXXX-XX-XX XX:XX:XX  ")
        self.mask_column_result("| util_test  | f1", "|",
                                15, " XXXX-XX-XX XX:XX:XX  ")


    def _mask_csv(self):
        self.mask_column_result("e1,root@localhost,", ",",
                                5, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("e1,root@localhost,", ",",
                                9, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("e1,root@localhost,", ",",
                                10, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("e1,root@localhost,", ",",
                                13, "XX")
        self.mask_column_result("def,util_test,", ",", 1, "")
        self.mask_column_result(",util_test,trg", ",", 5, "")
        self.mask_column_result(",util_test,t", ",",
                                10, "XXXXXXXXXX")
        self.mask_column_result(",util_test,t", ",",
                                11, "XXXXXXXXXX")
        self.mask_column_result(",util_test,t", ",",
                                13, "XXXXXXXXXX")
        self.mask_column_result(",util_test,t", ",",
                                15, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result(",util_test,t", ",",
                                16, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("util_test,p1,PROCEDURE", ",",
                                13, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("util_test,p1,PROCEDURE", ",",
                                14, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("util_test,f1,FUNCTION", ",",
                                13, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("util_test,f1,FUNCTION", ",",
                                14, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("util_test,e1", ",",
                                8, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result(",util_test,e1", ",",
                                17, "XX")
        self.mask_column_result("util_test,e1", ",",
                                9, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("util_test,e1", ",",
                                11, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("util_test,e1", ",",
                                17, "XX")
                                

    def _mask_tab(self):
        self.mask_column_result("e1	root@localhost", "\t",
                                5, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("e1	root@localhost", "\t",
                                9, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("e1	root@localhost", "\t",
                                10, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("e1	root@localhost", "\t",
                                13, "XX")
        self.mask_column_result("def	util_test	t", "\t", 1, "")
        self.mask_column_result("def	util_test	v", "\t", 1, "")
        self.mask_column_result("	util_test	trg", "\t", 5, "")
        self.mask_column_result("	util_test	t", "\t",
                                10, "XXXXXX")
        self.mask_column_result("	util_test	t", "\t",
                                11, "XXXXXXXX")
        self.mask_column_result("	util_test	t", "\t",
                                13, "XX")
        self.mask_column_result("	util_test	t", "\t",
                                15, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("	util_test	t", "\t",
                                16, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("util_test	p1	PROCEDURE", "\t",
                                13, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("util_test	p1	PROCEDURE", "\t",
                                14, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("util_test	f1	FUNCTION", "\t",
                                13, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("util_test	f1	FUNCTION", "\t",
                                14, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("util_test	e1", "\t",
                                8, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("util_test	e1", "\t",
                                17, "XX")
        self.mask_column_result("util_test	e1", "\t",
                                9, "XXXX-XX-XX XX:XX:XX")
        self.mask_column_result("util_test	e1", "\t",
                                11, "XXXX-XX-XX XX:XX:XX")
    
    def _mask_vertical(self):
        self.replace_result("                   UPDATE_TIME:",
                            "                   UPDATE_TIME: "
                            "XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("                   CREATE_TIME:",
                            "                   CREATE_TIME: "
                            "XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("              UPDATE_TIME:",
                            "              UPDATE_TIME: "
                            "XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("              CREATE_TIME:",
                            "              CREATE_TIME: "
                            "XXXX-XX-XX XX:XX:XX\n")

        self.replace_result("              CREATED:",
                            "              CREATED: XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("              created:",
                            "              CREATED: XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("             modified:",
                            "             MODIFIED: XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("         LAST_ALTERED:",
                            "         LAST_ALTERED: XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("               STARTS:",
                            "               STARTS: XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("               starts:",
                            "               STARTS: XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("                 ends:",
                            "                 ENDS: XXXX-XX-XX XX:XX:XX\n")
        self.replace_result("           ORIGINATOR:",
                            "           ORIGINATOR: XX\n")
        self.replace_result("           originator:",
                            "           ORIGINATOR: XX\n")

        self.replace_result("                   DATA_LENGTH:",
                            "                   DATA_LENGTH: XXXXXXX\n")
        self.replace_result("                  INDEX_LENGTH:",
                            "                  INDEX_LENGTH: XXXXXXX\n")
        self.replace_result("               MAX_DATA_LENGTH:",
                            "               MAX_DATA_LENGTH: XXXXXXX\n")
        self.replace_result("                     DATA_FREE:",
                            "                     DATA_FREE: XXXXXXXXXXX\n")
        
        self.replace_result("           AVG_ROW_LENGTH:",
                            "           AVG_ROW_LENGTH: XXXXXXX\n")
        self.replace_result("              DATA_LENGTH:",
                            "              DATA_LENGTH: XXXXXXX\n")
        self.replace_result("             INDEX_LENGTH:",
                            "             INDEX_LENGTH: XXXXXXX\n")
        self.replace_result("          MAX_DATA_LENGTH:",
                            "          MAX_DATA_LENGTH: XXXXXXX\n")
        self.replace_result("                DATA_FREE:",
                            "                DATA_FREE: XXXXXXXXXXX\n")
	self.replace_result("            TABLE_CATALOG: def",
                            "            TABLE_CATALOG: None\n")
        self.replace_result("        TABLE_CATALOG: def",
                            "        TABLE_CATALOG: None\n")
        self.replace_result("            TRIGGER_CATALOG: def",
                            "            TRIGGER_CATALOG: None\n")
        self.replace_result("       EVENT_OBJECT_CATALOG: def",
                            "       EVENT_OBJECT_CATALOG: None\n")
  
    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        return export_basic.test.cleanup(self)



