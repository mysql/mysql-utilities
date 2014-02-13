DROP DATABASE IF EXISTS no_primary_keys;
CREATE DATABASE no_primary_keys;

CREATE TABLE no_primary_keys.nonix_1_simple (c1 int, c2 int not null, c3 int not null, c4 int not null, c5 int, c6 int not null, UNIQUE `uk_nonullclmns` ( `c6`), INDEX `ix_nonull` (`c4`)) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE no_primary_keys.nonix_1_nix_2 (c1 int, c2 int not null, c3 int not null, c4 int not null, c5 int, c6 int not null, UNIQUE `uk_nonulls` (`c2`, `c6`), INDEX `ix_nonulls` (`c4`, `c3`), INDEX `ix_nulls` (`c1`, `c5`), INDEX `ix_nynulss` (`c6`, `c5`), INDEX `ix_ynnull` (`c5`, `c6`), UNIQUE KEY `ix_c` (`c1`, `c2`), UNIQUE KEY `ix_c2` (`c5`, `c6`)) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE no_primary_keys.`nonix_``2_nix_``2` (`c``1` int, `c``2` int not null, c3 int not null, c4 int not null, c5 int, c6 int not null, UNIQUE `uk_no``nulls` (`c``2`, `c6`), INDEX `ix_no``nulls` (`c3`, `c4`), INDEX `ix_no``nulls_``2` (`c6`, `c``2`), INDEX `ix_nulls` (`c``1`, `c5`), INDEX `ix_nynulss` (`c6`, `c5`), INDEX `ix_ynnull` (`c5`, `c6`), UNIQUE KEY `ix``_c` (`c``1`, `c``2`), UNIQUE KEY `ix_c2` (`c5`, `c6`) ) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE no_primary_keys.nonix_2_nix_2 (c1 int, c2 int not null, c3 int not null, c4 int not null, c5 int, c6 int not null, UNIQUE `uk_nonulls` (`c3`, `c4`), UNIQUE `uk2_nonulls` (`c2`, `c6`), INDEX `ix_nonulls` (`c3`, `c4`), INDEX `ix_nonulls_2` (`c6`, `c2`), INDEX `ix_nulls` (`c1`, `c5`), INDEX `ix_nynulss` (`c6`, `c5`), INDEX `ix_ynnull` (`c5`, `c6`), UNIQUE KEY `ix_c` (`c1`, `c2`), UNIQUE KEY `ix_c2` (`c5`, `c6`) ) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE no_primary_keys.nonix_2_nix_2_pk (c1 int, c2 int not null, c3 int not null, c4 int not null, c5 int, c6 int not null, UNIQUE `uk_nonulls` (`c3`, `c2`), UNIQUE `uk2_nonulls` (`c4`, `c6`), INDEX `ix_nonulls` (`c4`, `c3`), INDEX `ix_nulls` (`c1`, `c5`), INDEX `ix_nynulss` (`c6`, `c5`), INDEX `ix_ynnull` (`c5`, `c6`), PRIMARY KEY `p_key` (`c2`, `c6`), UNIQUE KEY `ix_c` (`c1`, `c2`), UNIQUE KEY `ix_c2` (`c5`, `c6`) ) ENGINE=InnoDB DEFAULT CHARSET=latin1;
