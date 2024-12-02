##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import types
import logging
from Products.ZenUtils.jsonutils import json
from zenoss.protocols.protobufs import zep_pb2 as eventConstants

OLD_SYSLOG_MAPPING = {
    0: eventConstants.SYSLOG_PRIORITY_DEBUG,
    1: eventConstants.SYSLOG_PRIORITY_INFO,
    2: eventConstants.SYSLOG_PRIORITY_NOTICE,
    3: eventConstants.SYSLOG_PRIORITY_WARNING,
    4: eventConstants.SYSLOG_PRIORITY_ERR,
    5: eventConstants.SYSLOG_PRIORITY_CRIT,
    6: eventConstants.SYSLOG_PRIORITY_ALERT,
    7: eventConstants.SYSLOG_PRIORITY_EMERG,
}

log = logging.getLogger('zen.WhereClause')

new_name_mapping = {
    'eventClass':'evt.event_class',
    'summary':'evt.summary',
    'message':'evt.message',
    'eventKey':'evt.event_key',
    'agent':'evt.agent',
    'manager':'evt.monitor',
    'severity':'evt.severity',
    'eventState':'evt.status',
    'count':'evt.count',
    'prodState':'dev.production_state',
    'device':'elem.name',
    'devicePriority':'dev.priority',
    'component':'sub_elem.name',
    'eventClassKey':'evt.event_class_key',
    'priority':'evt.syslog_priority',
    'facility':'evt.syslog_facility',
    'ntevid':'evt.nt_event_code',
    'ownerId':'evt.current_user_name',
    'deviceClass':'dev.device_class',
    'systems':'dev.systems',
    'deviceGroups':'dev.groups',
    'ipAddress':'dev.ip_address',
    'location':'dev.location',
}


def getName(str):
    # lookup the old to new map
    if str in new_name_mapping:
        return new_name_mapping[str]
    # don't know a better way to error yet.
    return str

def getValue(val):
    # escape things
    if isinstance(val, basestring):
        return '"%s"' % val.replace('"', '\"')
    else:
        return val

def getEndsWith(name, value):
    return "{name}.endswith({value})".format(
            name=getName(name),
            value=getValue(value)
            )

def getStartsWith(name, value):
    return "{name}.startswith({value})".format(
            name=getName(name),
            value=getValue(value)
            )

def getIn(name, value):
    return "{value} in {name}".format(
            name=getName(name),
            value=getValue(value)
            )

def getNotIn(name, value):
    return "{value} not in {name}".format(
            name=getName(name),
            value=getValue(value)
            )

def getEquality(name, op, value):
    return "{name} {op} {value}".format(
            name=getName(name),
            op=op,
            value=getValue(value)
            )


negativeModes = (
'!', # is not
'!~', # does not contain
'!^',   # does not begin with
)

def q(s):
    # turn string "fo'o" -> "'fo''o'"
    return "'%s'" % "''".join(s.split("'"))

class Error(Exception): pass

class WhereJavaScript:
    "Base class for converting to/from javascript"
    type = 'unknown'

    def __init__(self, label):
        self.label = label

    def genProperties(self, name):
        return '%s:{type:"%s",label:"%s"}' % (name, self.type, self.label)

    def buildClause(self, name, value, mode):
        foundNegativeMatch = False
        result = []
        for v in value:
            if not v: return None
            if mode in negativeModes: foundNegativeMatch = True
            result.append(self.buildClause1(name, v, mode))
        if not result:
            return None
        if foundNegativeMatch:
            return ' and '.join(result)
        else:
            return ' or '.join(result)

