# DROP DATABASE IF EXISTS `db``:db`;

CREATE DATABASE `db``:db`;

CREATE TABLE `db``:db`.```t``export_1` (`id``` int not null primary key auto_increment, other char(30)) ENGINE=InnoDB;
CREATE TABLE `db``:db`.```t``.``export_2` (`id``` int not null primary key auto_increment, other char(30)) ENGINE=InnoDB;

INSERT INTO `db``:db`.```t``export_1` (other) VALUES ("@`var``var`");
INSERT INTO `db``:db`.```t``.``export_2` (other) VALUES ("@`var`.`var`");

USE `db``:db`;

CREATE FUNCTION `fu``nc`(`a``` TEXT) RETURNS TEXT DETERMINISTIC RETURN `a```;

# NOTE: There is a bug in MySQL server 5.6.10 when backticks are used to create a trigger 
# (i.e., The ACTION_STATEMENT value in INFORMATION_SCHEMA.TRIGGERS is incorrect).
# Uncomment the trigger creation statment in a later release, once the bug is fixed.
# CREATE TRIGGER `trg``1` AFTER INSERT ON `db``:db`.```t``export_1` FOR EACH ROW INSERT INTO `db``:db`.```t``.``export_2` (other) VALUES (`fu``nc`(new.other));

CREATE PROCEDURE `pr````oc`() INSERT INTO `db``:db`.```t``export_1` (other) VALUES ("proc->trigger->func");

CREATE VIEW `db``:db`.```v``export_1` as SELECT * FROM `db``:db`.```t``export_1`;

CREATE EVENT `db``:db`.```e``export_1` ON SCHEDULE EVERY 1 YEAR DISABLE DO DELETE FROM `db``:db`.```t``export_1` WHERE other = "not there";

GRANT ALL ON `db``:db`.* TO 'joe'@'user';

