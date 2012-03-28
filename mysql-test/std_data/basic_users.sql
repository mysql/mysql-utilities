DROP DATABASE IF EXISTS util_test;
CREATE DATABASE util_test;
GRANT ALL ON util_test.* TO 'joe_nopass'@'user';
GRANT SELECT ON util_test.* TO 'joe_pass'@'user' IDENTIFIED BY 'dumb';
GRANT INSERT ON util_test.* TO 'amy_nopass'@'user';  
