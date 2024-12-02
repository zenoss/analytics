
DROP TABLE IF EXISTS schema_version;
CREATE TABLE schema_version
(
    version INTEGER NOT NULL,
    installed_time TIMESTAMP NOT NULL,
    PRIMARY KEY(version)
);



-- detect if table is not 1.5 compatible, alter if necessary
CREATE OR REPLACE FUNCTION update_relstorage_15()
RETURNS void 
AS
$$
BEGIN
    IF EXISTS(
	SELECT a.attname as "column", pg_catalog.format_type(a.atttypid,
	a.atttypmod) as "datatype"
	FROM pg_catalog.pg_attribute a
	WHERE a.attnum > 0
	AND NOT a.attisdropped
	AND a.attrelid = (
	SELECT c.oid
	FROM pg_catalog.pg_class c
	LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
	WHERE c.relname ~ '^(object_state)$'
	AND pg_catalog.pg_table_is_visible(c.oid)
	) 
   )
   THEN
	   ALTER TABLE object_state ADD COLUMN state_size BIGINT;
	   UPDATE object_state SET state_size = COALESCE(LENGTH(state), 0);
	   ALTER TABLE object_state ALTER COLUMN state_size SET NOT NULL;
	   COMMIT;
   END IF;   
END;
$$
LANGUAGE 'plpgsql';

SELECT update_relstorage_15();
DROP FUNCTION update_relstorage_15();

INSERT INTO schema_version (version, installed_time) VALUES(1, NOW());

