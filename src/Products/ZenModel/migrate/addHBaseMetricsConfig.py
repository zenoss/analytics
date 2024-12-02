##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class AddHBaseMetricsConfig(Migrate.Step):
    """ Set metrics reporting frequency to 15 secs. See ZEN-25317 """
    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        def updateService(serviceName):
            changed = False
            services = filter(lambda s: s.name == serviceName, ctx.services)
            hm_content = "# Licensed to the Apache Software Foundation (ASF) under one\n# or more contributor license agreements.  See the NOTICE file\n# distributed with this work for additional information\n# regarding copyright ownership.  The ASF licenses this file\n# to you under the Apache License, Version 2.0 (the\n# \"License\"); you may not use this file except in compliance\n# with the License.  You may obtain a copy of the License at\n#\n#     http://www.apache.org/licenses/LICENSE-2.0\n#\n# Unless required by applicable law or agreed to in writing, software\n# distributed under the License is distributed on an \"AS IS\" BASIS,\n# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n# See the License for the specific language governing permissions and\n# limitations under the License.\n\n# syntax: [prefix].[source|sink].[instance].[options]\n# See javadoc of package-info.java for org.apache.hadoop.metrics2 for details\n\n# sampling period\n*.period=15\n\n# Below are some examples of sinks that could be used\n# to monitor different hbase daemons.\n\nhbase.sink.file-all.class=com.zenoss.hadoop.metrics.ControlCenterSink\nhbase.sink.file-all.includedMetrics=Log\\\\w*,\\\\w*RegionServers\n# hbase.sink.file0.class=org.apache.hadoop.metrics2.sink.FileSink\n# hbase.sink.file0.context=hmaster\n# hbase.sink.file0.filename=master.metrics\n\n# hbase.sink.file1.class=org.apache.hadoop.metrics2.sink.FileSink\n# hbase.sink.file1.context=thrift-one\n# hbase.sink.file1.filename=thrift-one.metrics\n\n# hbase.sink.file2.class=org.apache.hadoop.metrics2.sink.FileSink\n# hbase.sink.file2.context=thrift-two\n# hbase.sink.file2.filename=thrift-one.metrics\n\n# hbase.sink.file3.class=org.apache.hadoop.metrics2.sink.FileSink\n# hbase.sink.file3.context=rest\n# hbase.sink.file3.filename=rest.metrics\n"
            rs_content = "# Licensed to the Apache Software Foundation (ASF) under one\n# or more contributor license agreements.  See the NOTICE file\n# distributed with this work for additional information\n# regarding copyright ownership.  The ASF licenses this file\n# to you under the Apache License, Version 2.0 (the\n# \"License\"); you may not use this file except in compliance\n# with the License.  You may obtain a copy of the License at\n#\n#     http://www.apache.org/licenses/LICENSE-2.0\n#\n# Unless required by applicable law or agreed to in writing, software\n# distributed under the License is distributed on an \"AS IS\" BASIS,\n# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n# See the License for the specific language governing permissions and\n# limitations under the License.\n\n# syntax: [prefix].[source|sink].[instance].[options]\n# See javadoc of package-info.java for org.apache.hadoop.metrics2 for details\n\n# sampling period\n*.period=15\n\n# Below are some examples of sinks that could be used\n# to monitor different hbase daemons.\n\nhbase.sink.file-all.class=com.zenoss.hadoop.metrics.ControlCenterSink\nhbase.sink.file-all.includedMetrics=numCallsInGeneralQueue,numCallsIn\\\\w*Queue,\\\\w*QueueLength,\\\\w*Count,\\\\w+RequestCount\n# hbase.sink.file0.class=org.apache.hadoop.metrics2.sink.FileSink\n# hbase.sink.file0.context=hmaster\n# hbase.sink.file0.filename=master.metrics\n\n# hbase.sink.file1.class=org.apache.hadoop.metrics2.sink.FileSink\n# hbase.sink.file1.context=thrift-one\n# hbase.sink.file1.filename=thrift-one.metrics\n\n# hbase.sink.file2.class=org.apache.hadoop.metrics2.sink.FileSink\n# hbase.sink.file2.context=thrift-two\n# hbase.sink.file2.filename=thrift-one.metrics\n\n# hbase.sink.file3.class=org.apache.hadoop.metrics2.sink.FileSink\n# hbase.sink.file3.context=rest\n# hbase.sink.file3.filename=rest.metrics\n"
            content = hm_content if serviceName == 'HMaster' else rs_content

            def equal(this, that):
                return this.name == that.name and this.filename == that.filename and this.owner == that.owner and this.permissions == that.permissions and this.content == that.content

            for service in services:
                newConfig = sm.ConfigFile(
                    name="/opt/hbase/conf/hadoop-metrics2-hbase.properties",
                    filename="/opt/hbase/conf/hadoop-metrics2-hbase.properties",
                    owner="hbase:hbase",
                    permissions="0664",
                    content=content
                )

                # If there's a config with the same name but is different from
                # the new config, overwrite it.
                if all([not equal(config, newConfig) for config in service.originalConfigs]):
                    service.originalConfigs.append(newConfig)
                    changed = True
                    log.info("Adding a configuration to OriginalConfigs of %s", service.name)

                # Add this config only if there's no config with the same name.
                # If there is such config, honor it.
                if all([not config.name == newConfig.name for config in service.configFiles]):
                    service.configFiles.append(newConfig)
                    changed = True
                    log.info("Adding a configuration to ConfigFiles of %s", service.name)

            return changed

        changed = False
        changed |= updateService('HMaster')
        changed |= updateService('RegionServer')

        if changed:
            log.info("Configuration added for HBase services")
            ctx.commit()


AddHBaseMetricsConfig()
