CREATE DATABASE compare_db_pkeys_db1;
CREATE DATABASE compare_db_pkeys_db2;
CREATE TABLE compare_db_pkeys_db1.t (a int, b int, c int, primary key (a, b)) ENGINE=INNODB;
CREATE TABLE compare_db_pkeys_db2.t (a int, b int, c int, primary key (a, b)) ENGINE=INNODB;
INSERT INTO compare_db_pkeys_db1.t (a, b, c) VALUES (1, 2, 3);
INSERT INTO compare_db_pkeys_db2.t (a, b, c) VALUES (1, 2, 4);