class Text(WhereJavaScript):
    "Convert to/from javascript for text entries"
    type = 'text'

    def toJS(self, mode, value):
        if mode == 'like':
            if value.startswith('%') and not value.endswith('%'):
                return '$', [value[1:]]
            elif not value.startswith('%') and value.endswith('%'):
                return '^', [value[:-1]]
            elif value.startswith('%') and value.endswith('%'):
                return '~', [value[1:-1]]
        if mode == 'not like':
            return '!~', [value[1:-1]]
        if mode == '=':
            return '', [value]
        if mode == '!=':
            return '!', [value]

    def buildPython(self, name, mode, value):
        if mode == 'like':
            if value.startswith('%') and not value.endswith('%'):
                return getEndsWith(name, value[1:])
            elif not value.startswith('%') and value.endswith('%'):
                return getStartsWith(name, value[:-1])
            elif value.startswith('%') and value.endswith('%'):
                return getIn(name, value[1:-1])
        if mode == 'not like':
            return getNotIn(name, value[1:-1])
        if mode == '=':
            return getEquality(name, '==', value)
        if mode == '!=':
            return getEquality(name, '!=', value)

    def buildClause1(self, name, v, mode):
        if mode == '~':
            return "%s like %s" % (name, q('%' + v + '%'))
        if mode == '^':
            return "%s like %s" % (name, q(v + '%'))
        if mode == '$':
            return "%s like %s" % (name, q('%' + v))
        if mode == '!~':
            return "%s not like %s" % (name, q('%' + v + '%'))
        if mode == '':
            return "%s = %s" % (name, q(v))
        if mode == '!':
            return "%s != %s" % (name, q(v))


class Select(WhereJavaScript):
    "Convert to/from javascript and where clause element for select entries"
    type = 'select'

    def __init__(self, label, options):
        WhereJavaScript.__init__(self, label)
        if options:
            if type(options[0]) != type(()):
                options = zip(range(len(options)), options)
        self.options = options

    def labelFromValue(self, value):
        return dict(self.options).get(value, 'Unknown')

    def valueFromLabel(self, value):
        return dict([(v, l) for l, v in self.options]).get(value, -1)

    def toJS(self, operator, value):
        if operator == '=':
            return ('', [self.labelFromValue(value)])
        if operator == '!=':
            return ('!', [self.labelFromValue(value)])
        result = []
        if operator in ('<', '>', '<=', '>='):
            for i, name in self.options:
                if eval('%d %s %d' % (i, operator, value)):
                    result.append(name)
        return ('', result)

    def buildPython(self, name, operator, value):
        if operator == '=':
            return getEquality(name, '==', value)
        else:
            return getEquality(name, operator, value)

    def genProperties(self, name):
        return '%s:{type:"%s",label:"%s", options:%r}' % (
            name, self.type, self.label, [s[1] for s in self.options])

    def buildClause1(self, name, v, mode):
        v = self.valueFromLabel(v)
        if type(v) in types.StringTypes:
            v = q(v)
        if mode == '':
            return "%s = %s" % (name, v)
        else:
            return "%s != %s" % (name, v)

    def buildMultiValuePython(self, name, mode, value):

        value = value.strip('%|')

        # if mode == 'like':
        #     if value.startswith('%') and not value.endswith('%'):
        #         return 'any(d.endswith({value}) for d in {name})'.format(value=getValue(bare_value), name=getName(name))
        #     elif not value.startswith('%') and value.endswith('%'):
        #         return 'any(d.startswith({value}) for d in {name})'.format(value=getValue(bare_value), name=getName(name))
        #     elif value.startswith('%') and value.endswith('%'):
        #         return 'any({value} in d for d in {name})'.format(value=getValue(bare_value), name=getName(name))
        #     else:
        #         return getIn(name, bare_value)
        #
        # if mode == 'not like':
        #     if value.startswith('%') and not value.endswith('%'):
        #         return 'not any(d.endswith({value}) for d in {name})'.format(value=getValue(bare_value), name=getName(name))
        #     elif not value.startswith('%') and value.endswith('%'):
        #         return 'not any(d.startswith({value}) for d in {name})'.format(value=getValue(bare_value), name=getName(name))
        #     elif value.startswith('%') and value.endswith('%'):
        #         return 'not any({value} in d for d in {name})'.format(value=getValue(bare_value), name=getName(name))
        #     else:
        #         return getNotIn(name, bare_value)

        if mode == 'like':
            return getIn(name, value)
        if mode == 'not like':
            return getNotIn(name, value)


class Compare(WhereJavaScript):
    "Convert to/from javascript and where clause elements for numeric comparisons"
    type = 'compare'

    def toJS(self, operator, value):
        return operator, [value]

    def buildPython(self, name, operator, value):
        if operator == '=':
            return getEquality(name, '==', value)
        else:
            return getEquality(name, operator, value)

    def buildClause1(self, name, v, mode):
        return "%s %s %s" % (name, mode, v)


