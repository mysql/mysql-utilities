CREATE DATABASE views_test;
CREATE TABLE views_test.t1(a serial, b int);
CREATE TABLE views_test.t2 like views_test.t1;
CREATE VIEW views_test.x1 as select t1.a as a, t1.b as b1, t2.b as b2 from views_test.t1 join views_test.t2 using (a);
CREATE VIEW views_test.y1 as select t1.a as a, t1.b as b1, t2.b as b2 from views_test.t1 join views_test.t2 using (a);
CREATE VIEW views_test.z1 as select t1.a as a, t1.b as b1, t2.b as b2 from views_test.t1 join views_test.t2 using (a);
CREATE VIEW views_test.b1 as select x1.a as a, x1.b1 as b1, y1.b1 as b2 from views_test.x1 join views_test.y1 using (a);
