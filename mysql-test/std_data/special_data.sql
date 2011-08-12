#
# Create a database with special symbols for compatibility testing.
#
CREATE DATABASE util_spec;
CREATE FUNCTION util_spec.spec_date(mydatetime datetime) RETURNS datetime DETERMINISTIC RETURN DATE_FORMAT(mydatetime, '%d/%m %H:%i')