class DeviceGroup(Select):
    def toJS(self, operator, value):
        if operator == 'like':
            return ['', [value[2:-1]]]
        if operator == 'not like':
            return ['!', [value[2:-1]]]

    def buildPython(self, name, operator, value):
        return self.buildMultiValuePython(name, operator, value)

    def buildClause1(self, name, v, mode):
        if mode == '':
            return "%s like %s" % (name, q('%|' + v + '%'))
        else:
            return "%s not like %s" % (name, q('%|' + v + '%'))
    
class EventClass(Select):
    type = 'evtClass'

    def toJS(self, operator, value):
        value = value.rstrip('%')
        if operator == '=':
            return ['', [value]]
        if operator == '!=':
            return ['!', [value]]
        if operator == 'like':
            return ['^', [value]]
        if operator == 'not like':
            return ['!^', [value]]

    def buildPython(self, name, operator, value):
                
        mode = operator
        if mode == 'like':
            if value.startswith('%') and not value.endswith('%'):
                return getEndsWith(name, value[1:])
            elif not value.startswith('%') and value.endswith('%'):
                return getStartsWith(name, value[:-1])
            elif value.startswith('%') and value.endswith('%'):
                return getIn(name, value[1:-1])
            else:
                return 
        if mode == 'not like':
            return getNotIn(name, value[1:-1])
        if mode == '=':
            return getEquality(name, '==', value)
        if mode == '!=':
            return getEquality(name, '!=', value)

    def buildClause1(self, name, v, mode):
        if mode == '':
            return "%s = %s" % (name, q(v))
        elif mode == '^':
            return "%s like %s" % (name, q(v + '%'))
        elif mode == '!^':
            return "%s not like %s" % (name, q(v + '%'))
        else:
            return "%s != %s" % (name, q(v))



class Enumerated(Select):
    "Convert to/from javascript and where clause elements for enumerated types"
    type='cselect'

    def toJS(self, operator, value):
        return operator, [self.labelFromValue(value)]

    def buildPython(self, name, operator, value):
        if operator == '=':
            return getEquality(name, '==', value)
        else:
            return getEquality(name, operator, value)

    def buildClause1(self, name, v, mode):
        return "%s %s %s" % (name, mode, self.valueFromLabel(v))

_Definitions = r'''
def u(s):
    # turn string "'fo''o'" -> "fo'o"
    c = s[0]
    s = c.join(s.split(c+c))
    return s[1:-1]

'''

_ParseSpec = r'''
parser WhereClause:
    ignore:    "[ \r\t\n]+"
    token END: "$"
    token NUM: "[0-9]+"
    token VAR: "[a-zA-Z0-9_]+"
    token BIN: ">=|<=|==|=|<|>|!=|<>"
    token STR: r'"([^\\"]+|\\.)*"'
    token STR2: r"'([^\\']+'{2,}|[^\\']+|\\.)*'"

    rule goal:    andexp ? END       {{ return locals().get('andexp', None) }}

    rule andexp:  orexp              {{ e = orexp }}
                  ( "and" orexp      {{ e = ('and', e, orexp) }}
                  )*                 {{ return e }}

    rule orexp:   binary             {{ e = binary }}
                  ( "or" binary      {{ e = ('or', e, binary) }}
                  )*                 {{ return e }}

    rule binary:  term               {{ e = term }}
                  ( BIN term         {{ e = (BIN, e, term) }}
                    | 'like' term    {{ e = ('like', e, term) }}
                    | 'not' 'like' term
                                     {{ e = ('not like', e, term) }}
                  )*                 {{ return e }}

    rule term:    NUM                {{ return int(NUM) }}
                  | VAR              {{ return VAR }}
                  | STR              {{ return u(STR) }}
                  | STR2             {{ return u(STR2) }}
                  | "\\(" andexp "\\)" {{ return andexp }}
'''

class _Parser:
    def __init__(self, spec):
        from yapps import grammar, yappsrt
        from StringIO import StringIO

        scanner = grammar.ParserDescriptionScanner(spec)
        parser = grammar.ParserDescription(scanner)
        parser = yappsrt.wrap_error_reporter(parser, 'Parser')
        parser.preparser = _Definitions
        parser.output = StringIO()
        parser.generate_output()
        exec parser.output.getvalue() in self.__dict__

