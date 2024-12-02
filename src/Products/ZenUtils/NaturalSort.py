import re

##
#This module is translated from java script to python with some enhancements from 
#the java script source code at repository: https://github.com/overset/javascript-natural-sort.
# The Zenoss UI uses the full javascript implementation for client-side sorting.
#
# - 4/15/2013, Seth Cleveland

#Numbers
#re = /(^-?[0-9]+(\.?[0-9]*)[df]?e?[0-9]?$|^0x[0-9a-f]+$|[0-9]+)/gi,
_NRE = re.compile( u'(^-?[0-9]+(\.?[0-9]*)[df]?e?[0-9]?$|^0x[0-9a-f]+$|[0-9]+)', re.I|re.U)

#WhiteSpace - not used...
#sre = /(^[ ]*|[ ]*$)/g,
#SRE = re.compile( u'(^[ ]*|[ ]*$)')

#DateTime - not used
#dre = /(^([\w ]+,?[\w ]+)?[\w ]+,?[\w ]+\d+:\d+(:\d+)?[\w ]?|^\d{1,4}[\/\-]\d{1,4}[\/\-]\d{1,4}|^\w+, \w+ \d+, \d{4})/,
#DRE = re.compile( u'(^([\w ]+,?[\w ]+)?[\w ]+,?[\w ]+\d+:\d+(:\d+)?[\w ]?|^\d{1,4}[\/\-]\d{1,4}[\/\-]\d{1,4}|^\w+, \w+ \d+, \d{4})', re.I|re.U)

#Hex
#hre = /^0x[0-9a-f]+$/i,
_HRE = re.compile( u'^0x[0-9a-f]+$', re.I|re.U)

#Leading zeros
#ore = /^0/,
#ORE = re.compile( u'^0.+', re.U)

#Leading delim
_L0RE = re.compile( u'^\0', re.U)

#Ending delim
_E0RE = re.compile( u'\0$', re.U)

def _get(list, index, value):
    if index < len( list):
        return list[index]
    return value

def _chunk(x):
    x = _NRE.sub( u'\0\\1\0', x)
    x = _L0RE.sub( u'', x)
    x = _E0RE.sub( u'', x)
    return x.split( u'\0')

def _hexValue(x):
    if _HRE.match( x):
        try: return int( x, 16)
        except Exception: pass
    return None 

def _floatValue(x):
    try: return float( x)
    except Exception: return None

def natural_compare( lhs, rhs):
    #convert all to strings strip whitespace
    x = unicode(lhs).lower().strip()
    y = unicode(rhs).lower().strip()

    #numeric, hex or date detection
    xD = _hexValue( x)
    yD = _hexValue( y)

    #first try and sort Hex/Int Values
    if not yD is None and not xD is None:
        _cmp = cmp(xD, yD)
        if _cmp != 0:
            return _cmp

    #chunk/tokenize
    xN = _chunk(x)
    yN = _chunk(y)

    i = 0
    num = max( len(xN), len(yN))
    # natural sorting by spliting numeric strings and strings
    while i < num:
        xV = _get( xN, i, '0')
        yV = _get( yN, i, '0')
        xF = _floatValue( xV)
        yF = _floatValue( yV)

        if xF is None and yF is None:
            #x and y are strings
            _cmp = cmp( xV, yV)
            if _cmp != 0: return _cmp
        elif xF is None and not yF is None:
            #x is string and y is number
            return 1
        elif not xF is None and yF is None:
            #x is number and y is string
            return -1
        else:
            #x is number and y is number
            if (xV.startswith( '0') and xV != '0') or (yV.startswith( '0') and yV != '0'):
                _cmp = cmp( xV, yV)
                if _cmp != 0: return _cmp
            else:
                _cmp = cmp( xF, yF)
                if _cmp != 0: return _cmp
        i += 1
    return 0

class NaturalObjectCompare:
    def __init__(self, this):
        self.this = this

    def __repr__(self):
        return repr( self.this)

    def __hash__(self):
        return hash( self.this)

    def __str__(self):
        return str( self.this)

    # Comparison operators
    def __cmp__(self, that):
        return natural_compare(self.this, that)

    def __eq__(self, that):
        return self.this == that

    def __ne__(self, that):
        return self.this != that

    def __lt__(self, that):
        return self.this < that

    def __le__(self, that):
        return self.this <= that

    def __gt__(self, that):
        return self.this > that

    def __ge__(self, that):
        return self.this >= that

