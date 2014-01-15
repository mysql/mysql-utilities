
_COMMANDS_COMMON = {
    "5.5": [("5.5", "--start-and-exit --user-args "
                    "--mysqld=--server-id={server_id} "
                    "--mysqld=--report-host=localhost"
                    "--mysqld=--log-bin=bin-log"
                    "--mysqld=--log-slave-updates")],

    "5.6": [("5.6 with GTIDs", "--start-and-exit --user-args "
                               "--mysqld=--server-id={server_id} "
                               "--mysqld=--gtid-mode=on "
                               "--mysqld=--enforce-gtid-consistency=on "
                               "--mysqld=--log-bin=bin-log "
                               "--mysqld=--log-slave-updates "
                               "--mysqld=--report-host=localhost "
                               "--mysqld=--master-info-repository=TABLE"),
            ("5.6 without GTIDs", "--start-and-exit --user-args "
                                  "--mysqld=--server-id={server_id} "
                                  "--mysqld=--log-bin=bin-log "
                                  "--mysqld=--log-slave-updates "
                                  "--mysqld=--report-host=localhost "
                                  "--mysqld=--master-info-repository=TABLE")],
    "5.7": [("5.7 with GTIDs", "--start-and-exit --user-args "
                               "--mysqld=--server-id={server_id} "
                               "--mysqld=--gtid-mode=on "
                               "--mysqld=--enforce-gtid-consistency=on "
                               "--mysqld=--log-bin=bin-log "
                               "--mysqld=--log-slave-updates "
                               "--mysqld=--report-host=localhost "
                               "--mysqld=--master-info-repository=TABLE"),
            ("5.7 without GTIDs", "--start-and-exit --user-args "
                                  "--mysqld=--server-id={server_id} "
                                  "--mysqld=--log-bin=bin-log "
                                  "--mysqld=--log-slave-updates "
                                  "--mysqld=--report-host=localhost "
                                  "--mysqld=--master-info-repository=TABLE")],

    "5.6.8": [("5.6.8 with GTIDs", "--start-and-exit --user-args "
                                   "--mysqld=--server-id={server_id} "
                                   "--mysqld=--gtid-mode=on "
                                   "--mysqld=--log-bin=bin-log "
                                   "--mysqld=--log-slave-updates "
                                   "--mysqld=--report-host=localhost "
                                   "--mysqld=--master-info-repository=TABLE "
                                   "--mysqld=--disable-gtid-unsafe-statements")
              ],
    "5.6.9": [("5.6.9 with GTIDs", "--start-and-exit --user-args "
                                   "--mysqld=--server-id={server_id} "
                                   "--mysqld=--gtid-mode=on "
                                   "--mysqld=--enforce-gtid-consistency=on "
                                   "--mysqld=--log-bin=bin-log "
                                   "--mysqld=--log-slave-updates "
                                   "--mysqld=--report-host=localhost "
                                   "--mysqld=--master-info-repository=TABLE")
              ]
}
COMMANDS_LINUX = {
    "5.1": [("5.1", "--start-and-exit --user-args "
                    "--mysqld=--ignore-builtin-innodb "
                    "--mysqld=--plugin-load=innodb=ha_innodb_plugin.so "
                    "--mysqld=--default_storage_engine=InnoDB "
                    "--mysqld=--innodb_file_per_table=1 "
                    "--mysqld=--innodb_file_format=barracuda "
                    "--mysqld=--innodb_strict_mode=1 "
                    "--mysqld=--server-id={server_id} "
                    "--mysqld=--report-host=localhost "
                    "--mysqld=--log-bin=bin-log")]
}
COMMANDS_LINUX.update(_COMMANDS_COMMON)

COMMANDS_WINDOWS = {
    "5.1": [("5.1", "--start-and-exit --user-args "
                    "--mysqld=--ignore-builtin-innodb "
                    "--mysqld=--plugin-load=innodb=ha_innodb_plugin.dll "
                    "--mysqld=--default_storage_engine=InnoDB "
                    "--mysqld=--innodb_file_per_table=1 "
                    "--mysqld=--innodb_file_format=barracuda "
                    "--mysqld=--innodb_strict_mode=1 "
                    "--mysqld=--server-id={server_id} "
                    "--mysqld=--report-host=localhost "
                    "--mysqld=--log-bin=bin-log")]
}
COMMANDS_WINDOWS.update(_COMMANDS_COMMON)
