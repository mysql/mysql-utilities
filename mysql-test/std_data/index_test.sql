CREATE DATABASE `util_test_a`
CREATE DATABASE `util_test_b`
CREATE DATABASE `util_test_c`
CREATE DATABASE `util_test_d`
CREATE DATABASE `util_test_e`
CREATE DATABASE `util_test_f`
CREATE DATABASE `util_test_g`

CREATE TABLE `util_test_a`.`t1` (`A` int(11) NOT NULL DEFAULT '0', `b` varchar(2) DEFAULT NULL, `c` varchar(255) DEFAULT NULL, `d` point NOT NULL, `e` geometry NOT NULL, PRIMARY KEY (`A`), SPATIAL KEY `s1` (`e`), SPATIAL KEY `s2` (`d`), SPATIAL KEY `s4` (`d`)) ENGINE=MyISAM DEFAULT CHARSET=latin1
CREATE TABLE `util_test_a`.`t2` (`id` int(11) DEFAULT NULL, KEY `id` (`id`) USING HASH) ENGINE=MyISAM DEFAULT CHARSET=latin1
CREATE TABLE `util_test_b`.`t3` (`id` int(11) DEFAULT NULL, KEY `id` (`id`) USING HASH) ENGINE=MEMORY DEFAULT CHARSET=latin1
CREATE TABLE `util_test_b`.`t4` (`id` int(11) DEFAULT NULL, KEY `id` (`id`) USING BTREE) ENGINE=MEMORY DEFAULT CHARSET=latin1
CREATE TABLE `util_test_c`.`t5` (`x` int(11) DEFAULT NULL, `y` varchar(255) DEFAULT NULL, `a` varchar(255) DEFAULT NULL, `b` varchar(255) DEFAULT NULL, `c` varchar(255) DEFAULT NULL, FULLTEXT KEY `ft` (`y`), FULLTEXT KEY `ft1` (`y`), FULLTEXT KEY `ft2` (`a`,`b`,`c`), FULLTEXT KEY `ft3` (`a`,`b`), FULLTEXT KEY `ft4` (`a`,`b`,`y`), FULLTEXT KEY `ft5` (`y`,`a`,`b`), FULLTEXT KEY `ft6` (`c`,`a`,`b`)) ENGINE=MyISAM DEFAULT CHARSET=latin1
CREATE TABLE `util_test_c`.`t6` (a char(30))
CREATE TABLE `util_test_d`.`cluster_idx` (`id` int(11) NOT NULL AUTO_INCREMENT, `col2` int(11) DEFAULT NULL, `col3` varchar(200) DEFAULT NULL, PRIMARY KEY (`id`), KEY `col2` (`col2`), KEY `redundant` (`col2`,`id`)) ENGINE=InnoDB DEFAULT CHARSET=latin1
CREATE TABLE `util_test_d`.`no_cluster_idx` (`id` int(11) NOT NULL AUTO_INCREMENT, `col2` int(11) DEFAULT NULL, `col3` varchar(200) DEFAULT NULL, PRIMARY KEY (`id`), KEY `col2` (`col2`), KEY `redundant` (`col2`,`id`)) ENGINE=MyISAM DEFAULT CHARSET=latin1
CREATE TABLE `util_test_d`.`various_cluster_idx` (`id` int(11) NOT NULL AUTO_INCREMENT, `col2` int(11) DEFAULT NULL, `col3` varchar(200) DEFAULT NULL, PRIMARY KEY (`id`), KEY `col2` (`col2`), KEY `col2_2` (`col2`), KEY `redundant` (`col2`,`id`), KEY `another_redundant` (`col3`,`id`)) ENGINE=InnoDB DEFAULT CHARSET=latin1

