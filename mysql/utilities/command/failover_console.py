#!/usr/bin/env python
#
# Copyright (c) 2010, 2012 Oracle and/or its affiliates. All rights reserved.
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
This file contains the automatic failover console. It contains only the
user interface code for the automatic failover feature for replication.
"""

import logging
import os
import sys
import time
from mysql.utilities.exception import UtilError, UtilRplError

_CONSOLE_HEADER = "MySQL Replication Failover Utility"
_CONSOLE_FOOTER = "Q-quit R-refresh H-health G-GTID Lists U-UUIDs"

_COMMAND_KEYS = {'\x1b[A':'ARROW_UP', '\x1b[B':'ARROW_DN'}

# Minimum number of rows needed to display screen
_MINIMUM_ROWS = 15
_HEALTH_LIST = "Replication Health Status"
_GTID_LISTS = ["Transactions executed on the servers:",
               "Transactions purged from the servers:",
               "Transactions owned by another server:"]
_UUID_LIST = "UUIDs"
_LOG_LIST = "Log File"
_GEN_UUID_COLS = ['host','port','role','uuid']
_GEN_GTID_COLS = ['host','port','role','gtid']
_DATE_LEN = 22

_DROP_FC_TABLE = "DROP TABLE mysql.failover_console"
_CREATE_FC_TABLE = "CREATE TABLE IF NOT EXISTS mysql.failover_console " + \
                   "(host char(30), port char(10))"
_SELECT_FC_TABLE = "SELECT * FROM mysql.failover_console WHERE host = '%s' " + \
                   "AND port = '%s'"
_INSERT_FC_TABLE = "INSERT INTO mysql.failover_console VALUES ('%s', '%s')"
_DELETE_FC_TABLE = "DELETE FROM mysql.failover_console WHERE host = '%s' " + \
                   "AND port = '%s'"
        

# Try to import the windows getch() if it fails, we're on Posix so define
# a custom getch() method to return keys.
try:
    # Win32
    from msvcrt import getch, kbhit
except ImportError:
    # UNIX/Posix
    import termios, tty
    from select import select
    
    # Make a get character keyboard method for Posix machines.
    def getch():
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        new = termios.tcgetattr(fd)
        new[3] = new[3] & ~termios.ICANON & ~termios.ECHO
        new[6][termios.VMIN] = 1
        new[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, new)
        key = None
        try:
            key = os.read(fd, 4)
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, old)
        return key
    
    # Make a keyboard hit method for Posix machines.
    def kbhit():
        return select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])


def get_terminal_size():
    """Return the size in columns, rows for terminal window
    
    This method will attempt to determine the current terminal window size.
    If it cannot, it returns the default of (80, 25) = 80 characters
    on a line and 25 lines.
    
    Returns tuple - (x, y) = max colum (# chars), max rows 
    """
    import struct

    default = (80,25)
    try:
        if os.name == "posix":
            import fcntl, termios
            y, x = 0, 1
            packed_info = fcntl.ioctl(0, termios.TIOCGWINSZ,
                                      struct.pack('HHHH', 0, 0, 0, 0))
            wininfo = struct.unpack('HHHH', packed_info)
            return (wininfo[x], wininfo[y])
        else:
            from ctypes import windll, create_string_buffer
    
            # -11 == stdout
            handle = windll.kernel32.GetStdHandle(-11)
            strbuff = create_string_buffer(22)
            res = windll.kernel32.GetConsoleScreenBufferInfo(handle, strbuff)
            left, top, right, bottom = 5, 6, 7, 8
            wininfo = struct.unpack("hhhhHhhhhhh", csbi.raw)
            x = wininfo[right] - wininfo[left] + 1
            y = wininfo[bottom] - wininfo[top ]+ 1
            return (x, y)
    except:
        pass # silence! just return default on error.
    return default


class FailoverConsole(object):
    """Automatic Failover Console
    
    This class implements a basic, text screen console for displaying
    information about the master and the replication health for the 
    topology. The interface supports these commands:
    
      - H = show replication health
      - G = toggle through GTID lists (GTID_DONE, GTID_LOST, GTID_OWNED)
    
    """
    
    def __init__(self, master, get_health_data,
                 get_gtid_data, get_uuid_data, options):
        """Constructor
        
        The constructor requires the caller to specify a master of the
        Master class instance, and method pointers for getting health,
        gtid, and uuid information. An options dictionary is used to define
        overal behavior of the class methods.
        
        master[in]          a Master class instance
        get_health_data[in] method pointer to heatlh data method
        get_gtid_data[in]   method pointer to gtid data method
        get_uuid_data[in]   method pointer to uuid data method
        options[in]         option dictionary to include
          interval          time in seconds for interval loop, default = 15
          failover_mode     failover mode (used for reporting only),
                            default = 'auto'
        """
        self.interval = int(options.get("interval", 15))
        self.mode = options.get("failover_mode", "auto")
        self.logging = options.get("logging", False)
        self.log_file = options.get("log_file", None)

        self.alarm = time.time() + self.interval
        self.gtid_list = -1
        self.scroll_size = 0
        self.start_list = 0
        self.end_list = 0
        self.rows_printed = 0
        self.list_data = None
        self.comment = _HEALTH_LIST
        self.scroll_on = False
        self.old_mode = None
        
        # Callback methods for reading data
        self.master = master
        self.get_health_data = get_health_data
        self.get_gtid_data = get_gtid_data
        self.get_uuid_data = get_uuid_data
        
        self._reset_screen_size()
        
        
    def register_instance(self, clear=False, register=True):
        """Register the console as running on the master.
        
        This method will attempt to register the console as running against
        the master for failover modes auto or elect. If another console is
        already registered, this instance becomes blocked resulting in the
        mode change to 'fail' and failover will not occur when this instance
        of the console detects failover.
        
        clear[in]      if True, clear the sentinel database entries on the
                       master. Default is False.
        register[in]   if True, register the console on the master. If False,
                       unregister the console on the master. Default is True.
   
        Returns string - new mode if changed     
        """
        # We cannot check disconnected masters and do not need to check if
        # we are doing a simple fail mode.
        if self.master is None or self.mode == 'fail':
            return self.mode
        
        host_port = (self.master.host, self.master.port)
        # Drop the table if specified
        if clear:
            self.master.exec_query(_DROP_FC_TABLE)
        
        # Register the console
        if register:
            res = self.master.exec_query(_CREATE_FC_TABLE)
            res = self.master.exec_query(_SELECT_FC_TABLE % host_port)
            if res != []:
                # Someone beat us there. Drat.
                self.old_mode = self.mode
                self.mode = 'fail'
            else:
                # We're first! Yippee.
                res = self.master.exec_query(_INSERT_FC_TABLE % host_port)
        # Unregister the console if our mode was changed
        elif self.old_mode != self.mode:
            res = self.master.exec_query(_DELETE_FC_TABLE % host_port)
        
        return self.mode


    def _reset_interval(self, interval=15):
        """Reset the interval timing
        """
        self.interval = interval
        self.alarm = self.interval + time.time()
   
   
    def _reset_screen_size(self):
        """Recalculate the screen size
        """
        self.max_cols, self.max_rows = get_terminal_size()
        if self.max_rows < _MINIMUM_ROWS: 
            self.max_rows = _MINIMUM_ROWS   


    def _format_gtid_data(self):
        """Get the formatted GTID data
        
        This method sets the member list_data to the GTID list to populate
        the list. A subsequent call to _print_list() displays the new
        list.
        """
        rows = []

        # Get GTID lists
        self.gtid_list += 1
        if self.gtid_list > 2:
            self.gtid_list = 0
        if self.get_gtid_data is not None:
            gtid_data = self.get_gtid_data()
            self.comment = _GTID_LISTS[self.gtid_list]
            rows = gtid_data[self.gtid_list]
            
        self.start_list = 0
        self.end_list = len(rows)
        return (_GEN_GTID_COLS, rows)


    def _format_health_data(self):
        """Get the formatted health data
        
        This method sets the member list_data to the health list to populate
        the list. A subsequent call to _print_list() displays the new
        list.
        """
        rows = []

        # Get health information
        if self.get_health_data is not None:
            health_data = self.get_health_data()
            self.start_list = 0
            self.end_list = len(health_data[1])
            return health_data
        
        return ([], [])

        
    def _format_uuid_data(self):
        """Get the formatted UUID data
        
        This method sets the member list_data to the UUID list to populate
        the list. A subsequent call to _print_list() displays the new
        list.
        """
        rows = []

        # Get UUID information
        if self.get_uuid_data is not None:
            self.comment = _UUID_LIST
            rows = self.get_uuid_data()

        print rows
        self.start_list = 0
        self.end_list = len(rows)
        return (_GEN_UUID_COLS, rows)
        
    
    def _format_log_entries(self):
        """Get the log data if logging is on
        
        This method sets the member list_data to the log entries to populate
        the list if logging is enables. A subsequent call to _print_list()
        displays the new list.
        """
        rows = []
        cols = ["Date", "Entry"]
        if self.logging and self.log_file is not None:
            self.comment = _LOG_LIST
            log = open(self.log_file, "r")
            for row in log.readlines():
                rows.append((row[0:_DATE_LEN], row[_DATE_LEN+1:].strip('\n')))
            log.close()        
            self.start_list = 0
            self.end_list = len(rows)

        return(cols, rows)

        
    def _do_command(self, key):
        """Execute the user command representing the key pressed
        
        This method executes the command based on the key pressed. Commands
        recognized include show health, toggle through GTID lists, show
        UUIDs, and scroll list UP/DOWN.
        
        The method also checks for resize of the terminal window for nicer,
        automatic list resize.
        
        key[in]        key pressed by user
                       Note: Invalid keys are ignored.    
        """
        # We check for screen resize here
        self.max_cols, self.max_rows = get_terminal_size()
        
        # Reset the GTID list counter
        if key not in ['g','G']:
            self.gtid_list = -1

        # Refresh
        if key in ['r','R']:
            self._refresh()
        # Show GTIDs
        elif key in ['g','G']:
            self.list_data = self._format_gtid_data()
            self._print_list()
        # Show health report
        elif key in ['h','H']:
            self.list_data = self._format_health_data()
            self._print_list()
        elif key in ['u','U']:
            self.list_data = self._format_uuid_data()
            self._print_list()
        elif key in ['l', 'L']:
            if self.logging:
                self.list_data = self._format_log_entries()
                self._print_list()
        elif key in _COMMAND_KEYS:
            self._scroll(key)
            
   
    def _wait_for_interval(self):
        """Wait for the time interval to expire
        
        This method issues a timing loop to wait for the specified interval to
        expire or quit if the user presses 'q' or 'Q'. The method passes all
        other keyboard requests to the _do_command() method for processing.

        If the interval expires, the method returns None.
        If the user presses a key, the method returns the numeric key number.
        
        Returns - None or int (see above)        
        """
        # If on *nix systems, set the terminal IO sys to not echo
        if os.name == "posix":
            import tty, termios
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
            
        key = None
        done = False
        # loop for interval in seconds while detecting keypress 
        while not done:
            done = self.alarm <= time.time()
            if kbhit() and not done:
                key = getch()
                done = True

        # Reset terminal IO sys to older state
        if os.name == "posix":
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

        return key
    
    
    def clear(self):
        """Clear the screen
        
        This method uses a platform specific terminal screen clear to simulate
        a clear of the console.
        """
        if os.name == "posix":
            os.system("clear")
        else:
            os.system("cls")
        self.rows_printed = 0
   
    
    def _print_header(self):
        """Display header
        """
        print _CONSOLE_HEADER
        next_interval = time.ctime(self.alarm)
        print "Failover Mode =", self.mode, "    Next Interval =", next_interval
        if self.old_mode is not None and self.old_mode != self.mode:
            print
            print "NOTICE: Failover mode changed to fail due to another"
            print "        instance of the console running against master."
            self.rows_printed += 2
            self.max_rows -= 3
        print
        self.rows_printed += 4
   
    
    def _print_master_status(self):
        """Display the master information
        
        This method displays the master information from SHOW MASTER STATUS.
        """
        from mysql.utilities.common.format import format_tabular_list
        
        # If no master present, don't print anything.
        if self.master is None:
            return
        
        try:
            status = self.master.get_status()[0]
            if self.logging:
                logging.info("Master status: binlog: %s, position:%s" %
                             (status[0], status[1]))
        except:
            raise UtilRplError("Cannot get master status")
        print "Master Information"
        print "------------------"
        cols = ("Binary Log File", "Position",
                "Binlog_Do_DB", "Binlog_Ignore_DB")
        fmt_opts = {
           "print_header" : True,
           "separator"    : None,
           "quiet"        : True,
           "print_footer" : False,
        }
        logfile = status[0][0:20] if len(status[0]) > 20 else status[0]
        rows = [(logfile, status[1], status[2], status[3])]
        format_tabular_list(sys.stdout, cols, rows, fmt_opts)
        print
        self.rows_printed += 4
    
    
    def _scroll(self, key):
        """Scroll the list view
        
        This method recalculates the start_list and end_list member variables
        depending on the key pressed. UP moves the list up (lower row indexes)
        and DOWN moves the list down (higher row indexes). It calls
        _print_list() at the end to redraw the screen.
                
        key[in]        key pressed by user
                       Note: Invalid keys are ignored.
        """
        from mysql.utilities.common.format import print_list

        if _COMMAND_KEYS[key] == 'ARROW_UP':
            if self.start_list > 0:
                self.start_list -= self.scroll_size
                if self.start_list < 0:
                    self.start_list = 0
                self.stop_list = self.scroll_size
            else:
                return # Cannot scroll up any further
        elif _COMMAND_KEYS[key] == 'ARROW_DN':
            if self.end_list < len(self.list_data[1]):
                self.start_list = self.end_list
                self.end_list += self.scroll_size
                if self.end_list > len(self.list_data[1]):
                    self.end_list = len(self.list_data[1])
            else:
                return # Cannot scroll down any further
        else:
            return # Not a valid scroll key
        self._print_list(True)


    def _print_list(self, refresh=True, comment=None):
        """Display the list information
        
        This method displays the list information using the start_list and
        end_list member variables to control the view of the data. This
        permits users to scroll through the data should it be longer than
        the space permitted on the screen.
        """
        from mysql.utilities.common.format import print_list

        # If no data to print, exit
        if self.list_data is None:
            return

        if refresh:
            self.clear()
            self._print_header()
            self._print_master_status()

        # Print list name
        if comment is None:
            comment = self.comment
        print comment
        self.rows_printed += 1
        
        # Print the list in the remaining space
        footer_len = 2
        remaining_rows = self.max_rows - self.rows_printed - 4 - footer_len
        if len(self.list_data[1][self.start_list:self.end_list]) > remaining_rows:
            rows = self.list_data[1][self.start_list:self.start_list+remaining_rows]
            self.end_list = self.start_list+remaining_rows
            self.scroll_on = True
        else:
            if len(self.list_data[1]) == self.end_list and self.start_list == 0:
                self.scroll_on = False
            rows = self.list_data[1][self.start_list:self.end_list]
        if len(rows) > 0:
            self.scroll_size = len(rows)
            print_list(sys.stdout, 'GRID', self.list_data[0], rows)
            self.rows_printed += self.scroll_size + 4
        else:
            print "0 Rows Found."
            self.rows_printed += 1

        if refresh:
            self._print_footer(self.scroll_on)
    

    def _print_footer(self, scroll=False):
        """Print the footer
        
        This method prints the footer for the console consisting of the
        user commands permitted.
        
        scroll[in]     if True, display scroll commands
        """
        # Print blank lines fill screen
        for i in range(self.rows_printed, self.max_rows-2):
            print
        # Show bottom menu options
        print _CONSOLE_FOOTER,
        # If logging enabled, show command
        if self.logging:
            print "L-log entries",
        if scroll:
            print "Up|Down-scroll"
        else:
            print
        self.rows_printed = self.max_rows
   
    
    def _refresh(self):
        """Refresh the console
        
        This method redraws the console resetting screen size if the
        command/terminal window was resized since last action.
        """
        self.clear()
        self._reset_screen_size()
        self._print_header()
        self._print_master_status()
        self._print_list(False)
        self._print_footer(self.scroll_on)
        

    def display_console(self):
        """Display the failover console
        
        This method presents the information for the failover console. Since
        there is no UI module in use, it clears the screen and redraws the
        data again. 
        
        It uses the method specified in the constructor for getting and
        refreshing the data.
        
        Returns bool - True = user exit no errors, False = errors
        """
        self._reset_interval()

        # Get the data for first printing of the screen
        if self.list_data is None:
            self.list_data = self.get_health_data()
            self.start_list = 0
            self.end_list = len(self.list_data[1])
            self.gtid_list = -1   # Reset the GTID list counter
                    
        # Draw the screen
        self._refresh()
        
        # Wait for a key press or the interval to expire
        done = False
        while not done:
            key = self._wait_for_interval()
            if key is None:
                return None
            if key in ['Q','q']:
                return True
            else:
                self._do_command(key)

        return False
    
