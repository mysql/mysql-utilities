CREATE DATABASE views_test;

CREATE TABLE views_test.t1 (a int not null, b int not null) ENGINE=InnoDB;
INSERT INTO views_test.t1 VALUES (3, 2);

CREATE VIEW views_test.v1 AS SELECT views_test.t1.a,views_test.t1.b FROM views_test.t1;
CREATE VIEW views_test.v2 AS SELECT views_test.t1.a,(views_test.t1.b + 1) FROM views_test.t1;
CREATE VIEW views_test.v3 AS SELECT views_test.t1.a, (views_test.t1.b + 1) FROM views_test.t1;
SET @previous_sql_mode = @@session.sql_mode;
SET @@session.sql_mode = 'ANSI_QUOTES';
CREATE VIEW "views_test"."v4" AS SELECT "views_test"."t1"."a","views_test"."t1"."b" FROM "views_test"."t1";
CREATE VIEW "views_test"."v5" AS SELECT "views_test"."t1"."a", "views_test"."t1"."b" FROM "views_test"."t1";
CREATE VIEW "views_test"."v6" AS SELECT "views_test"."t1"."a",("views_test"."t1"."b" + 1) FROM "views_test"."t1";
CREATE VIEW "views_test"."v7" AS SELECT "views_test"."t1"."a", ("views_test"."t1"."b" + 1) FROM "views_test"."t1";
SET @@session.sql_mode = @previous_sql_mode;
CREATE VIEW `views_test`.`v8` AS SELECT `views_test`.`t1`.`a`,`views_test`.`t1`.`b` FROM `views_test`.`t1`;
CREATE VIEW `views_test`.`v9` AS SELECT `views_test`.`t1`.`a`, `views_test`.`t1`.`b` FROM `views_test`.`t1`;
CREATE VIEW `views_test`.`v10` AS SELECT `views_test`.`t1`.`a`,(`views_test`.`t1`.`b` + 1) FROM `views_test`.`t1`;
CREATE VIEW `views_test`.`v11` AS SELECT `views_test`.`t1`.`a`, (`views_test`.`t1`.`b` + 1) FROM `views_test`.`t1`;
