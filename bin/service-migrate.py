#!/usr/bin/env python

import sys
import servicemigration as sm
sm.require("1.0.0")

TMP_FILENAME = "/tmp/zenoss-service-migration.json"

if sys.argv[-1] == "begin":
    ctx = sm.ServiceContext()
    ctx.commit(TMP_FILENAME)
    print TMP_FILENAME,
elif sys.argv[-1] == "end":
    ctx = sm.ServiceContext(TMP_FILENAME)
    ctx.commit()
else:
    raise ValueError("No operation specified.")
