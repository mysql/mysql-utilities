#
# DROP DATABASE IF EXISTS util_test_keys;
#
CREATE DATABASE util_test_keys;
CREATE TABLE util_test_keys.t1 (a int DEFAULT 0, b int, c int, d char(30)) ENGINE=INNODB;
INSERT INTO util_test_keys.t1 VALUES (1, 2, 3, 'four');
INSERT INTO util_test_keys.t1 VALUES (2, 3, 5, 'five');
INSERT INTO util_test_keys.t1 VALUES (3, 4, 6, 'six');
INSERT INTO util_test_keys.t1 VALUES (4, 2, 2, 'two');
INSERT INTO util_test_keys.t1 VALUES (5, 6, 9, 'nine');
ALTER TABLE util_test_keys.t1 ADD PRIMARY KEY (a);

CREATE TABLE util_test_keys.t2 (a int DEFAULT 0, b int DEFAULT 0, c int, d char(30)) ENGINE=INNODB;
ALTER TABLE util_test_keys.t2 ADD PRIMARY KEY (a, b);
ALTER TABLE util_test_keys.t2 ENGINE = InnoDB;
INSERT INTO util_test_keys.t2 (a, b, c, d) SELECT a, b, c, d FROM util_test_keys.t1;

CREATE TABLE util_test_keys.t3 (a int DEFAULT 0, b int DEFAULT 0, c int DEFAULT 0, d char(30)) ENGINE=INNODB;
ALTER TABLE util_test_keys.t3 ADD PRIMARY KEY (a, b, c);
ALTER TABLE util_test_keys.t3 ENGINE = InnoDB;
INSERT INTO util_test_keys.t3 (a, b, c, d) SELECT a, b, c, d FROM util_test_keys.t1;