# These test cases are designed for the case of a PRIMARY key that was marked as duplicated of an unique index with more columns.
CREATE TABLE `util_test_f`.`t1` ( `id` int(11) NOT NULL, `a1` int(11) NOT NULL, `a2` int(11) NOT NULL, `a3` int(11) NOT NULL, `a4` int(11) NOT NULL, PRIMARY KEY (`id`), UNIQUE KEY (`id`,`a1`), UNIQUE KEY `i2` (`a1`,`a3`,`a4`), KEY `i1` (`a1`,`a2`,`a3`)) ENGINE=MyISAM DEFAULT CHARSET=latin1;
CREATE TABLE `util_test_f`.`t2` ( `id` int(11) NOT NULL, `a1` int(11) NOT NULL, `a2` int(11) NOT NULL, `a3` int(11) NOT NULL, `a4` int(11) NOT NULL, PRIMARY KEY (`id`,`a1`), UNIQUE KEY `id` (`id`,`a1`), UNIQUE KEY `a1` (`id`), UNIQUE KEY `i2` (`a1`,`a3`,`a4`), UNIQUE KEY `id3` (`id`,`a1`,`a2`) USING BTREE,  KEY `i1` (`a1`,`a2`,`a3`)) ENGINE=MyISAM DEFAULT CHARSET=latin1;
CREATE TABLE `util_test_f`.`qted_``2_quoted_``2` ( `c``1` int, `c``2` int not null, c3 int not null, c4 int not null, c5 int, c6 int not null, UNIQUE `uk_no``nonulls` (`c``2`, `c6`), INDEX `ix_no``nulls` (`c``2`, `c6`, `c4`), INDEX `ix_no``nulls_``2` (`c``2`, `c6`), INDEX `ix_1` (`c``1`, `c5`), INDEX `ix_2` (`c``1`, `c5`), INDEX `ix_3` (`c5`), UNIQUE KEY `ix``_c` (`c``1`, `c6`), UNIQUE KEY `ix_c2` (`c``1`, `c6`, `c``2`)) ENGINE=InnoDB DEFAULT CHARSET=latin1;

# These test cases are designed for the --report-indexes option of mysqlindexcheck and --show-indexes with -vv
CREATE TABLE `util_test_e`.`t1` (a int(11)) ENGINE=InnoDB DEFAULT CHARSET=latin1;
CREATE TABLE `util_test_e`.`t2` (a int(11), b int(11), c int(11), key(`b`)) ENGINE=InnoDB DEFAULT CHARSET=latin1;
CREATE TABLE `util_test_e`.`t3` (a int(11), b int(11), c int(11), UNIQUE key(`b`)) ENGINE=InnoDB DEFAULT CHARSET=latin1;
CREATE TABLE `util_test_e`.`t4` (a int(11), b int(11), c int(11), PRIMARY key(`b`)) ENGINE=InnoDB DEFAULT CHARSET=latin1;
CREATE TABLE `util_test_e`.`t5` (a int(11) NOT NULL, b int(11), c int(11), UNIQUE key(`a`)) ENGINE=InnoDB DEFAULT CHARSET=latin1;

# These test cases are designed to test redundant index detection on indexes that are only a partial match

CREATE TABLE `util_test_g`.`t1` (`id` int(11) NOT NULL, `a1` int(11) NOT NULL, `a2` int(11) NOT NULL, `a3` int(11) NOT NULL, `a4` int(11) NOT NULL, PRIMARY KEY (`id`), UNIQUE KEY (`id`,`a1`), UNIQUE KEY `bti2` (`a1`,`a3`,`a4`), KEY `bti1` (`a1`,`a2`,`a3`), KEY `bti3` (`a1`,`a2`), KEY `bti4` (`a1`,`a3`), KEY `bti5` (`a2`,`a3`)) ENGINE=MyISAM DEFAULT CHARSET=latin1;
CREATE TABLE `util_test_g`.`t2` (`id` int(11) NOT NULL, `b1` int(11) NOT NULL, `b2` int(11) NOT NULL, PRIMARY KEY (`id`) USING HASH, UNIQUE KEY (`id`,`b1`) USING HASH, UNIQUE KEY `hi2` (`b2`,`b1`) USING HASH, KEY `hi1` (`b1`,`b2`) USING HASH, KEY `hi3` (`b1`,`b2`, `id`) USING HASH, KEY `hi4` (`b1`) USING HASH, KEY `hi5` (`b1`,`b2`) USING HASH) ENGINE=MEMORY;
CREATE TABLE `util_test_g`.`t3` (`x` int(11) DEFAULT NULL, `y` varchar(255) DEFAULT NULL, `a` varchar(255) DEFAULT NULL, `b` varchar(255) DEFAULT NULL, `c` varchar(255) DEFAULT NULL, FULLTEXT KEY `ft` (`c`), FULLTEXT KEY `ft1` (`y`), FULLTEXT KEY `ft2` (`a`,`b`,`c`), FULLTEXT KEY `ft3` (`a`,`b`), FULLTEXT KEY `ft4` (`a`,`b`,`y`), FULLTEXT KEY `ft5` (`y`,`a`,`b`), FULLTEXT KEY `ft6` (`c`,`a`,`b`), FULLTEXT KEY `ft7` (`a`,`y`,`c`)) ENGINE=MyISAM DEFAULT CHARSET=latin1;
