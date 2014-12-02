#
# DROP DATABASE IF EXISTS util_test_fk;
#
# NOTE: Must load with FKey checks OFF. This is so a1 is 'created' before
#       t1 to show proper functioning.
#
CREATE DATABASE util_test_fk;
USE util_test_fk;
CREATE TABLE util_test_fk.a1 (a int DEFAULT 0, b char(20), c int, PRIMARY KEY(a), CONSTRAINT c FOREIGN KEY (c) REFERENCES `util_test_fk`.`t1`(d)) ENGINE=INNODB;
CREATE TABLE util_test_fk.t1 (d int DEFAULT 0, b char(20), PRIMARY KEY(d)) ENGINE=INNODB;
INSERT INTO util_test_fk.t1 VALUES (1, 'one'), (2, 'two'), (3, 'three');
INSERT INTO util_test_fk.a1 VALUES (4, 'four', 1), (5, 'five', 2), (6, 'six', 3), (7, NULL, 3);

CREATE DATABASE util_test_fk2;
USE util_test_fk2;
CREATE TABLE util_test_fk2.a2 (a int DEFAULT 0, b char(20), fc int, fd int, PRIMARY KEY(a), CONSTRAINT `fk_fc_fd` FOREIGN KEY (fc,fd) REFERENCES `util_test_fk2`.`t2`(c,d) ON UPDATE CASCADE) ENGINE=INNODB;
CREATE TABLE util_test_fk2.t2 (c int DEFAULT 0, d int DEFAULT 0, a int, PRIMARY KEY (c,d), CONSTRAINT `fk_t1_a` FOREIGN KEY (a) REFERENCES `util_test_fk`.`a1`(a)) ENGINE=INNODB;
CREATE TABLE util_test_fk2.t3 (x int DEFAULT 0, c int , d int, a int, PRIMARY KEY (x), CONSTRAINT `fk_a1_1` FOREIGN KEY (a) references `util_test_fk`.`a1`(a), CONSTRAINT `fk2_t2_cd` FOREIGN KEY (c,d) REFERENCES `util_test_fk2`.`t2`(c,d)) ENGINE=INNODB;
INSERT INTO util_test_fk2.t2 VALUES(1,1,4);
INSERT INTO util_test_fk2.t3 VALUES(23,1,1,1);
INSERT INTO util_test_fk2.a2 VALUES(6,'bar',1,1);

CREATE DATABASE util_test_fk3;
USE util_test_fk3;
CREATE TABLE util_test_fk2.m (a int NOT NULL DEFAULT 0, b char(20), PRIMARY KEY (a)) ENGINE=MYISAM;
INSERT INTO util_test_fk2.m VALUES(1,'foo');
