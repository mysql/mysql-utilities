DROP DATABASE IF EXISTS `blob_test`;
CREATE DATABASE `blob_test`;
CREATE TABLE `blob_test`.`blob_table` (`a` MEDIUMINT(11) NOT NULL AUTO_INCREMENT, `b` TINYTEXT, `c` BLOB, PRIMARY KEY (`a`)) ENGINE=InnoDB;
INSERT INTO `blob_test`.`blob_table` VALUES (NULL, 'test', 0xff0e);

CREATE TABLE `blob_test`.`text_table`( text_col TINYTEXT);
INSERT INTO `blob_test`.`text_table` VALUES ('This is a test');
INSERT INTO `blob_test`.`text_table` VALUES ('This is a test 2');
INSERT INTO `blob_test`.`text_table` VALUES ('This is a test 3 with special characters: \0\'\"\b\n\r\t\Z\\\%\_');

CREATE TABLE blob_test.blobs(text_col TINYTEXT, bin_col BINARY, blob_col BLOB) ENGINE=InnoDB;
INSERT INTO blob_test.blobs VALUES('playing guitar must be cool!', 1, 0xff0e);
INSERT INTO blob_test.blobs VALUES('riding a bicycle` is cool!', 2, 0xff0e);
INSERT INTO blob_test.blobs VALUES('python is pretty cool!', 3, 0xff0e);
INSERT INTO blob_test.blobs VALUES(NULL, NULL, NULL);

CREATE TABLE blob_test.blobs_pk(text_col MEDIUMTEXT, bin_col BINARY, blob_col BLOB, int_col INT, char_col VARCHAR(10) ,PRIMARY KEY (int_col)) ENGINE=InnoDB;
INSERT INTO blob_test.blobs_pk VALUES('playing guitar must be cool!', 1, 0xff0e, 1, 'this');
INSERT INTO blob_test.blobs_pk VALUES('riding a bicycle` is cool!', 2, 0xff0e, 2, 'is');
INSERT INTO blob_test.blobs_pk VALUES('python is pretty cool!', 3, 0xff0e, 3, 'strange');
INSERT INTO blob_test.blobs_pk VALUES(NULL, NULL, NULL, 4, '!');
