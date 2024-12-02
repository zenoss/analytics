
/* detect if schema exists.
   if exists, check if it's 1.5 compatible.
   if not compatible, alter table to be 1.5 compatible
*/
DROP PROCEDURE IF EXISTS upgrade_relstor_1_5;
DELIMITER $$
CREATE  PROCEDURE upgrade_relstor_1_5()
BEGIN

    if exists(select 1 from information_schema.columns where table_schema = DATABASE()
                  and upper(table_name) = 'OBJECT_STATE')
    THEN

        IF NOT EXISTS(select 1 from information_schema.columns where table_schema = DATABASE()
                      and upper(table_name) = 'OBJECT_STATE' and column_name = 'state_size')
        THEN
        
            IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND COLUMN_NAME = 'md5')
            THEN
               ALTER TABLE object_state ADD COLUMN state_size BIGINT AFTER md5;
               UPDATE object_state SET state_size = COALESCE(LENGTH(state), 0);
               ALTER TABLE object_state MODIFY state_size BIGINT NOT NULL AFTER md5;
            ELSE
               ALTER TABLE object_state ADD COLUMN state_size BIGINT AFTER tid;
               UPDATE object_state SET state_size = COALESCE(LENGTH(state), 0);
               ALTER TABLE object_state MODIFY state_size BIGINT NOT NULL AFTER tid;
            END IF;
        END IF;
    END IF;
END
$$
DELIMITER ;

call upgrade_relstor_1_5();

DROP PROCEDURE upgrade_relstor_1_5;

CREATE TABLE `schema_version`
(
    `version` INTEGER NOT NULL,
    `installed_time` DATETIME NOT NULL,
    PRIMARY KEY(version)
) ENGINE=InnoDB CHARACTER SET=utf8 COLLATE=utf8_general_ci;

INSERT INTO `schema_version` (`version`, `installed_time`) VALUES(1, NOW());