where = _Parser(_ParseSpec)

@json
def toJavaScript(meta, clause):
    # sql is case insensitive, map column names to lower-case versions
    lmeta = dict([(n.lower(), n) for n in meta.keys()])
    tree = where.parse('goal', clause)

    def recurse(root, result):
        if type(root) == types.TupleType:
            n = len(root)
            if n == 1:
                recurse(root[0], result)
            op, name, value = root
            if op in ('and', 'or'):
                recurse(root[1], result)
                recurse(root[2], result)
            else:
                name = lmeta.get(name.lower(), None)
                if name is not None:
                    op, value = meta[name].toJS(op, value)
                    result.append([name, op, value])

    result = []
    recurse(tree, result)
    result.sort()
    return result

def collapse(tree):
    """
    Collapses adjacent and/ors into one statement.
    and(and(a, b), c) becomes and(a, b, c).
    """
    def _collapse(term, curopr=None, oprstack=None):
        op = term[0]
        if op == curopr:
            _collapse(term[1], op, oprstack)
            _collapse(term[2], op, oprstack)
        elif op in ('and', 'or'):
            s1, s2 = [], []
            _collapse(term[1], op, s1)
            _collapse(term[2], op, s2)
            combined = [op] + s1 + s2
            oprstack.append(combined)
        else:
            oprstack.append(term)

    exprs = []
    _collapse(tree, None, exprs)
    return exprs

class PythonConversionException(Exception):
    """
    Exception thrown when a where clause fails conversion to a Python expression.
    """
    pass

def toPython(meta, clause):
    # sql is case insensitive, map column names to lower-case versions
    lmeta = dict([(n.lower(), n) for n in meta.keys()])
    tree = where.parse('goal', clause)
    
    def recurse(root, result):
        if isinstance(root, (list, tuple)):
            op = root[0]
            if op in ('and', 'or'):
                all_sub_results = []
                for clause in root[1:]:
                    sub_result = []
                    recurse(clause, sub_result)
                    all_sub_results.extend(sub_result)
                result.append('(' + (' %s ' % op).join(all_sub_results) + ')')
            else:
                name, value = root[1], root[2]
                orig_name = name.lower()
                name = lmeta.get(orig_name, None)
                if name is not None:
                    # Special case - ntevid must be convertable to integer and operator must be == or !=
                    if orig_name == 'ntevid':
                        if op not in ('=','!='):
                            raise PythonConversionException('Unable to migrate ntevid starts/ends-with clause')
                        try:
                            value = int(value)
                        except ValueError:
                            raise PythonConversionException('Failed to convert ntevid to integer')
                    if orig_name == 'priority':
                        value = OLD_SYSLOG_MAPPING[value]

                    python_statement = meta[name].buildPython(name, op, value)
                    result.append('(%s)' % python_statement)

    result = []
    tree = collapse(tree)
    recurse(tree[0], result)
    rule = result[0]
    # And's and Or's already add parentheses - we need to strip the outermost parens
    if tree[0][0] in ('and', 'or'):
        rule = rule[1:-1]
    return rule


def fromFormVariables(meta, form):
    result = []
    for n, attrType in meta.items():
        if form.has_key(n):
            value = form[n]
            if type(value) != type([]):
                value = [value]
            mode = form.get(n + "_mode", None)
            clause = attrType.buildClause(n, value, mode)
            if clause:
                result.append('(%s)' % clause)
    return ' and '.join(result)


if __name__ == '__main__':
    meta = {}
    toJavaScript(meta, 'severity = 3 or severity = 4')
    toJavaScript(meta, "severity >= 4 and eventState = 0 and prodState = 1000")
    toJavaScript(meta, "severity >= 2 and eventState = 0 and prodState = 1000")
    print toJavaScript(meta, '(prodState = 1000) and (eventState = 0 or eventState = 1) and (severity >= 3)')
    print fromFormVariables(meta,
                            dict(severity='Info',
                                 severity_mode='>',
                                 eventState='New',
                                 eventState_mode='=',
                                 prodState='Production',
                                 prodState_mode='='))
