CREATE DATABASE util_test_a
CREATE DATABASE util_test_b
CREATE DATABASE util_test_c

CREATE TABLE util_test_a.`t1` (`A` int(11) NOT NULL DEFAULT '0', `b` varchar(2) DEFAULT NULL, `c` varchar(255) DEFAULT NULL, `d` point NOT NULL, `e` geometry NOT NULL, PRIMARY KEY (`A`), SPATIAL KEY `s1` (`e`), SPATIAL KEY `s2` (`d`), SPATIAL KEY `s4` (`d`)) ENGINE=MyISAM DEFAULT CHARSET=latin1
CREATE TABLE util_test_a.`t2` (`id` int(11) DEFAULT NULL, KEY `id` (`id`) USING HASH) ENGINE=MyISAM DEFAULT CHARSET=latin1
CREATE TABLE util_test_b.`t3` (`id` int(11) DEFAULT NULL, KEY `id` (`id`) USING HASH) ENGINE=MEMORY DEFAULT CHARSET=latin1
CREATE TABLE util_test_b.`t4` (`id` int(11) DEFAULT NULL, KEY `id` (`id`) USING BTREE) ENGINE=MEMORY DEFAULT CHARSET=latin1
CREATE TABLE util_test_c.`t5` (`x` int(11) DEFAULT NULL, `y` varchar(255) DEFAULT NULL, `a` varchar(255) DEFAULT NULL, `b` varchar(255) DEFAULT NULL, `c` varchar(255) DEFAULT NULL, FULLTEXT KEY `ft` (`y`), FULLTEXT KEY `ft1` (`y`), FULLTEXT KEY `ft2` (`a`,`b`,`c`), FULLTEXT KEY `ft3` (`a`,`b`), FULLTEXT KEY `ft4` (`a`,`b`,`y`), FULLTEXT KEY `ft5` (`y`,`a`,`b`), FULLTEXT KEY `ft6` (`c`,`a`,`b`)) ENGINE=MyISAM DEFAULT CHARSET=latin1
CREATE TABLE util_test_c.`t6` (a char(30))
