#
# This test data is for checking database consistency.
#

CREATE DATABASE inventory;
USE inventory;

CREATE TABLE `supplier` (`code` int(11) NOT NULL, `name` char(30) DEFAULT NULL, PRIMARY KEY (`code`)) ENGINE=MyISAM DEFAULT CHARSET=latin1;

CREATE TABLE `supplies` (`stock_number` int(11) NOT NULL DEFAULT '0', `description` char(40) DEFAULT NULL, `qty` int(11) DEFAULT NULL, `cost` float(10,2) DEFAULT NULL, `type` enum('cleaning','washing','waxing','polishing','repair','drying','tools','other') DEFAULT NULL, `notes` char(4) DEFAULT NULL, `supplier` int(11) DEFAULT NULL, PRIMARY KEY (`stock_number`)) ENGINE=MyISAM DEFAULT CHARSET=latin1;

USE inventory;

INSERT INTO inventory.supplier VALUES (1, 'Graniger Garage Guru');

INSERT INTO inventory.supplies VALUES (11056, 'Microfiber and foam pad cleaner', 1, 9.99, 'cleaning', '', 1);
INSERT INTO inventory.supplies VALUES (11136, 'Rubber cleaner', 1, 9.99, 'cleaning', '', 1);
INSERT INTO inventory.supplies VALUES (11065, 'Spray on car wash', 1, 14.99, 'washing', '', 1);
INSERT INTO inventory.supplies VALUES (11138, 'Under carriage spray', 1, 13.99, 'cleaning', '', 1);
INSERT INTO inventory.supplies VALUES (11270, 'Carpet cleaner', 1, 9.99, 'cleaning', '', 1);
INSERT INTO inventory.supplies VALUES (11108, 'Window cleaner', 1, 6.99, 'cleaning', '', 1);
INSERT INTO inventory.supplies VALUES (11146, 'Speed shine', 1, 9.99, 'repair', '', 1);
INSERT INTO inventory.supplies VALUES (11135, 'Paint prep', 1, 12.99, 'repair', '', 1);
INSERT INTO inventory.supplies VALUES (12980, 'Bug off', 1, 14.99, 'other', '', 1);
INSERT INTO inventory.supplies VALUES (11098, 'Spray on wax', 2, 12.99, 'waxing', '', 1);
INSERT INTO inventory.supplies VALUES (11171, 'Best of show wax', 1, 19.99, 'waxing', '', 1);
INSERT INTO inventory.supplies VALUES (11017, 'Fine glass polish', 1, 15.99, 'polishing', '', 1);
INSERT INTO inventory.supplies VALUES (11102, 'Car wash', 1, 7.99, 'washing', '', 1);
INSERT INTO inventory.supplies VALUES (11163, 'Machine polish 3', 1, 14.99, 'polishing', '', 1);
INSERT INTO inventory.supplies VALUES (11186, 'Plastic polish', 1, 9.99, 'polishing', '', 1);
INSERT INTO inventory.supplies VALUES (11185, 'Plastic cleaner', 1, 6.99, 'polishing', '', 1);
INSERT INTO inventory.supplies VALUES (11036, 'Dried on wax remover', 1, 7.99, 'waxing', '', 1);
INSERT INTO inventory.supplies VALUES (11173, 'Vinyl and rubber dressing', 1, 9.99, 'cleaning', '', 1);
INSERT INTO inventory.supplies VALUES (11149, 'Interior scent +AC0- new car', 1, 6.99, 'cleaning', '', 1);
INSERT INTO inventory.supplies VALUES (11153, 'Paint cleaning clay', 1, 19.99, 'cleaning', '', 1);
INSERT INTO inventory.supplies VALUES (11035, 'Wheel cleaning clay', 1, 14.99, 'cleaning', '', 1);
INSERT INTO inventory.supplies VALUES (11263, 'Red wax pad', 1, 4.99, 'waxing', '', 1);
INSERT INTO inventory.supplies VALUES (11241, 'Orange polish pad', 1, 4.99, 'polishing', '', 1);
INSERT INTO inventory.supplies VALUES (90211, 'Window wand set', 1, 8.99, 'cleaning', '', 1);
INSERT INTO inventory.supplies VALUES (10628, 'Red wax pad', 1, 5.99, 'waxing', '', 1);
INSERT INTO inventory.supplies VALUES (10626, 'Orange polish pad', 1, 5.99, 'polishing', '', 1);
INSERT INTO inventory.supplies VALUES (10665, 'Glass polish pad', 3, 9.99, 'polishing', '', 1);
INSERT INTO inventory.supplies VALUES (15736, 'Long wheel cleaning wand set', 1, 12.99, 'cleaning', '', 1);
INSERT INTO inventory.supplies VALUES (15516, 'Dust brush set', 1, 12.99, 'cleaning', '', 1);
INSERT INTO inventory.supplies VALUES (11034, 'Spray nozzles (extra)', 2, 2.99, 'other', '', 1);
INSERT INTO inventory.supplies VALUES (10268, 'Wash mits', 2, 11.99, 'washing', '', 1);
INSERT INTO inventory.supplies VALUES (11117, 'Microfiber drying towel', 1, 26.99, 'drying', '', 1);
INSERT INTO inventory.supplies VALUES (11115, 'Microfiber polish towel', 2, 16.99, 'polishing', '', 1);
INSERT INTO inventory.supplies VALUES (11116, 'Microfiber wax removal towel', 3, 16.99, 'waxing', '', 1);
INSERT INTO inventory.supplies VALUES (11269, 'Microfiber spray on car wash towel', 3, 16.99, 'cleaning', '', 1);
INSERT INTO inventory.supplies VALUES (11104, 'Interior cleaner', 1, 9.99, 'cleaning', '', 1);
INSERT INTO inventory.supplies VALUES (11040, 'Leather care', 1, 9.99, 'other', '', 1);
INSERT INTO inventory.supplies VALUES (11080, 'Microfiber interior cleaning towel', 3, 9.99, 'cleaning', '', 1);
INSERT INTO inventory.supplies VALUES (67260, 'Wash bucket', 1, 39.99, 'tools', '', 1);
INSERT INTO inventory.supplies VALUES (11205, 'Tire dressing applicator', 1, 5.99, 'other', '', 1);
INSERT INTO inventory.supplies VALUES (11049, 'Glass cleaning clay', 1, 12.99, 'cleaning', '', 1);
INSERT INTO inventory.supplies VALUES (11106, 'Wheel cleaner', 1, 9.99, 'cleaning', '', 1);
INSERT INTO inventory.supplies VALUES (11141, 'Leather rejuvenator', 1, 12.99, 'other', '', 1);
INSERT INTO inventory.supplies VALUES (10739, '3 inch orbital - 25 foot cord', 1, 109.99, 'tools', '', 1);
INSERT INTO inventory.supplies VALUES (10765, '6 inch orbital - 10 foot cord', 1, 129.99, 'tools', '', 1);

CREATE VIEW `tools` AS SELECT * FROM inventory.supplies WHERE type in ('tool', 'other');
CREATE VIEW `cleaning` AS SELECT * FROM inventory.supplies WHERE type in ('cleaning','washing');
CREATE VIEW `finishing_up` AS SELECT * FROM inventory.supplies WHERE type in ('waxing','polishing','drying');


