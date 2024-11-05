##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os
import socket

from Products.ZenUtils.path import zenPath

def main():
    "Run a tcpdump PCAP file to zentrap"
    dumpfile = zenPath('Products/ZenEvents/tests/trapdump.pcap')
    packets = []
    packet = []
    # extract packet data without getting a pcap module:
    for line in os.popen('tcpdump -x -r %s' % dumpfile):
        if line[0] == '\t':
            hex = line.split(':', 1)[1].replace(' ','').strip()
            bytes = [hex[i:i+2] for i in range(0, len(hex), 2)]
            data = ''.join([chr(int(byte, 16)) for byte in bytes])
            packet.append(data)
        else:
            if packet:
                packets.append(''.join(packet))
    if packet:
        packets.append(''.join(packet))
    assert len(packets) == 2
    for p in packets:
        assert p[0] == chr(0x45)        # check for IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for p in packets:
        p = p[28:]                      # get to UDP data
        s.sendto(p, ('127.0.0.1', 1162))

main()
