#
# DROP DATABASE IF EXISTS util_test_fk;
#
# NOTE: Must load with FKey checks OFF. This is so a1 is 'created' before
#       t1 to show proper functioning.
#
CREATE DATABASE util_test_fk;
CREATE TABLE util_test_fk.a1 (a int, b char(20), c int, PRIMARY KEY(a), CONSTRAINT c FOREIGN KEY (c) REFERENCES t1(d)) ENGINE=INNODB;
CREATE TABLE util_test_fk.t1 (d int, b char(20), PRIMARY KEY(d)) ENGINE=INNODB;
INSERT INTO util_test_fk.t1 VALUES (1, 'one'), (2, 'two'), (3, 'three');
INSERT INTO util_test_fk.a1 VALUES (4, 'four', 1), (5, 'five', 2), (6, 'six', 3), (7, NULL, 3);

