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

CREATE DATABASE util_test_fk2;
CREATE TABLE util_test_fk2.a2 (a int, b char(20), fc int, fd int, PRIMARY KEY(a), CONSTRAINT `fk_fc_fd` FOREIGN KEY (fc,fd) REFERENCES `util_test_fk2`.`t2`(c,d) ON UPDATE CASCADE) ENGINE=INNODB;
CREATE TABLE util_test_fk2.t2 (c int, d int, a int, PRIMARY KEY (c,d), CONSTRAINT `fk_t1_a` FOREIGN KEY (a) REFERENCES `util_test_fk`.`a1`(a)) ENGINE=INNODB;
INSERT INTO util_test_fk2.t2 VALUES(1,1,3);
INSERT INTO util_test_fk2.a2 VALUES('20','bar',1,1);

CREATE DATABASE util_test_fk3;
CREATE TABLE util_test_fk2.m (a int, b char(20), PRIMARY KEY (a)) ENGINE=MYISAM;
INSERT INTO util_test_fk2.m VALUES(1,'foo');
