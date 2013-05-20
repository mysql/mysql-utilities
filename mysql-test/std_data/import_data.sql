CREATE DATABASE `import_test`;
CREATE TABLE `import_test`.`customers` (`id` int(10) unsigned NOT NULL, `name` varchar(255) NOT NULL, PRIMARY KEY (`id`)) ENGINE=InnoDB;

INSERT INTO `import_test`.`customers` (`id`, `name`) VALUES (1, 'Customer 1');
INSERT INTO `import_test`.`customers` (`id`, `name`) VALUES (2, 'Customer 2');
INSERT INTO `import_test`.`customers` (`id`, `name`) VALUES (3, 'Customer 3');
INSERT INTO `import_test`.`customers` (`id`, `name`) VALUES (4, 'Customer 4');
INSERT INTO `import_test`.`customers` (`id`, `name`) VALUES (5, 'Customer 5');
