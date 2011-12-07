#
# This file is a variant of the basic_data.sql file and is used for doing
# compares and generating tests for transofmations.
#
#DROP DATABASE IF EXISTS util_test;
#
CREATE DATABASE util_test;
CREATE TABLE util_test.t1 (a char(30)) ENGINE=MEMORY;
INSERT INTO util_test.t1 VALUES ("01 Test Basic database example"); 
INSERT INTO util_test.t1 VALUES ("02 Test Basic mod1 database example"); 
INSERT INTO util_test.t1 VALUES ("03 Test Basic database example"); 
INSERT INTO util_test.t1 VALUES ("04 Test Basic database example"); 
INSERT INTO util_test.t1 VALUES ("05 Test Basic mod2 database example"); 
INSERT INTO util_test.t1 VALUES ("06 Test Basic database example"); 
INSERT INTO util_test.t1 VALUES ("08 Test Basic database example"); 

CREATE TABLE util_test.t2 (a char(30)) ENGINE=MYISAM;
INSERT INTO util_test.t2 VALUES ("11 Test Basic database example"); 
INSERT INTO util_test.t2 VALUES ("12 modified Basic database example"); 
INSERT INTO util_test.t2 VALUES ("13 Test Basic database example"); 

CREATE TABLE util_test.t3 (a int not null auto_increment, d char(30), primary key(a)) ENGINE=MYISAM;
INSERT INTO util_test.t3 (d) VALUES ("14 test fkeys");
INSERT INTO util_test.t3 (d) VALUES ("15 test fkeys");
INSERT INTO util_test.t3 (d) VALUES ("16 test fkeys");

CREATE TABLE util_test.t4 (c int not null, d int not null) ENGINE=MYISAM;
INSERT INTO util_test.t4 VALUES (3, 2);

CREATE PROCEDURE util_test.p1(p1 CHAR(20)) INSERT INTO util_test.t2 VALUES ("100");

CREATE TRIGGER util_test.trg BEFORE UPDATE ON util_test.t1 FOR EACH ROW INSERT INTO util_test.t1 VALUES('Wax on, wax off');

CREATE FUNCTION util_test.f1() RETURNS INT DETERMINISTIC RETURN (SELECT -1);

CREATE VIEW util_test.v1 as SELECT * FROM util_test.t2;

GRANT ALL ON util_test.* TO 'joe'@'user';
