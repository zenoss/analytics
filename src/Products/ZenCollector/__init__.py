##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
ZenCollector is a unified collection framework for Zenoss. The framework
provides the following features:

1. Collection can be split up into tasks based upon collector-defined
   boundaries. The default boundary is one task for each device.

2. Tasks are independently scheduled and will not have to wait for other tasks
   to complete before continuing their own collection cycle. This improves
   collector scalability by preventing slow devices from blocking other tasks.

3. Device ping issues are retrieved periodically and tasks for those devices
   are paused and resumed as needed.

4. Heartbeat events will be periodically sent to ZenHub to indicate the
   collector daemon is running.

5. Collector daemon statistics will be periodically saved into RRD.

6. The collector configuration service is extensible and can be enhanced or
   replaced as needed.


To implement a new collector using the ZenCollector framework, use the
following steps:

1. Determine what data your collector is actually gathering, and from what kind
   of devices.

2. Implement a new HubService that extends
   Products.ZenCollector.services.config.CollectorConfigService to filter out
   which devices are sent to the collector and what attributes are sent back
   via a DeviceProxy object.

3. Implement an object that provides the ICollectorPreferences interface and
   specifies the overall configuration preferences of the new collector.

4. Decide if the SimpleTaskSplitter will suffice. This task splitter will
   create a single task for each device returned by your configuration service.
   If not, then create your own task splitter to meet your collector's needs.

5. Implement an object that provides the IScheduledTask interface. The task
   will do the actual work of collecting from a device, or other system, and
   processing the data.

   Tasks should always be implemented using the Twisted asynchronous
   communications framework so that the entire collector daemon can continue to
   serve requests for other tasks while I/O is pending.

6. Implement the main method of your collector, which should use the following
   pattern:

    from Products.ZenCollector.daemon import CollectorDaemon
    from Products.ZenCollector.tasks import SimpleTaskFactory, \
                                            SimpleTaskSplitter

    if __name__ == '__main__':
        myPreferences = MyCollectorPreferences()
        myTaskFactory = SimpleTaskFactory(MyTask)
        myTaskSplitter = SimpleTaskSplitter(myTaskFactory)
        daemon = CollectorDaemon(myPreferences, myTaskSplitter)
        daemon.run()
"""
