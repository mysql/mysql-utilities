DROP DATABASE IF EXISTS `db``:db`;

CREATE DATABASE `db``:db`;

CREATE TABLE `db``:db`.```t``export_1` (`id``` int not null primary key auto_increment, other char(30)) ENGINE=InnoDB DEFAULT CHARSET=latin1;
CREATE TABLE `db``:db`.```t``.``export_2` (`id``` int not null primary key auto_increment, other char(30)) ENGINE=InnoDB DEFAULT CHARSET=latin1;

INSERT INTO `db``:db`.```t``export_1` (other) VALUES ("@`var``var1`");
INSERT INTO `db``:db`.```t``export_1` (other) VALUES ("@`var``var2`");
INSERT INTO `db``:db`.```t``export_1` (other) VALUES ("@`var``var3`");
INSERT INTO `db``:db`.```t``export_1` (other) VALUES ("@`var``var4`");
INSERT INTO `db``:db`.```t``export_1` (other) VALUES ("@`var``var5`");
INSERT INTO `db``:db`.```t``.``export_2` (other) VALUES ("@`var`.`var1`");
INSERT INTO `db``:db`.```t``.``export_2` (other) VALUES ("@`var`.`var2`");
INSERT INTO `db``:db`.```t``.``export_2` (other) VALUES ("@`var`.`var3`");

USE `db``:db`;

CREATE VIEW `db``:db`.```v``export_1` as SELECT * FROM `db``:db`.```t``export_1`;

