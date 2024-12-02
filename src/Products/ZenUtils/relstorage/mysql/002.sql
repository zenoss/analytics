
/* detect if schema exists.
   if exists, check if using compressed format for object_state 
*/
DROP PROCEDURE IF EXISTS check_barracuda_object_state;
DELIMITER $$
CREATE  PROCEDURE check_barracuda_object_state()
BEGIN

    IF EXISTS(SELECT 1 from information_schema.columns WHERE table_schema = DATABASE()
                  AND upper(table_name) = 'OBJECT_STATE')
    THEN

        IF NOT EXISTS(select 1 FROM information_schema.tables WHERE table_schema = DATABASE()
                      and upper(table_name) = 'OBJECT_STATE' and row_format = 'Compressed')
        THEN
            ALTER TABLE object_state ENGINE=Innodb row_format=Compressed;
        END IF;
    END IF;
END
$$
DELIMITER ;

call check_barracuda_object_state();

DROP PROCEDURE check_barracuda_object_state;
INSERT INTO `schema_version` (`version`, `installed_time`) VALUES(2, NOW());

