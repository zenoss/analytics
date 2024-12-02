#!/bin/bash

if [[ $1 = "mariadb-model" ]]; then
  DB="zodb"
else
  DB="zep"
fi

# Use "/usr/bin/python" rather than "/opt/zenoss/bin/python" because the
# latter is not available in mariadb image.
# The file "/opt/zenoss/Products/ZenUtils/ZenDB.py" will have to be copied
# into the mariadb image via product-assembly repo's "mariadb/Dockerfile.in"
/usr/bin/python /opt/zenoss/bin/zendb --usedb $DB --execsql=<<SQL
USE information_schema;

SELECT
    table_schema "Database",
    sum(data_length + index_length) "Bytes",
    sum(data_free) "Free"
FROM
    TABLES
GROUP BY
    1
;
SQL
