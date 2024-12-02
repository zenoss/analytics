import Migrate
import logging
log = logging.getLogger("zen.migrate")
from xml.etree import ElementTree as etree  

import servicemigration as sm 
sm.require("1.0.0")

class UpdateZepLogbackConfig(Migrate.Step):
    """ 
    Removing zeneventserver metrics logging inside container.
    """
    version = Migrate.Version(108, 0, 0)

    UPDATED_LOGBACK_CONFIG = """<?xml version="1.0" encoding="UTF-8"?>
<!--
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
-->


<configuration scan="true">
    <statusListener class="ch.qos.logback.core.status.OnConsoleStatusListener" />

    <if condition='isNull("ZENOSS_DAEMON")'>
        <then>
            <appender name="APPENDER" class="ch.qos.logback.core.ConsoleAppender">
                <encoder>
                    <pattern>%date{yyyy-MM-dd'T'HH:mm:ss.SSS} [%thread] %-5level %logger - %msg%n</pattern>
                </encoder>
            </appender>
        </then>
        <else>
            <appender name="APPENDER" class="ch.qos.logback.core.rolling.RollingFileAppender">
                <file>${ZENHOME:-.}/log/zeneventserver.log</file>
                <rollingPolicy class="ch.qos.logback.core.rolling.FixedWindowRollingPolicy">
                    <!-- daily rollover -->
                    <fileNamePattern>${ZENHOME:-.}/log/zeneventserver.log.%i</fileNamePattern>
                    <!-- keep up to 3 logs by default -->
                    <minIndex>1</minIndex>
                    <maxIndex>3</maxIndex>
                </rollingPolicy>
                <triggeringPolicy class="ch.qos.logback.core.rolling.SizeBasedTriggeringPolicy">
                    <maxFileSize>10MB</maxFileSize>
                </triggeringPolicy>
                <encoder>
                    <pattern>%date{yyyy-MM-dd'T'HH:mm:ss.SSS} [%thread] %-5level %logger - %msg%n</pattern>
                </encoder>
            </appender>
        </else>
    </if>

    <contextName>zeneventserver</contextName>
    <jmxConfigurator />
    <logger name="org.springframework" level="WARN"/>
    <logger name="ch.qos.logback" level="WARN"/>
    <logger name="com.zenoss" level="${ZENOSS_LOG_LEVEL:-INFO}" />
    <logger name="org.zenoss" level="${ZENOSS_LOG_LEVEL:-INFO}" />
    <root level="INFO">
        <appender-ref ref="APPENDER"/>
    </root>
</configuration>
"""
        
    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return
    
        isUpdated = False
        service = filter(lambda s: s.name == "zeneventserver", ctx.services)[0]
        configFiles = service.originalConfigs + service.configFiles 
        # Update logback.xml
        cfgs = filter(lambda f: f.name == "/opt/zenoss/etc/zeneventserver/logback.xml", configFiles)
        for cfg in cfgs:
            if "METRICS-APPENDER" in cfg.content:
                cfg.content = self.UPDATED_LOGBACK_CONFIG
                isUpdated = True

        if isUpdated:
            ctx.commit()

UpdateZepLogbackConfig()
