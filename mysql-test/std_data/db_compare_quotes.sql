CREATE DATABASE compare_db_quotes_1;
CREATE DATABASE compare_db_quotes_2;
CREATE TABLE compare_db_quotes_1.t1(id int not null auto_increment primary key, name varchar(100)) ENGINE=INNODB;
CREATE TABLE compare_db_quotes_2.t1(id int not null auto_increment primary key, name varchar(100)) ENGINE=INNODB;
INSERT INTO compare_db_quotes_1.t1(name) values("single quote' bug");
INSERT INTO compare_db_quotes_2.t1(name) values("single quote bug");
