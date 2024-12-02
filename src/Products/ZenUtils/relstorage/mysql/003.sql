DROP PROCEDURE IF EXISTS create_connection_info;
DELIMITER $$
CREATE  PROCEDURE create_connection_info()
BEGIN
    IF NOT EXISTS(SELECT 1 FROM schema_version WHERE version = 3)
    AND NOT EXISTS(SELECT 1
                   FROM information_schema.columns
                   WHERE table_schema = DATABASE()
                   AND UPPER(table_name) = 'CONNECTION_INFO')
    THEN
        CREATE TABLE connection_info(
          connection_id INT NOT NULL,
          pid INT NOT NULL,
          info TEXT NOT NULL,
          ts TIMESTAMP NOT NULL,
          PRIMARY KEY(connection_id),
          KEY(pid)
        ) ENGINE = InnoDB;

        INSERT INTO `schema_version` (`version`, `installed_time`)
        VALUES(3, NOW());
    END IF;
END
$$
DELIMITER ;

call create_connection_info();

DROP PROCEDURE create_connection_info;

