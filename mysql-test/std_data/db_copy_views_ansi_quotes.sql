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
# Create views with dependencies (to test copy/import order).
CREATE VIEW `views_test`.`v13` AS SELECT 1 AS value;
CREATE VIEW `views_test`.`v12` AS SELECT * FROM `views_test`.`v13`;
CREATE VIEW `views_test`.`v14` AS SELECT * FROM `views_test`.`v12`;
# Create view with dependency on join of views
CREATE VIEW `views_test`.`v0` (a, a1, b1) AS SELECT * FROM `views_test`.`v14` inner join `views_test`.`v2`;
CREATE VIEW `views_test`.`v15` (a, a1, b1, a2, b2) AS SELECT * FROM `views_test`.`v0` inner join `views_test`.`v1`;
