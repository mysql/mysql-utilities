.. intro:

########################################
Brief overview of command-line utilities
########################################

This is a brief overview of the MySQL command-line utilities. See their 
respective manual pages for further details and examples:

`mysqldbcompare`
  * Compare databases on two servers or the same server
  * Compare definitions and data
  * Generate a difference report
  * Generate SQL transformation statements

`mysqldbcopy`
  * Copy databases between servers
  * Clone databases on the same server
  * Supports rename

`mysqldbexport`
  * Export metadata and/or data from one or more databases
  * Formats: SQL, CSV, TAB, Grid, Vertical

`mysqldbimport`
  * Import metadata and data from one or more files
  * Reads all formats from mysqldbexport

`mysqldiff`
  * Compare object definitions
  * Generate a difference report

`mysqldiskusage`
  * Show disk usage for databases
  * Generate reports in SQL, CSV, TAB, Grid, Vertical

`mysqlfailover`
  * Performs replication health monitoring
  * Provides automatic failover on a replication topology
  * Uses Global Transaction Identifiers (GTID, MySQL Server 5.6.5+)

`mysqlindexcheck`
  * Read indexes for one or more tables
  * Check for redundant and duplicate indexes
  * Generate reports in SQL, CSV, TAB, Grid, Vertical

`mysqlmetagrep`
  * Search metadata
  * Regexp, database search
  * Generate SQL statement for search query

`mysqlprocgrep`
  * Search process information
  * Generate SQL statement for search
  * Kill processes that match query

`mysqlreplicate`
  * Setup replication
  * Start from beginning, current, specific binlog, pos

`mysqlrpladmin`
  * Administers the replication topology
  * Allows recovery of the master
  * Commands include elect, failover, gtid, health, start, stop, and switchover

`mysqlrplcheck`
  * Check replication configuration
  * Tests binary logging on master

`mysqlrplshow`
  * Show slaves attached to master
  * Can search recursively
  * Show the replication topology as a graph or list

`mysqlserverclone`
  * Start a new instance of a running server

`mysqlserverinfo`
  * Show server information
  * Can search for running servers on a host
  * Access online or offline servers

`mysqluserclone`
  * Clone a user account, to the same or different server
  * Show user grants

`mut`
  * Tests for all utilities
  * Similar to MTR
  * Comparative and value result support
  * Tests written as Python classes
