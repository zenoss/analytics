##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import cgi
import re
import cStringIO
import logging
from Products.PageTemplates.Expressions import getEngine
from zope.tal.htmltalparser import HTMLTALParser
from zope.tal.talgenerator import TALGenerator
from zope.tales.engine import Engine
from zope.tal.talinterpreter import TALInterpreter
from DateTime import DateTime
from Products.Zuul.interfaces.info import IInfo

log = logging.getLogger("zen.actions")

class InvalidTalesException(Exception):
    pass


_compiled = {}

def talesEvalStr(expression, context, extra=None, skipfails=False):
    return talesEval('string:%s' % expression, context, extra, skipfails)


def talesEval(express, context, extra=None, skipfails=False):
    """Perform a TALES eval on the express using context.
    """
    try:
        compiled = talesCompile(express)
    except Exception as e:
        compiled = talesCompile("string:%s" % express)

    contextDict = { 'context':context,
                    'here':context,
                    'nothing':None,
                    'now': DateTime(),
                    }
    if isinstance(extra, dict):
        contextDict.update(extra)

    try:
        contextDict['info'] = IInfo(context)
    except TypeError:
        pass

    try:
        res = compiled(getEngine().getContext(contextDict))
    except Exception as e:
        msg = "Error when processing tales expression %s on context %s : Exception Class %s Message: %s" % (express,
                                                                                                            context,
                                                                                                            type(e), e)
        if skipfails:
            res = express
            log.debug(msg)
        else:
            raise InvalidTalesException(msg)

    if isinstance(res, Exception):
        raise res
    return res

def talesCompile(express):
    compiled = _compiled.get(express, None)
    if not compiled:
        _compiled[express] = compiled = getEngine().compile(express)
    return compiled

TAG = re.compile(r'(<tal[^<>]>)')
TPLBLOCK = re.compile(r'\$\{(.*?)\}')

def _chunk_repl(match):
    """
    Need this to escape quotes and <> in expressions
    """
    interior = cgi.escape(match.groups()[0], True)
    return '<tal:block content="%s"/>' % interior

def talEval(expression, context, extra=None, skipfails=False):
    """
    Perform a TAL eval on the expression.
    """
    # First, account for the possibility that it is merely TALES; if there are
    # no <tal> in it at all (nor the ${python:} you can do with this function),
    # just send it to talesEval
    isTales = '<tal' not in expression and '${python:' not in expression
    if isTales:
        return talesEvalStr(expression, context, extra, skipfails)

    contextDict = { 'context':context,
                    'here':context,
                    'nothing':None,
                    'now': DateTime(),
                    }
    if isinstance(extra, dict):
        contextDict.update(extra)

    # Next, as a convenience, replace all ${} blocks that aren't inside a <tal>
    # with <tal:block content="..."/> equivalent
    chunks = TAG.split(expression)
    modified = []
    for chunk in chunks:
        if chunk.startswith('<tal'):
            modified.append(chunk)
        else:
            modified.append(TPLBLOCK.sub(_chunk_repl, chunk))
    expression = ''.join(modified)

    # Finally, compile the expression and apply context
    gen = TALGenerator(Engine, xml=0)
    parser = HTMLTALParser(gen)
    parser.parseString(expression)
    program, macros = parser.getCode()
    output = cStringIO.StringIO()
    context = Engine.getContext(contextDict)
    TALInterpreter(program, macros, context, output, tal=True)()
    return output.getvalue()
