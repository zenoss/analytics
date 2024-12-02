##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


App_Start = "/App/Start"
App_Stop = "/App/Stop"
Change_Add = "/Change/Add"
Change = "/Change"
Change_Remove = "/Change/Remove"
Change_Set = "/Change/Set"
Change_Rebuild = "/Change/Rebuild"
Change_Add_Blocked = "/Change/Add/Blocked"
Change_Remove_Blocked = "/Change/Remove/Blocked"
Change_Set_Blocked = "/Change/Set/Blocked"
Cmd_Fail = "/Cmd/Fail"
Cmd_Ok = "/Cmd/Ok"
Heartbeat = "/Heartbeat"
Perf_Snmp = "/Perf/Snmp"
Perf_XmlRpc = "/Perf/XmlRpc"
Status_Heartbeat = "/Status/Heartbeat"
Status_IpService = "/Status/IpService"
Status_Nagios = "/Status/Nagios" # Deprecated, but included for consistency
Status_OSProcess = "/Status/OSProcess"
Status_Perf = "/Status/Perf"
Status_Ping = "/Status/Ping"
Status_Ping_Lag = "/Status/Ping/Lag"
Status_RRD = "/Status/RRD"
Status_Snmp = "/Status/Snmp"
Status_Update = "/Status/Update"
Status_Web = "/Status/Web"
Status_Wmi = "/Status/Wmi"
Status_Wmi_Conn = "/Status/Wmi/Conn"
Status_WinService = "/Status/WinService"
Status_XmlRpc = "/Status/XmlRpc"
Status_ZEP = "/Status/ZEP"
Capacity = "/Capacity"
Unknown = "/Unknown"

Severities = 'Clear Debug Info Warning Error Critical'.split()
Clear, Debug, Info, Warning, Error, Critical = range(6)
