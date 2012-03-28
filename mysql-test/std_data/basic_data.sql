#
# DROP DATABASE IF EXISTS util_test;
#
CREATE DATABASE util_test;
CREATE TABLE util_test.t1 (a char(30)) ENGINE=MEMORY;
INSERT INTO util_test.t1 VALUES ("01 Test Basic database example"); 
INSERT INTO util_test.t1 VALUES ("02 Test Basic database example"); 
INSERT INTO util_test.t1 VALUES ("03 Test Basic database example"); 
INSERT INTO util_test.t1 VALUES ("04 Test Basic database example"); 
INSERT INTO util_test.t1 VALUES ("05 Test Basic database example"); 
INSERT INTO util_test.t1 VALUES ("06 Test Basic database example"); 
INSERT INTO util_test.t1 VALUES ("07 Test Basic database example"); 

CREATE TABLE util_test.t2 (a char(30)) ENGINE=MYISAM;
INSERT INTO util_test.t2 VALUES ("11 Test Basic database example"); 
INSERT INTO util_test.t2 VALUES ("12 Test Basic database example"); 
INSERT INTO util_test.t2 VALUES ("13 Test Basic database example"); 

CREATE TABLE util_test.t3 (a int not null auto_increment, b char(30), primary key(a)) ENGINE=InnoDB;
INSERT INTO util_test.t3 (b) VALUES ("14 test fkeys");
INSERT INTO util_test.t3 (b) VALUES ("15 test fkeys");
INSERT INTO util_test.t3 (b) VALUES ("16 test fkeys");

CREATE TABLE util_test.t4 (c int not null, d int not null, CONSTRAINT ref_t3 FOREIGN KEY(c) REFERENCES util_test.t3(a)) ENGINE=InnoDB;
INSERT INTO util_test.t4 VALUES (3, 2);

CREATE PROCEDURE util_test.p1(p1 CHAR(20)) INSERT INTO util_test.t1 VALUES ("50");

CREATE TRIGGER util_test.trg AFTER INSERT ON util_test.t1 FOR EACH ROW INSERT INTO util_test.t2 VALUES('Test objects count');

CREATE FUNCTION util_test.f1() RETURNS INT DETERMINISTIC RETURN (SELECT 1);

CREATE VIEW util_test.v1 as SELECT * FROM util_test.t1;

CREATE EVENT util_test.e1 ON SCHEDULE EVERY 1 YEAR DISABLE DO DELETE FROM util_test.t1 WHERE a = "not there";

GRANT ALL ON util_test.* TO 'joe'@'user';
