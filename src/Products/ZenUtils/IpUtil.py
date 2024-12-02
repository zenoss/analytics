##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """IpUtil

IPv4 and IPv6 utility functions

Internally, IPv6 addresses will use another character rather than ':' as an underscore
is representable in URLs.  Zope object names *MUST* be okay in URLs.

"""

import re
import socket

from ipaddr import IPAddress, IPNetwork

from Products.ZenUtils.Exceptions import ZentinelException
from twisted.names.client import lookupPointer
from twisted.internet import threads

IP_DELIM = '..'
INTERFACE_DELIM = '...'

IPV4_ADDR_TYPE = "IPv4"
IPV4_ADDR_LEN = 4
IPV4_ANY_ADDRESS = "0.0.0.0"

IPV6_ADDR_TYPE = "IPv6"
IPV6_ADDR_LEN = 16
IPV6_ANY_ADDRESS = "::"

def _getPreferedIpVersion():
    """
    Determine the preferred ip version for DNS resolution.
    """
    PREFERRED_IP_KEY = 'preferredipversion'
    from Products.ZenUtils import GlobalConfig 
    globalConf = GlobalConfig.getGlobalConfiguration()
    if PREFERRED_IP_KEY in globalConf:
        version = globalConf[PREFERRED_IP_KEY]
        if version.lower() == IPV4_ADDR_TYPE.lower():
            return socket.AF_INET
        elif version.lower() == IPV6_ADDR_TYPE.lower():
            return socket.AF_INET6
        else:
            import sys
            print >> sys.stderr, 'unknown preferredipversion %s in global.conf' % version
            
    return None  # use the system default, overrideable in /etc/gai.conf

_PREFERRED_IP_VERSION = _getPreferedIpVersion()

def ipwrap(ip):
    """
    Convert IP addresses to a Zope-friendly format.
    """
    if isinstance(ip, str):
        wrapped = ip.replace(':', IP_DELIM)
        return wrapped.replace('%', INTERFACE_DELIM)
    return ip

def ipunwrap(ip):
    """
    Convert IP addresses from a Zope-friendly format to a real address.
    """
    if isinstance(ip, str):
        unwrapped = ip.replace(IP_DELIM, ':')
        return unwrapped.replace(INTERFACE_DELIM, '%')
    return ip

def ipstrip(ip):
    "strip interface off link local IPv6 addresses"
    if '%' in ip:
        address = ip[:ip.index('%')]
    else:
        address = ip
    return address

def ipunwrap_strip(ip):
    """
    ipunwrap + strip interface off link local IPv6 addresses
    """
    unwrapped = ipunwrap(ip)
    return ipstrip(unwrapped)

def _bytesToCanonIpv6(byteString):
    """
    SNMP provides a 16-byte index to table items, where the index
    represents the IPv6 address.
    """
    # To form an IPv6 address, need to combine pairs of octets (in hex)
    # and join them with a colon
    left =  map(int, byteString[::2])
    right = map(int, byteString[1::2])
    return ':'.join("%x%02x" % tuple(x) for x in zip(left, right))

def bytesToCanonIp(byteString):
    """
    SNMP provides either a 4-byte or 16-byte index to table items, where the 
    index represents an IPV4 or IPV6 address, respectively. Raises a ValueError
    for incompatible types.    

    >>> bytesToCanonIp( ['254','128','0','0','0','0','0','0','2','80','86','255','254','138','46','210'])
    'fe80::250:56ff:fe8a:2ed2'
    >>> bytesToCanonIp( ['253','0','0','0','0','0','0','0','0','0','0','0','10','175','210','5'])
    'fd00::aaf:d205'
    >>> bytesToCanonIp( ['hello','world'])
    Traceback (most recent call last):
        ...
    ValueError: Unsupported IP Address: hello.world
    >>> bytesToCanonIp( ['253','0','0','0','0','0','0','0','0','0','0','0','10','175','210','5'])
    'fd00::aaf:d205'
    """

    byteStringLen =  len(byteString)
    if byteStringLen == IPV4_ADDR_LEN:
       rawIpStr = '.'.join(byteString)
    elif byteStringLen == IPV6_ADDR_LEN:
       rawIpStr = _bytesToCanonIpv6(byteString)
    else:
       raise ValueError("Unsupported IP Address: %s" % '.'.join(byteString))

    return str(IPAddress(rawIpStr))


class IpAddressError(ZentinelException): pass

class InvalidIPRangeError(Exception):
    """
    Attempted to parse an invalid IP range.
    """


def isip(ip):
    uIp = str(ipunwrap(ip))
    # Twisted monkey patches socket.inet_pton on systems that have IPv6
    # disabled and raise a ValueError instead of the expected socket.error
    # if the passed in address is invalid.
    try:
        socket.inet_pton(socket.AF_INET, uIp)
    except (socket.error, ValueError):
        try:
            socket.inet_pton(socket.AF_INET6, uIp)
        except (socket.error, ValueError):
            return False
    return True


def checkip(ip):
    """
    Check that an IPv4 address is valid. Return true
    or raise an exception(!)

    >>> checkip('10.10.20.5')
    True
    >>> try: checkip(10)
    ... except IpAddressError as ex: print ex
    10 is an invalid address
    >>> try: checkip('10')
    ... except IpAddressError as ex: print ex
    10 is an invalid address
    >>> try: checkip('10.10.20.500')
    ... except IpAddressError as ex: print ex
    10.10.20.500 is an invalid address
    >>> checkip('10.10.20.0')
    True
    >>> checkip('10.10.20.255')
    True
    """
    if not isip(ip):
        raise IpAddressError( "%s is an invalid address" % ip )
    return True


def numbip(ip):
    """
    Convert a string IP to a decimal representation easier for
    calculating netmasks etc.

    Deprecated in favour of ipToDecimal()
    """
    return ipToDecimal(ip)

def ipToDecimal(ip):
    """
    Convert a string IP to a decimal representation easier for
    calculating netmasks etc.

    >>> ipToDecimal('10.10.20.5')
    168432645
    >>> try: ipToDecimal('10.10.20.500')
    ... except IpAddressError as ex: print ex
    10.10.20.500 is an invalid address
    """
    checkip(ip)
    unwrapped = ipunwrap(ip)
    if '%' in unwrapped:
        address = unwrapped[:unwrapped.index('%')]
    else:
        address = unwrapped
    return int(IPAddress(address))

def ipFromIpMask(ipmask):
    """
    Get just the IP address from an CIDR string like 1.1.1.1/24

    >>> ipFromIpMask('1.1.1.1')
    '1.1.1.1'
    >>> ipFromIpMask('1.1.1.1/24')
    '1.1.1.1'
    """
    return ipmask.split("/")[0]

def ipAndMaskFromIpMask(ipmask):
    """
    Get just the IP address and Mask from string like 1.1.1.1/24
    """
    if ipmask.find("/") > -1:
        ip, netmask = ipmask.split("/",1)
        return ip, netmask
    return ipmask, ""

def strip(ip):
    """
    Convert a numeric IP address to a string

    Deprecated in favour of decimalIpToStr()
    """
    return decimalIpToStr(ip)

def decimalIpToStr(ip):
    """
    Convert a decimal IP address (as returned by ipToDecimal)
    to a regular IPv4 dotted quad address.

    >>> decimalIpToStr(ipToDecimal('10.23.44.57'))
    '10.23.44.57'
    """
    return str(IPAddress(ipunwrap(ip)))

def hexToBits(hex):
    """
    Convert hex netbits (0xff000000) to decimal netmask (8)

    >>> hexToBits("0xff000000")
    8
    >>> hexToBits("0xffffff00")
    24
    """
    return maskToBits(hexToMask(hex))
    

def hexToMask(hex):
    """
    Converts a netmask represented in hex to octets represented in
    decimal.

    >>> hexToMask("0xffffff00")
    '255.255.255.0'
    >>> hexToMask("0xffffffff")
    '255.255.255.255'
    >>> hexToMask("0x00000000")
    '0.0.0.0'
    >>> hexToMask("0x12300000")
    '18.48.0.0'
    >>> hexToMask("0x00000123")
    '0.0.1.35'
    >>> hexToMask("0xbadvalue")
    '255.255.255.255'
    >>> hexToMask("0x123")
    '255.255.255.255'
    >>> hexToMask("trash")
    '255.255.255.255'
    """
    try:
        hex = hex.lower()
        if len(hex) != 10 or not hex.startswith('0x'):
            raise Exception('malformed netmask')
        int(hex, 16)  # valid hexadecimal?
    except Exception:
        return "255.255.255.255"

    octets = []
    for idx in [2,4,6,8]:
        decimal = int(hex[idx:idx+2], 16)
        octets.append(str(decimal))
    return '.'.join(octets)


def maskToBits(netmask):
    """
    Convert string rep of netmask to number of bits

    >>> maskToBits('255.255.255.255')
    32
    >>> maskToBits('255.255.224.0')
    19
    >>> maskToBits('0.0.0.0')
    0
    """
    if isinstance(netmask, basestring) and '.' in netmask:
        test = 0xffffffff
        if netmask[0]=='0': return 0
        masknumb = ipToDecimal(netmask)
        for i in range(32):
            if test == masknumb: return 32-i
            test = test - 2 ** i
        return None
    else:
        return int(netmask)
       

def bitsToMaskNumb(netbits):
    """
    Convert integer number of netbits to a decimal number

    Deprecated in favour of bitsToDecimalMask()
    """
    return bitsToDecimalMask(netbits)

def bitsToDecimalMask(netbits):
    """
    Convert integer number of netbits to a decimal number

    >>> bitsToDecimalMask(32)
    4294967295
    >>> bitsToDecimalMask(19)
    4294959104
    >>> bitsToDecimalMask(0)
    0
    """
    masknumb = 0
    netbits=int(netbits)
    for i in range(32-netbits, 32):
        masknumb += 2 ** i
    return masknumb
   

def bitsToMask(netbits):
    """
    Convert netbits into a dotted-quad subnetmask

    >>> bitsToMask(12)
    '255.240.0.0'
    >>> bitsToMask(0)
    '0.0.0.0'
    >>> bitsToMask(32)
    '255.255.255.255'
    """
    return decimalIpToStr(bitsToDecimalMask(netbits))


def getnet(ip, netmask):
    """
    Deprecated in favour of decimalNetFromIpAndNet()
    """
    return decimalNetFromIpAndNet(ip, netmask)

def decimalNetFromIpAndNet(ip, netmask):
    """
    Get network address of IP as string netmask as in the form 255.255.255.0

    >>> getnet('10.12.25.33', 24)
    168564992
    >>> getnet('10.12.25.33', '255.255.255.0')
    168564992
    """
    checkip(ip)
    return int(IPNetwork(ipunwrap(ip) + '/' + str(netmask)).network)

def getnetstr(ip, netmask):
    """
    Deprecated in favour of netFromIpAndNet()
    """
    return netFromIpAndNet(ip, netmask)

def netFromIpAndNet(ip, netmask):
    """
    Return network number as string

    >>> netFromIpAndNet('10.12.25.33', 24)
    '10.12.25.0'
    >>> netFromIpAndNet('250.12.25.33', 1)
    '128.0.0.0'
    >>> netFromIpAndNet('10.12.25.33', 16)
    '10.12.0.0'
    >>> netFromIpAndNet('10.12.25.33', 32)
    '10.12.25.33'
    """
    checkip(ip)
    return str(IPNetwork( ipunwrap(ip) + '/' + str(netmask)).network)

def asyncNameLookup(address, uselibcresolver = True):
    """
    Turn IP addreses into names using deferreds
    """
    if uselibcresolver:
        # This is the most reliable way to do a lookup use it 
        return threads.deferToThread(lambda : socket.gethostbyaddr(address)[0])
    else:
        # There is a problem with this method because it will ignore /etc/hosts
        address = '.'.join(address.split('.')[::-1]) + '.in-addr.arpa'
        d = lookupPointer(address, [1,2,4])
        def ip(result):
            return str(result[0][0].payload.name)
        d.addCallback(ip)
        return d

def asyncIpLookup(name):
    """
    Look up an IP based on the name passed in.  We use gethostbyname to make
    sure that we use /etc/hosts as mentioned above.

    This hasn't been tested.
    """
    return threads.deferToThread(lambda : socket.gethostbyname(name))

def generateAddrInfos(hostname):
    """
    generator for dicts from addrInfo structs for hostname
    """
    for addrInfo in socket.getaddrinfo(hostname, None):
        yield {"ipAddress": addrInfo[-1][0],
                "ipFamily": addrInfo[0]}

def getHostByName(hostname, preferredIpVersion=_PREFERRED_IP_VERSION):
    """
    Look up an IP based on the name passed in, synchronously. Not using
    socket.gethostbyname() because it does not support IPv6.

    preferredIpVersion should equal something like socket.AF_INET or
    socket.AF_INET6
    """
    addrInfos = generateAddrInfos(hostname)
    if preferredIpVersion is not None:
        for addrInfo in addrInfos:
            if addrInfo['ipFamily'] == preferredIpVersion:
                return addrInfo['ipAddress']
    firstInfo = addrInfos.next()
    return firstInfo['ipAddress']

def parse_iprange(iprange):
    """
    Turn a string specifying an IP range into a list of IPs.

    @param iprange: The range string, in the format '10.0.0.a-b'
    @type iprange: str

        >>> parse_iprange('10.0.0.1-5')
        ['10.0.0.1', '10.0.0.2', '10.0.0.3', '10.0.0.4', '10.0.0.5']
        >>> parse_iprange('10.0.0.2-5')
        ['10.0.0.2', '10.0.0.3', '10.0.0.4', '10.0.0.5']
        >>> parse_iprange('10.0.0.1')
        ['10.0.0.1']
        >>> try: parse_iprange('10.0.0.1-2-3')
        ... except InvalidIPRangeError: print "Invalid"
        Invalid
        >>> parse_iprange('fd00::aaf:d201-d203')
        ['fd00::aaf:d201', 'fd00::aaf:d202', 'fd00::aaf:d203']
    """
    rangeList = iprange.split('-')
    if len(rangeList) > 2: # Nothing we can do about this
        raise InvalidIPRangeError('%s is an invalid IP range.' % iprange)
    elif len(rangeList) == 1: # A single IP was passed
        return [iprange]

    beginIp, endIp = rangeList
    # Is it just an int?
    separator = '.'
    strFn = lambda x:x
    base = 10
    if beginIp.find(':')> -1:
        separator=':'
        base=16
        strFn = lambda x: '{0:x}'.format(x)
    net, start = beginIp.rsplit(separator, 1)
    start = int(start, base)
    end = int(endIp, base)

    return ['%s%s%s' % (net, separator, strFn(x)) for x in xrange(start, end+1)]


def getSubnetBounds(ip):
    """
    Given a string representing the lower limit of a subnet, return decimal
    representations of the first and last IP of that subnet.

    0 is considered to define the beginning of a subnet, so x.x.x.0 represents
    a /24, x.x.0.0 represents a /16, etc. An octet of 0 followed by a non-zero
    octet, of course, is not considered to define a lower limit.

        >>> map(decimalIpToStr, getSubnetBounds('10.1.1.0'))
        ['10.1.1.0', '10.1.1.255']
        >>> map(decimalIpToStr, getSubnetBounds('10.1.1.1'))
        ['10.1.1.1', '10.1.1.1']
        >>> map(decimalIpToStr, getSubnetBounds('10.0.1.0'))
        ['10.0.1.0', '10.0.1.255']
        >>> map(decimalIpToStr, getSubnetBounds('0.0.0.0'))
        ['0.0.0.0', '255.255.255.255']
        >>> map(decimalIpToStr, getSubnetBounds('10.0.0.0'))
        ['10.0.0.0', '10.255.255.255']
        >>> map(decimalIpToStr, getSubnetBounds('100.0.0.0'))
        ['100.0.0.0', '100.255.255.255']
        >>> map(decimalIpToStr, getSubnetBounds('::100.0.0.0'))
        ['100.0.0.0', '100.255.255.255']

    """
    octets = ip.split('.')
    otherend = []
    while octets:
        o = octets.pop()
        if o=='0':
            otherend.append('255')
        else:
            otherend.append(o)
            break
    otherend.reverse()
    octets.extend(otherend)
    upper = '.'.join(octets)
    return numbip(ip), numbip(upper)

def ensureIp(ip):
    """
    Given a partially formed IP address this will return a complete Ip address
    with four octets with the invalid or missing entries replaced by 0
    
    @param ip partially formed ip (will strip out alpha characters)
    @return valid IP address field
    
    >>> from Products.ZenUtils.IpUtil import ensureIp
    >>> ensureIp('20')
    '20.0.0.0'
    >>> ensureIp('2000')
    '0.0.0.0'
    >>> ensureIp('10.175.X')
    '10.175.0.0'
    >>> ensureIp('10.0.1')
    '10.0.1.0'
    >>> 
    """
    # filter out the alpha characters
    stripped = ''.join(c for c in ip if c in '1234567890.')
    octets = stripped.split('.')

    # make sure we always have 4 
    while (len(octets) < 4):
        octets.append('0')

    # validate each octet
    for (idx, octet) in enumerate(octets):
        # cast it to an integer
        try:
            octet = int(octet)
        except ValueError:
            octet = 0

        # make it 0 if not in the valid ip range
        if not (0 < octet < 256):
            octets[idx] = '0'

    return '.'.join(octets)

def get_ip_version(ip):
    """
    Given an IP Address string, return the ip version (4, 6
    or None if the ip is not valid)
    """
    try:
        ip_address = IPAddress(ip)
        return ip_address.version
    except ValueError:
        return None

def isRemotelyReachable(ip):
    """
    Given an IP Address string, returns a boolean if the given ip can be 
    reached remotely.
    """
    try:
        ip_address = IPAddress(ip)
        return not ip_address.is_link_local and not ip_address.is_loopback
    except ValueError:
        return False

def get_default_netmask(ip):
    netmask = 24
    if get_ip_version(ip) == 6:
        netmask = 48
    return netmask
